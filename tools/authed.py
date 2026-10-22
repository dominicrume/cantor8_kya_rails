#!/usr/bin/env python3
"""Make an authenticated request and return the STATUS, never the body.

CLAUDE.md: a secret in means tainted out. Any response from something you
authenticated to may contain the credential back, so the body is never
printed. This exists so the safe path is also the shortest one to type, and
there is no reason to hand-write an authenticated `curl` again.

    python3 tools/authed.py ghcr https://ghcr.io/v2/owner/pkg/tags/list
    python3 tools/authed.py github https://api.github.com/user --header x-oauth-scopes

Prints a status line, and optionally named response HEADERS, which are safe.
Prints the body never. If you genuinely need a field out of the body, add a
named extractor below that returns a BOOLEAN or a LENGTH, not the value.

Written 23 October 2026, after a diagnostic against ghcr.io's token endpoint
printed a live PyPI-style classic token into a transcript. The endpoint
returns the base64 of the credential you sent it as its bearer token, so a
request that looked like a permissions check handed the secret straight back.
"""
import base64
import json
import pathlib
import subprocess  # nosec B404 - fixed argv, no shell
import sys

SAFE_HEADERS = ("http/", "x-oauth-scopes:", "x-ratelimit-remaining:",
                "www-authenticate:", "content-type:", "location:")


def credential(kind):
    """Return (user, secret) for a named source. Never prints either."""
    if kind == "ghcr":
        f = pathlib.Path.home() / ".docker" / "config.json"
        e = json.loads(f.read_text())["auths"]["ghcr.io"]
        if "auth" in e:
            u, _, s = base64.b64decode(e["auth"]).decode().partition(":")
            return u, s
        return e["username"], e["password"]
    if kind == "github":
        p = subprocess.run(["gh", "auth", "token"],  # nosec B603 B607
                           capture_output=True, text=True)
        return "x-access-token", p.stdout.strip()
    sys.exit("unknown credential source: %s" % kind)


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    kind, url = argv[0], argv[1]
    want = [a.lower() for a in argv[2:] if not a.startswith("--")]
    user, secret = credential(kind)

    # -o /dev/null is the whole point: the body is discarded before it can be
    # seen, rather than fetched and then filtered. A filter can be forgotten.
    p = subprocess.run(  # nosec B603 B607
        ["curl", "-s", "-o", "/dev/null", "-D", "-", "--max-time", "30",
         "-u", "%s:%s" % (user, secret), url],
        capture_output=True, text=True)

    shown = 0
    for line in p.stdout.splitlines():
        low = line.lower()
        if low.startswith("http/") or any(low.startswith(h) for h in want):
            print("   ", line.strip())
            shown += 1
    if not shown:
        print("    no status line returned; curl exit %d" % p.returncode)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
