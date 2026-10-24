#!/usr/bin/env python3
"""Make an authenticated request and return the STATUS, never the body.

CLAUDE.md: a secret in means tainted out. Any response from something you
authenticated to may contain the credential back, so the body is never
printed. This exists so the safe path is also the shortest one to type, and
there is no reason to hand-write an authenticated `curl` again.

    python3 tools/authed.py ghcr https://ghcr.io/v2/owner/pkg/tags/list
    python3 tools/authed.py github https://api.github.com/user x-oauth-scopes

Prints a status line, and optionally named response HEADERS, which are safe.
Prints the body never. If you genuinely need a field out of the body, add a
named extractor below that returns a BOOLEAN or a LENGTH, not the value.

Written 23 October 2026, after a diagnostic against ghcr.io's token endpoint
printed a live classic token into a transcript. The endpoint returns the
base64 of the credential you sent it as its bearer token, so a request that
looked like a permissions check handed the secret straight back.

Corrected 24 October 2026. The `github` source used to shell out to
`gh auth token`, which is the FIRST command CLAUDE.md forbids by name. A tool
written to keep credentials out of the transcript was running the one command
guaranteed to put one there. tests/security_lint.py has had that string in its
rule list the whole time and read this file on every run: it searched for the
text "gh auth token" and this file spelled it ["gh", "auth", "token"]. The
rule was right, the scan was right, and the match was defeated by punctuation.
"""
import base64
import json
import pathlib
import subprocess  # nosec B404 - fixed argv, no shell
import sys


def ghcr_credential():
    """Return (user, secret) for ghcr.io from the docker config. Never prints.

    Note what this cannot see: if the config sets "credsStore", every OCI
    client ignores the "auths" block and delegates to the native helper, so a
    credential read from here is not the one the registry will be given. That
    mismatch cost six debugging rounds and a wrongly filed issue on 22 October
    2026, which is why it is written down here rather than remembered.
    """
    config = pathlib.Path.home() / ".docker" / "config.json"
    entry = json.loads(config.read_text())["auths"]["ghcr.io"]
    if "auth" in entry:
        user, _, secret = base64.b64decode(entry["auth"]).decode().partition(":")
        return user, secret
    return entry["username"], entry["password"]


def headers_for(kind, url):
    """Return the raw response header block, having discarded the body."""
    if kind == "ghcr":
        user, secret = ghcr_credential()
        # -o /dev/null is the whole point: the body is discarded before it can
        # be seen, rather than fetched and then filtered. A filter can be
        # forgotten and a discard cannot.
        argv = ["curl", "-s", "-o", "/dev/null", "-D", "-", "--max-time", "30",
                "-u", "%s:%s" % (user, secret), url]
    elif kind == "github":
        # gh holds the token itself, so it never enters this process. Only the
        # header block is kept; everything after the blank line is dropped
        # below without being looked at.
        argv = ["gh", "api", "--include", "--method", "GET", url]
    else:
        sys.exit("unknown credential source: %s" % kind)

    done = subprocess.run(argv, capture_output=True, text=True)  # nosec B603 B607
    block, _, _ = done.stdout.partition("\n\n")
    return block, done.returncode


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    kind, url = argv[0], argv[1]
    want = tuple(a.lower() for a in argv[2:] if not a.startswith("--"))

    block, code = headers_for(kind, url)
    shown = [line.strip() for line in block.splitlines()
             if line.lower().startswith(("http/",) + want)]

    for line in shown:
        print("   ", line)
    if not shown:
        print("    no status line returned; exit %d" % code)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
