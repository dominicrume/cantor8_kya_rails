#!/usr/bin/env python3
"""What is out there with somebody else's name on it, and has anyone answered.

Three things are waiting on other people and none of them will tell you. This
asks GitHub directly rather than making you remember three URLs.

    python3 tools/waiting.py

Needs nothing installed. Uses gh for authentication if it is there, and falls
back to the public API, which is enough to read a public issue.
"""
import json
import os
import subprocess
import sys
import urllib.request

WATCHING = [
    ("OpenZeppelin/canton-contracts", 43, "issue",
     "three untested access-control fences"),
    ("canton-network-devs/Canton-Developer-Hub", 156, "pull",
     "KYA Rails in the tool catalogue"),
]

GH = os.path.expanduser("~/gh")


def api(path):
    """Public read. gh if it is available, plain HTTPS if not."""
    if os.path.exists(GH):
        try:
            p = subprocess.run([GH, "api", path], capture_output=True,  # nosec B603 - literal argv
                               text=True, timeout=60)
            if p.returncode == 0:
                return json.loads(p.stdout)
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    try:
        with urllib.request.urlopen("https://api.github.com" + path, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:                       # noqa: BLE001 - offline is an answer
        return {"_error": str(e)}


def show(repo, number, kind, what):
    thing = api("/repos/%s/issues/%d" % (repo, number))
    if thing.get("_error"):
        print("  %s#%d  could not be read: %s" % (repo, number, thing["_error"][:40]))
        return 0
    state = thing.get("state", "?")
    n = thing.get("comments", 0)
    merged = " MERGED" if kind == "pull" and thing.get("pull_request", {}).get("merged_at") else ""
    print("  %-44s %-6s%s  %d comment(s)" % ("%s#%d" % (repo, number), state, merged, n))
    print("      %s" % what)
    if not n:
        return 0
    for c in api("/repos/%s/issues/%d/comments" % (repo, number)) or []:
        if isinstance(c, dict) and c.get("user"):
            first = (c.get("body") or "").strip().splitlines()
            print("      -> %s (%s): %s"
                  % (c["user"]["login"], c["created_at"][:10],
                     (first[0][:90] if first else "")))
    return n


def main():
    print("waiting on other people")
    replies = sum(show(r, n, k, w) for r, n, k, w in WATCHING)
    print()
    print("  dev-fund@canton.foundation  -- email, so check your inbox")
    print()
    if replies:
        print("%d repl(y/ies). Somebody has answered." % replies)
        return 0
    print("nothing yet. That is normal: the eight funded Dev Fund proposals took")
    print("15, 37, 85, 103 and 113 days from filing to decision.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
