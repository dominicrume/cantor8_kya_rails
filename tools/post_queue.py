#!/usr/bin/env python3
"""Walk the pending drafts one at a time: check, copy, open the page, wait.

WHY THIS EXISTS. tools/before_posting.py checks one draft and can put its body
on the clipboard. On 31 October 2026 all five pending drafts were checked in a
row, each with --copy, and the clipboard held only the last one. Four replies
were "ready" and none of them were anywhere. A tool that is correct per
invocation and wrong across a session is still wrong, because the session is
the unit of work.

So this does the whole queue, in order, and refuses to move on until you say a
thing is posted:

    python3 tools/post_queue.py

For each draft, in the order set in QUEUE below, it

  1. runs tools/before_posting.py and stops the whole queue if that fails,
     because a draft that does not pass is not posted and not skipped quietly,
  2. puts that draft's body on the clipboard, without its Post-To line,
  3. opens its destination in your browser,
  4. prints exactly what to press there, and waits,
  5. writes the date into docs/drafts/posted.log when you confirm, so the
     repository knows what left and when, and STATUS.md can be true.

Press Enter to confirm a post. Type s to skip one, or q to stop. Nothing is
recorded for a skip, so running it again picks that draft up.

Python standard library only. The only commands it runs are pbcopy and open,
both macOS, both with a literal argv.
"""

import json
import os
import re
import subprocess  # nosec B404 - literal argv, shell=False. The only values
                   # passed are paths from QUEUE below and a destination read
                   # from the draft's own first line.
import sys
import time
import urllib.error
import urllib.request

# The account whose post we are looking for when we go and check.
AUTHOR = "orumedominic"
GH_AUTHOR = "dominicrume"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFTS = os.path.join(ROOT, "docs", "drafts")
SOURCES = os.path.join(DRAFTS, "sources")
LOG = os.path.join(DRAFTS, "posted.log")

# THE TEST FOR THIS LIST IS WHO SPOKE LAST, AND IT IS MEASURED, NOT REMEMBERED.
#
# The first version of this QUEUE held six drafts and gave each one a reason in
# prose. Two of those reasons were false. It said Arpit Karnatak had been
# waiting since 18 October; the last post on topic 9084 is orumedominic,
# 22 October 01:45 UTC, so he was answered and the thread is ours. It implied
# the Dev Fund proposals were owed something; #860 and #866 both end with a
# dominicrume comment on 31 October.
#
# That is the same defect as the log that wrote "posted" on a keystroke. The
# tool stated a fact about a destination it had not read. A wrong reason is
# worse than no reason, because a wrong reason gets acted on: it would have
# sent an unprompted reply to a man who is not waiting, and spent the one thing
# this project has less of than code.
#
# So the list below holds only threads where the last word is NOT ours,
# measured on 4 November 2026, oldest debt first, with the timestamp that
# proves it. Anything whose last post is ours lives in OPTIONAL and is printed
# as not owed.
QUEUE = [
    ("ask-champion-860.md",
     "The money. #860's body has read `Needs Champion` for 38 days, and the "
     "field is the whole blocker: #866 carries a named champion, Yiannis "
     "Varelis of Five North, who wrote four words on 9 October, 'Happy to "
     "champion this.' He has never been asked about #860. Three public OFFERS "
     "have been made to him and ignored since 22 October, so this one is a "
     "closed question with a date on it. It also asks for the thing that "
     "closes the DevNet gap: Five North runs the live validator OS Ledger is "
     "deployed against. Goes FIRST."),
    ("reply-radev-9323.md",
     "Georgi Radev answered a direct question on topic 9323. Last post there "
     "is radevG, 27 October 11:52 UTC, 8 days ago. Longest debt, and he is "
     "credited by name in the CIP, so it goes first."),
    ("reply-leonid-9114.md",
     "Leonid corrected the Motivation on topic 9114. Last post there is "
     "leonidr, 30 October 01:40 UTC. While the page is open, tick PREDGE's "
     "post 6 as the solution: has_accepted_answer is still false, and you "
     "told him on 26 October that you had marked it."),
    ("reply-dpm-331.md",
     "digital-asset/dpm#331 was closed 31 October 16:49 UTC as not a true "
     "concern, and the maintainer was right. The only comment on it is his. A "
     "short acceptance costs nothing and is the one thing that answers an 'AI "
     "contribution' label: a person taking the judgement back. Leave the pull "
     "request closed."),
    ("post-sig-security.md",
     "A new topic in SIG Security, which holds exactly two topics, one of "
     "them the auto About post, and no post of yours at all. Nobody is "
     "waiting on this one, so it goes LAST: it says the others have already "
     "corrected the draft, which is only true once they are in."),
]

# Drafts that are written and checked but NOT owed, because the last word in
# those threads is already ours. They are listed rather than deleted so that
# nothing is quietly lost, and so the next person reading this file can see
# that the decision was made on a measurement.
OPTIONAL = [
    ("reply-karnatak-9084.md",
     "Topic 9084's last post is orumedominic, 22 October 01:45 UTC. He is not "
     "waiting on you; you are waiting on him. Send this only if you have "
     "something new and finished to show, never as a nudge."),
    ("reply-meier-cip-discuss.md",
     "Simon Meier on cip-discuss. Not a debt: he has not written since #910. "
     "But the draft HAS changed since the list saw it, so this is worth "
     "sending once the forum replies are in and the changes are real."),
]


def print_optional():
    """Say what is written and NOT owed, so it is neither sent nor forgotten."""
    if not OPTIONAL:
        return
    print("=" * 72)
    print("WRITTEN BUT NOT OWED. The last word in each of these is already")
    print("yours, measured 4 November 2026. Sending one is a choice, not a")
    print("debt, and an unprompted reply spends credit rather than earning it.")
    for name, why in OPTIONAL:
        print()
        print("  %s" % name)
        print("    %s" % why)
    print()


def run(argv, **kw):
    return subprocess.run(argv, **kw)  # nosec B603 - literal argv, no shell


def destination_and_body(path):
    with open(path) as f:
        raw = f.read()
    if raw.startswith("Post-To:"):
        first, _, rest = raw.partition("\n")
        return first[len("Post-To:"):].strip(), rest.lstrip("\n")
    return None, raw


def url_of(destination):
    """The destination line carries a URL and then a human instruction."""
    return destination.split()[0] if destination else None


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "post-queue"})
    with urllib.request.urlopen(req, timeout=20) as r:  # nosec B310 - https
        return r.read().decode("utf-8", "replace")


def verify(url):
    """Go and look. Returns (True, detail), (False, detail) or (None, why).

    WHY THIS EXISTS, and it is the sharpest lesson this repository has taught
    itself. The first version of this file asked "Enter once it is posted" and
    wrote the date into the log on that keystroke alone. On 31 October 2026 it
    recorded two replies as posted. Neither was on the forum. The log was a
    record written by the party it was about, confirming its own compliance,
    with nothing independent checking: the precise thing step-0-refusal exists
    to argue is not evidence. A tool built alongside that argument should not
    have made that mistake, and the only honest fix is to go and look.

    None means the destination cannot be checked without a credential, and
    that is reported rather than quietly treated as a pass.
    """
    m = re.search(r"forum\.canton\.network/t/(?:[^/]+/)?(\d+)", url)
    if m:
        try:
            d = json.loads(fetch("https://forum.canton.network/t/%s.json"
                                 % m.group(1)))
        except (urllib.error.URLError, ValueError) as e:
            return None, "could not reach the forum: %s" % e
        posts = d.get("post_stream", {}).get("posts", [])
        if not posts:
            return None, "no posts came back"
        last = posts[-1]
        if last.get("username") == AUTHOR:
            return True, "last post is #%s by %s at %s" % (
                last.get("post_number"), AUTHOR, last.get("created_at", "")[:16])
        return False, "last post is #%s by %s at %s, not you" % (
            last.get("post_number"), last.get("username"),
            last.get("created_at", "")[:16])

    m = re.search(r"github\.com/([^/]+/[^/]+)/pull/(\d+)", url)
    if m:
        r = run(["gh", "api", "repos/%s/issues/%s/comments" % m.groups(),
                 "--jq", ".[-1].user.login"], capture_output=True, text=True)
        if r.returncode != 0:
            return None, "gh could not read the pull request"
        who = r.stdout.strip()
        if who == GH_AUTHOR:
            return True, "last comment is by %s" % who
        return False, "last comment is by %s, not you" % (who or "nobody")

    if "forum.canton.network/c/" in url:
        return None, ("a new topic in a category, which this cannot check "
                      "without knowing the topic id. Paste its URL here next "
                      "time and it will be checkable")
    if "lists.sync.global" in url:
        return None, ("a Groups.io list, which returns 402 to automated "
                      "fetches. Check the RSS feed by eye")
    return None, "no check is written for this destination"


def main():
    # --dry-run checks every draft and prints the whole plan without touching
    # the clipboard, opening a browser or writing the log. It exists because
    # testing this tool any other way opens five browser windows on somebody
    # else's machine.
    dry = "--dry-run" in sys.argv

    sources = sorted(
        os.path.join(SOURCES, f) for f in os.listdir(SOURCES)
        if f.endswith(".txt"))
    if not sources:
        print("No sources in %s, so no quote could be checked. Stopping."
              % SOURCES)
        return 1

    done = set()
    if os.path.exists(LOG):
        with open(LOG) as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    done.add(parts[1])

    todo = [(n, why) for n, why in QUEUE if n not in done]
    print("%d of %d drafts still to post." % (len(todo), len(QUEUE)))
    if done:
        print("Already posted, per docs/drafts/posted.log: %s"
              % ", ".join(sorted(done)))
    if not todo:
        print("Nothing left. Everything in the queue is logged as posted.")
        print()
        print_optional()
        return 0
    print()

    posted = 0
    for i, (name, why) in enumerate(todo, 1):
        path = os.path.join(DRAFTS, name)
        print("=" * 72)
        print("%d of %d   %s" % (i, len(todo), name))
        print("WHY NOW: %s" % why)
        print("=" * 72)

        # Captured rather than inherited, for two reasons. The child writes
        # straight to the terminal while the parent's prints are buffered, so
        # inheriting puts every banner in the wrong place. And the child ends
        # with its own POST IT AT and "Add --copy" lines, which are correct on
        # their own and wrong here, because this queue does the copying.
        sys.stdout.flush()
        check = run([sys.executable, os.path.join(ROOT, "tools",
                                                  "before_posting.py"),
                     path] + sources, cwd=ROOT, capture_output=True, text=True)
        for line in (check.stdout + check.stderr).splitlines():
            if line.startswith("POST IT AT:") or line.startswith("Add --copy"):
                continue
            print(line)
        sys.stdout.flush()
        if check.returncode != 0:
            print()
            print("This draft did NOT pass. The queue stops here rather than")
            print("skipping it, because a skipped draft is how an unchecked")
            print("one gets posted later. Fix it and run this again.")
            return 1

        destination, body = destination_and_body(path)
        if not destination:
            print("No Post-To line in %s, so I do not know where it goes."
                  % name)
            return 1

        print()
        if dry:
            print("DRY RUN: would copy %d characters and open the page."
                  % len(body))
            print("GO HERE:  %s" % destination)
            print()
            continue

        cp = run(["pbcopy"], input=body, text=True)
        if cp.returncode == 0:
            print("The body is on your clipboard. %d characters." % len(body))
        else:
            print("pbcopy failed. Open %s and copy it by hand." % path)

        print("GO HERE:  %s" % destination)
        u = url_of(destination)
        if u:
            run(["open", u], capture_output=True)
            print("(opened in your browser)")

        print()
        ans = input("Enter once it is posted, s to skip, q to stop: ").strip()
        if ans.lower() == "q":
            print("Stopped. %d posted this run." % posted)
            return 0
        if ans.lower() == "s":
            print("Skipped, and nothing written to the log, so it comes back.")
            print()
            continue

        # Do not take the keystroke for the fact. Go and look.
        print("checking that it is actually there...")
        ok, detail = verify(url_of(destination) or "")
        if ok is False:
            print("NOT THERE: %s" % detail)
            print("Nothing written to the log, so this draft comes back.")
            print("If you did post it, the page may not have caught up: run")
            print("this again in a minute.")
            print()
            continue
        if ok is None:
            print("CANNOT CHECK: %s" % detail)
            again = input("Logging it on your word alone. Type 'yes' if it "
                          "is really posted: ").strip().lower()
            if again != "yes":
                print("Not logged, so it comes back.")
                print()
                continue
            note = "  (unverified, on your word)"
        else:
            print("CONFIRMED: %s" % detail)
            note = "  (verified)"

        with open(LOG, "a") as f:
            f.write("%s %s%s\n" % (time.strftime("%Y-%m-%d"), name, note))
        posted += 1
        print("Logged. %s" % name)
        print()

    if dry:
        print("=" * 72)
        print("DRY RUN finished. Every draft above passed its checks and")
        print("nothing was copied, opened or logged. Run it without")
        print("--dry-run to actually work through them.")
        print()
        print_optional()
        return 0

    print_optional()
    print("=" * 72)
    print("%d posted this run, and written into docs/drafts/posted.log." % posted)
    print()
    print("Commit the log so the repository records what left and when:")
    print("  git add docs/drafts/posted.log && git commit -m 'Posted the")
    print("  replies that were owed' && git push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
