#!/usr/bin/env python3
"""What is out there with somebody else's name on it, and has anyone answered.

This asks, rather than making you remember the URLs.

    python3 tools/waiting.py

IT ONLY WATCHED GITHUB FOR ITS FIRST WEEK, AND THAT WAS THE MISTAKE. Every
reply this project has ever received came from the Canton forum, and none of
them came from a GitHub issue. On 11 September two people replied on the forum:
one asked us to say plainly what we are building, and one read the design,
found the hole and specified the fix a day before it was built. Both sat
unanswered for two days while this tool reported "nothing yet", truthfully,
about the wrong place.

A tool called "waiting on other people" that watches only the channel nobody
answers on is worse than no tool, because it is reassuring.

Forum topics are read as public JSON: Discourse serves any topic at `<url>.json`
with no key. Needs nothing installed.
"""
import json
import os
import re
import subprocess  # nosec B404 - shelling out to gh is the point
import sys
import urllib.request

WATCHING = [
    ("OpenZeppelin/canton-contracts", 43, "issue",
     "three untested access-control fences"),
    ("OpenZeppelin/canton-token-template", 9, "issue",
     "24 of 32 fences with no test behind them"),
    ("OpenZeppelin/canton-stablecoin", 9, "issue",
     "25 of 30, including the oracle price guard"),
    ("canton-network-devs/Canton-Developer-Hub", 156, "pull",
     "KYA Rails in the tool catalogue"),
]

# Discourse topics, read as JSON. `us` is our own username: a reply from
# anybody else is somebody answering, and a reply from us is not.
FORUM = "https://forum.canton.network"
US = "orumedominic"
TOPICS = [
    (9059, "the OpenZeppelin feedback thread, where the stablecoin issuer is"),
    (9114, "our own topic: how do you prove your app didn't do something?"),
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
    url = "https://api.github.com" + path
    if not url.startswith("https://api.github.com/"):
        return {"_error": "refusing a URL that is not the GitHub API"}
    try:
        with urllib.request.urlopen(url, timeout=30) as r:   # nosec B310 - checked above
            return json.loads(r.read())
    except Exception as e:                       # noqa: BLE001 - offline is an answer
        return {"_error": str(e)}


def replies(repo, number):
    """Every comment, one line each. Empty when nobody has answered."""
    out = []
    for c in api("/repos/%s/issues/%d/comments" % (repo, number)) or []:
        if isinstance(c, dict) and c.get("user"):
            first = (c.get("body") or "").strip().splitlines()
            out.append("      -> %s (%s): %s"
                       % (c["user"]["login"], c["created_at"][:10],
                          first[0][:90] if first else ""))
    return out


def show(repo, number, kind, what):
    thing = api("/repos/%s/issues/%d" % (repo, number))
    if thing.get("_error"):
        print("  %s#%d  could not be read: %s" % (repo, number, thing["_error"][:40]))
        return 0
    merged = " MERGED" if thing.get("pull_request", {}).get("merged_at") else ""
    n = thing.get("comments", 0)
    print("  %-44s %-6s%s  %d comment(s)"
          % ("%s#%d" % (repo, number), thing.get("state", "?"), merged, n))
    print("      %s" % what)
    for line in replies(repo, number) if n else []:
        print(line)
    return n


def posts_on(number):
    """Every post on a forum topic, or None if it could not be read.

    Offline is an answer, not an exception: a tool that raises when the network
    is down is a tool nobody runs, and this one exists to be run every day.
    """
    url = "%s/t/%d.json" % (FORUM, number)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:   # nosec B310 - literal host
            data = json.loads(r.read())
    except Exception as e:                       # noqa: BLE001 - offline is an answer
        print("  forum/t/%d   could not be read: %s" % (number, str(e)[:40]))
        return None
    return (data.get("post_stream") or {}).get("posts") or []


def plain(post):
    """A forum post's text, with Discourse's HTML taken out."""
    return " ".join(re.sub(r"<[^>]+>", " ", post.get("cooked") or "").split())


def topic(number, what):
    """Posts on one forum topic, and who is owed a reply.

    The thing worth printing is not the post count. It is whether the LAST post
    is somebody else's, because that is the definition of owing a reply, and it
    is the question nobody was asking for two days.
    """
    posts = posts_on(number)
    if posts is None:
        return 0
    others = [p for p in posts if p.get("username") != US]
    print("  %-44s %d post(s), %d from other people"
          % ("forum.canton.network/t/%d" % number, len(posts), len(others)))
    print("      %s" % what)
    if not posts:
        return 0
    for p in others[-2:]:
        print("      -> %s (%s): %s"
              % (p.get("username"), (p.get("created_at") or "")[:10], plain(p)[:96]))
    return announce(posts[-1])


def announce(last):
    """Say, unmissably, whether the last word was somebody else's.

    Unmissably is the requirement, not a flourish. The old version of this tool
    printed "nothing yet" for two days while two people waited, and it was
    telling the truth about the wrong place. A line that can be skimmed past is
    the same failure with extra steps.
    """
    owed = last.get("username") != US
    if owed:
        print("      ** THE LAST WORD IS THEIRS. You owe %s a reply. **"
              % last.get("username"))
    return 1 if owed else 0


def main():
    print("waiting on other people")
    replies = sum(show(r, n, k, w) for r, n, k, w in WATCHING)
    print()
    print("the forum, which is where every reply has actually come from")
    owed = sum(topic(n, w) for n, w in TOPICS)
    print()
    if owed:
        print("%d conversation(s) waiting on YOU, not on them." % owed)
        print("Answer those before filing anything new.")
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
