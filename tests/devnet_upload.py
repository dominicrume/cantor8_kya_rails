#!/usr/bin/env python3
"""Upload the mandate DAR to DevNet and read what Canton says about it.

docs/upgrade-path.md said "upload to DevNet and read the response" without
saying how, which is the kind of gap that turns a two-minute step into an
afternoon. This is how.

Canton checks upgrade compatibility at upload. A NOT_VALID_UPGRADE_PACKAGE
names the type that changed and refuses; a quiet success means it vetted and
the new version is live. Both are worth seeing in full, so nothing here
swallows the response.

    python3 tests/devnet_upload.py                 the current built DAR
    python3 tests/devnet_upload.py path/to.dar     a specific one

Needs C8_CLIENT_SECRET. Never in CI: CI must not be able to deploy.
"""
import glob, json, os, sys, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "step-2-agent"))


def find_dar():
    pattern = os.path.join(ROOT, "step-1-mandate", ".daml", "dist",
                           "kya-rails-mandate-*.dar")
    found = sorted(glob.glob(pattern))
    if not found:
        return None
    return found[-1]


def refuse_if_tests_inside(path):
    """A DAR carrying test types makes renaming a test an on-ledger breaking
    change. That cost a failed upgrade once; see docs/upgrade-path.md."""
    import subprocess
    out = subprocess.run(["daml", "damlc", "inspect-dar", path],
                         capture_output=True, text=True).stdout
    return [l for l in out.splitlines() if "Test" in l and "Kya" in l]


def upload(path, dn, c8lab):
    url = c8lab.BASE.rstrip("/") + "/v2/packages"
    with open(path, "rb") as fh:
        body = fh.read()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": "Bearer " + c8lab.token(sub=dn.USER),
        "Content-Type": "application/octet-stream"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read().decode()[:600]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:900]


def main():
    if not os.environ.get("C8_CLIENT_SECRET"):
        print("C8_CLIENT_SECRET is not set. Run tests/devnet_check.py first.")
        return 1
    path = sys.argv[1] if len(sys.argv) > 1 else find_dar()
    if not path or not os.path.exists(path):
        print("no DAR found. Run `cd step-1-mandate && daml build` first.")
        return 1

    leaked = refuse_if_tests_inside(path)
    if leaked:
        print("REFUSING TO UPLOAD: this DAR contains test types.")
        for l in leaked[:5]:
            print("   ", l.strip())
        print("Tests belong in step-1-mandate/test, a separate package.")
        return 1

    import devnet_ledger as dn
    import c8lab
    print("uploading %s (%d bytes)" % (os.path.basename(path),
                                       os.path.getsize(path)))
    return report(*upload(path, dn, c8lab))


def report(code, body):
    print("  HTTP %s" % code)
    if body.strip():
        print("  " + body.strip().replace("\n", "\n  "))
    if code in (200, 201, 204):
        print("\n  vetted. Canton accepted it as an upgrade of what was there.")
        return 0
    print("\n  refused. If this says NOT_VALID_UPGRADE_PACKAGE, the message")
    print("  above names the type that changed -- read it literally.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
