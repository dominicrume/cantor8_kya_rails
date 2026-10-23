#!/usr/bin/env python3
"""Push a Daml DAR to an OCI registry in the exact shape `dpm publish dar` makes.

Written while debugging what looked like a dpm authentication bug and was not.
dpm 1.0.21 works. The local ~/.docker/config.json carried credsStore alongside
a hand-written auths entry, and every OCI client correctly ignores auths when
credsStore is set, so the request went out unauthenticated and ghcr answered
403. See digital-asset/dpm#329, filed in error and corrected.

Keeping this anyway. The artefacts it produced are published and correct, it
documents the on-the-wire shape of a DAR artifact in one readable file, and
it is useful wherever dpm is not available.

Every structural choice below was read out of dpm's own source rather than
guessed, because an artefact in the wrong shape is one nobody can consume.
The three things dpm's PULL path actually requires:

  * the manifest annotation org.opencontainers.image.version, strict semver
  * a layer titled exactly dar.yaml, apiVersion digitalasset.com/v1, kind Dar
  * every layer's org.opencontainers.image.title matching dar.yaml's path

The media types are set correctly anyway, so a later dpm that does validate
them still accepts what this wrote.

CLAUDE.md: a secret in means tainted out. Nothing here prints a response body
or a token. Status codes only.

    python3 tools/oci_push_dar.py ghcr.io/owner/name 1.0.0 path/to.dar LICENSE
"""
import base64
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess  # nosec B404 - fixed argv, no shell
import sys
import tempfile
import zipfile

ARTIFACT_TYPE = "application/vnd.dar.artifact"
FILE_MEDIA_TYPE = "application/vnd.dar.file"
MANIFEST_TYPE = "application/vnd.oci.image.manifest.v1+json"
EMPTY_TYPE = "application/vnd.oci.empty.v1+json"
EMPTY_BODY = b"{}"


def sha(b):
    return "sha256:" + hashlib.sha256(b).hexdigest()


def main_package_id(dar):
    """Read the main package id out of the DAR, rather than trusting a filename."""
    mf = zipfile.ZipFile(dar).read("META-INF/MANIFEST.MF").decode()
    mf = mf.replace("\r\n ", "").replace("\n ", "")
    m = re.search(r"Main-Dalf:\s*(\S+)", mf)
    if not m:
        sys.exit("no Main-Dalf in %s" % dar)
    h = re.search(r"-([0-9a-f]{64})\.dalf$", m.group(1))
    return h.group(1) if h else m.group(1)


class Registry:
    """Thin OCI client. Returns status codes; never returns or prints a body
    that could carry the credential."""

    def __init__(self, host, repo):
        self.host, self.repo = host, repo
        e = json.loads((pathlib.Path.home() / ".docker" / "config.json").read_text())
        a = e["auths"][host]
        if "auth" in a:
            self.user, _, self.secret = base64.b64decode(a["auth"]).decode().partition(":")
        else:
            self.user, self.secret = a["username"], a["password"]
        self.token = self._bearer()

    def _bearer(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        scope = "repository:%s:pull,push" % self.repo
        subprocess.run(  # nosec B603 B607
            ["curl", "-s", "-o", path, "--max-time", "60",
             "-u", "%s:%s" % (self.user, self.secret),
             "https://%s/token?scope=%s&service=%s" %
             (self.host, scope.replace(":", "%3A").replace("/", "%2F"), self.host)],
            capture_output=True)
        try:
            t = json.load(open(path)).get("token", "")
        finally:
            os.unlink(path)
        if not t:
            sys.exit("could not obtain a push token for %s" % self.repo)
        return t

    def _curl(self, args, capture_headers=False):
        base = ["curl", "-s", "-o", "/dev/null", "--max-time", "300",
                "-H", "Authorization: Bearer " + self.token]
        if capture_headers:
            base += ["-D", "-", "-w", "\n%{http_code}"]
        else:
            base += ["-w", "%{http_code}"]
        r = subprocess.run(base + args, capture_output=True, text=True)  # nosec B603 B607
        return r.stdout

    def has_blob(self, digest):
        return self._curl(["-I", "https://%s/v2/%s/blobs/%s"
                           % (self.host, self.repo, digest)]).strip().endswith("200")

    def push_blob(self, data, label):
        digest = sha(data)
        if self.has_blob(digest):
            print("    %-28s already present" % label)
            return digest
        out = self._curl(["-X", "POST", "https://%s/v2/%s/blobs/uploads/"
                          % (self.host, self.repo)], capture_headers=True)
        loc = ""
        for line in out.splitlines():
            if line.lower().startswith("location:"):
                loc = line.split(":", 1)[1].strip()
        if not loc:
            sys.exit("    %s: registry refused to start an upload" % label)
        if loc.startswith("/"):
            loc = "https://%s%s" % (self.host, loc)
        sep = "&" if "?" in loc else "?"
        fd, path = tempfile.mkstemp()
        os.write(fd, data)
        os.close(fd)
        try:
            code = self._curl(["-X", "PUT",
                               "-H", "Content-Type: application/octet-stream",
                               "--data-binary", "@" + path,
                               loc + sep + "digest=" + digest]).strip()
        finally:
            os.unlink(path)
        print("    %-28s %s bytes  HTTP %s" % (label, len(data), code))
        if code not in ("201", "202"):
            sys.exit("    upload failed")
        return digest

    def put_manifest(self, body, tag):
        fd, path = tempfile.mkstemp()
        os.write(fd, body)
        os.close(fd)
        try:
            code = self._curl(["-X", "PUT", "-H", "Content-Type: " + MANIFEST_TYPE,
                               "--data-binary", "@" + path,
                               "https://%s/v2/%s/manifests/%s"
                               % (self.host, self.repo, tag)]).strip()
        finally:
            os.unlink(path)
        return code


def file_annotations(path, extra=None):
    st = os.stat(path)
    name = os.path.basename(path)
    mode = "%o" % (st.st_mode & 0o777)
    mod = datetime.datetime.fromtimestamp(
        st.st_mtime, datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    a = {
        "org.opencontainers.image.title": name,
        "network.canton.dpm.file-mode": mode,
        "network.canton.dpm.file-modtime": mod,
        "network.canton.dpm.file-name": name,
        # dpm emits these legacy duplicates unless SKIP_LEGACY_OCI_ANNOTATIONS=true
        "com.digitalasset.file-mode": mode,
        "com.digitalasset.file-modtime": mod,
        "com.digitalasset.file-name": name,
    }
    a.update(extra or {})
    return a


def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    target, version, dar = argv[0], argv[1], argv[2]
    license_file = argv[3] if len(argv) > 3 else None
    host, _, repo = target.partition("/")
    reg = Registry(host, repo)

    pkg_id = main_package_id(dar)
    dar_name = os.path.basename(dar)
    print("  %s:%s" % (target, version))
    print("    main package id %s" % pkg_id)

    layers = []
    # 1. the DAR itself
    data = pathlib.Path(dar).read_bytes()
    d = reg.push_blob(data, dar_name)
    layers.append({"mediaType": FILE_MEDIA_TYPE, "digest": d, "size": len(data),
                   "annotations": file_annotations(
                       dar, {"network.canton.dpm.main-package-id": pkg_id})})

    # 2. the generated dar.yaml. Strict schema: dpm parses it with yaml.Strict().
    manifest_yaml = (
        "apiVersion: digitalasset.com/v1\n"
        "kind: Dar\n"
        "spec:\n"
        "  dars:\n"
        "    - path: %s\n"
        "      main-package-id: %s\n" % (dar_name, pkg_id)
    ).encode()
    d = reg.push_blob(manifest_yaml, "dar.yaml")
    layers.append({"mediaType": FILE_MEDIA_TYPE, "digest": d,
                   "size": len(manifest_yaml),
                   # dpm sets ONLY the title on this layer, no fileinfo keys
                   "annotations": {"org.opencontainers.image.title": "dar.yaml"}})

    # 3. the licence, which dpm requires for a DAR publish
    if license_file:
        data = pathlib.Path(license_file).read_bytes()
        d = reg.push_blob(data, os.path.basename(license_file))
        layers.append({"mediaType": FILE_MEDIA_TYPE, "digest": d,
                       "size": len(data), "annotations": file_annotations(license_file)})

    reg.push_blob(EMPTY_BODY, "empty config")

    created = datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="seconds").replace("+00:00", "Z")
    manifest = {
        "schemaVersion": 2,
        "mediaType": MANIFEST_TYPE,
        "artifactType": ARTIFACT_TYPE,
        "config": {"mediaType": EMPTY_TYPE, "digest": sha(EMPTY_BODY), "size": 2},
        "layers": layers,
        "annotations": {
            # the one thing dpm's pull path genuinely requires
            "org.opencontainers.image.version": version,
            "org.opencontainers.image.created": created,
        },
    }
    body = json.dumps(manifest, separators=(",", ":")).encode()
    code = reg.put_manifest(body, version)
    print("    manifest                     HTTP %s" % code)
    return 0 if code in ("201", "202") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
