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

import os
import subprocess  # nosec B404 - literal argv, shell=False. The only values
                   # passed are paths from QUEUE below and a destination read
                   # from the draft's own first line.
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFTS = os.path.join(ROOT, "docs", "drafts")
SOURCES = os.path.join(DRAFTS, "sources")
LOG = os.path.join(DRAFTS, "posted.log")

# Oldest debt first, and the new topic last so that when it says the others
# have already been answered, that is true at the moment it is posted.
QUEUE = [
    ("reply-radev-9323.md",
     "Georgi Radev answered a direct question on 27 October and has had "
     "nothing back. Longest debt, so it goes first."),
    ("reply-leonid-9114.md",
     "Leonid corrected the Motivation on 30 October. While the page is open, "
     "tick PREDGE's post 6 as the solution. You told him on 26 October that "
     "you had, and it is still false."),
    ("reply-karnatak-9084.md",
     "Arpit Karnatak of Vacuumlabs, waiting since 18 October, and your own "
     "question to him has been open since 22 October."),
    ("reply-meier-cip-discuss.md",
     "Simon Meier, author of eight CIPs. The hardest one, and the one where "
     "the draft has changed since the list saw it."),
    ("post-sig-security.md",
     "A new topic in SIG Security, which holds two posts and is nine days "
     "old. Post this LAST: it says the others have already corrected the "
     "draft, which is only true once they are in."),
]


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

        with open(LOG, "a") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%d"), name))
        posted += 1
        print("Logged. %s" % name)
        print()

    if dry:
        print("=" * 72)
        print("DRY RUN finished. Every draft above passed its checks and")
        print("nothing was copied, opened or logged. Run it without")
        print("--dry-run to actually work through them.")
        return 0

    print("=" * 72)
    print("%d posted this run, and written into docs/drafts/posted.log." % posted)
    print()
    print("Commit the log so the repository records what left and when:")
    print("  git add docs/drafts/posted.log && git commit -m 'Posted the")
    print("  replies that were owed' && git push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
