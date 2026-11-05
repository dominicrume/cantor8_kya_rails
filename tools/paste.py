#!/usr/bin/env python3
"""One draft onto the clipboard, the page open, and the boxes named.

    python3 tools/paste.py radev
    python3 tools/paste.py            # lists what there is

WHY THIS EXISTS. post_queue.py walks the whole queue and asks questions.
This does one thing: it puts one draft's body on the clipboard, opens its
destination, and prints which box the text goes in and which button submits
it. Written 5 November 2026, after a new-topic title was typed into the page
of an existing thread and nothing was posted. The handover had said "paste
it, the tab is open", which is not an instruction, it is an assumption.

A draft's first block is its header: Post-To: <url>, and optionally
Title: <text>. Everything after the first blank line is the body.

Python standard library only.
"""

import os
import re
import subprocess  # nosec B404 - literal argv, shell=False, no credential
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFTS = os.path.join(ROOT, "docs", "drafts")


def parts(path):
    raw = open(path).read()
    head, _, body = raw.partition("\n\n")
    url = re.search(r"https?://\S+", head)
    title = re.search(r"^Title:\s*(.+(?:\n(?!\w+:).+)*)", head, re.M)
    return (url.group(0).rstrip(")").rstrip() if url else None,
            " ".join(title.group(1).split()) if title else None,
            body.strip())


def kind(url, title):
    """Name the boxes. A reply has no title; a new topic has two."""
    if "github.com" in url:
        return ["Scroll to the bottom comment box, headed 'Write'.",
                "Paste there.",
                "Press the green 'Comment' button."]
    if "/t/" in url:
        return ["Scroll to the very bottom of the thread.",
                "Press the grey 'Reply' button. A reply has NO title box.",
                "Paste into the editor that opens.",
                "Press the blue 'Reply' button to submit."]
    if "/c/" in url:
        return ["Press the '+ New Topic' button, top right.",
                "TITLE box: the title printed above, exactly.",
                "BODY box, the big one underneath: paste.",
                "Check the category selector reads the one in the URL.",
                "Press the blue 'Create Topic' button."]
    return ["Paste it into the message body.", "Submit it."]


def main(argv):
    names = sorted(f for f in os.listdir(DRAFTS) if f.endswith(".md")
                   and f != "posted.log")
    if len(argv) < 2:
        print("Which draft? Partial names are fine:\n")
        for n in names:
            print("  python3 tools/paste.py %s" % n[:-3])
        return 2

    want = argv[1].lower().replace(".md", "")
    hits = [n for n in names if want in n.lower()]
    if len(hits) != 1:
        print("%d drafts match %r: %s" % (len(hits), want,
                                          ", ".join(hits) or "none"))
        return 2

    path = os.path.join(DRAFTS, hits[0])
    url, title, body = parts(path)
    if not url:
        print("No Post-To line in %s." % hits[0])
        return 1

    p = subprocess.run(["pbcopy"], input=body, text=True)  # nosec B603 B607
    print("=" * 68)
    print(hits[0])
    print("=" * 68)
    if title:
        print()
        print("TITLE, copy this line by hand:")
        print()
        print("    %s" % title)
    print()
    print("BODY: %d characters, %s."
          % (len(body), "on your clipboard" if p.returncode == 0
             else "pbcopy FAILED, open %s and copy it" % path))
    print()
    print("GO TO: %s" % url)
    print()
    for i, step in enumerate(kind(url, title), 1):
        print("  %d. %s" % (i, step))
    print()
    subprocess.run(["open", url], capture_output=True)  # nosec B603 B607
    print("(opened in your browser)")
    print()
    print("Then tell me, and I will read the page back before anything is")
    print("written to docs/drafts/posted.log.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
