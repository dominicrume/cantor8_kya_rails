#!/usr/bin/env python3
"""Check a draft BEFORE it is posted. Exit 1 means do not post it.

WHY THIS EXISTS, with the date and the failure.

On 31 October 2026 a comment went onto canton-foundation/canton-dev-fund#866,
somebody else's funding proposal. It quoted a sentence back at its authors and
linked a document in this repository. Both turned out to be correct. Both were
verified AFTER the comment was posted, and only because the owner asked.

The same day, a reply was drafted describing a forum poster as working at
Digital Asset. He does not. The affiliation had been inferred from the quality
of his writing and from a file path he cited, and nothing had been checked.

Neither failure was a lack of care in the moment. Both were the wrong ORDER:
build the message, post it, verify afterwards. That order produces a correct
message most of the time, which is exactly why it survives. The cost arrives
on the day it does not, in somebody else's repository, under your own name,
permanently.

So the order is fixed here rather than remembered:

    python3 tools/before_posting.py <draft file> [source file ...]

What it checks, mechanically:

1. EVERY QUOTE IS IN A SOURCE. Any "double quoted span" of more than four
   words in the draft must appear verbatim in one of the source files given on
   the command line. A quote with no source is the #866 failure.

2. EVERY LINK TO THIS REPOSITORY RESOLVES. A github.com/dominicrume/... blob
   link must name a file that exists, is committed, and is pushed, because a
   reader following it gets a 404 otherwise.

3. STALENESS IS SHOWN, NOT GUESSED. For each such file the tool prints the
   date of its last commit next to the date of HEAD. It cannot know whether a
   document is out of date. It can refuse to let you link one without being
   told how old it is, which is the part that went wrong.

4. EVERY AFFILIATION IS SOURCED. A sentence asserting that a named person is
   "at", "of" or "works at" an organisation must carry a URL on the same line
   or in a `Sources:` block. Inferred affiliations are how the second failure
   happened.

What it CANNOT check, stated so nobody mistakes a pass for a proofread: that a
quote is in context, that a claim is true, that the tone is right, or that the
document you linked still says what you think. It checks the order, not the
content.

Python standard library only. No network: every check is local, so it runs
before you are online with the thing you are about to send.
"""

import os
import re
import subprocess  # nosec B404 - every call below is a literal git argv with
                   # shell=False, and no part of a draft reaches it. The only
                   # external value passed to git is a path that came out of a
                   # regex over our own repository link format.
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The positive control. A scan that finds nothing looks exactly like a scan
# that looked nowhere, so this file proves it can catch each failure it was
# written for before it is allowed to pass anything. The two cases are the
# real ones from 31 October 2026.
CONTROL_DRAFT = """
Thanks for this. You wrote "a sentence nobody has ever
written anywhere at all" and I agree.

Leonid at Digital Asset reviewed it.

See https://github.com/dominicrume/cantor8_kya_rails/blob/main/docs/no-such-file.md
"""
# The control's quote WRAPS across a line, because the version of this file
# that did not allow that reported zero quotes in a real draft and passed it.
# The control carries each failure in the shape it actually arrived in.
# Note the control says "Leonid", one word, not "Simon Meier", two. The first
# version of this file used the two-word name and passed, while the real
# sentence that went wrong on 31 October 2026 named a single first name and
# slipped straight through the check written to catch it. A control easier than
# the case it stands for is not a control.


def git(*args):
    r = subprocess.run(  # nosec B603 B607 - literal argv, no shell
        ["git"] + list(args), cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


# A quote may WRAP. The first version of this pattern was r'"([^"\n]{20,400})"'
# and the newline exclusion made every quote in a hard-wrapped file invisible:
# run against the four replies on 31 October 2026 it reported zero quotes in a
# draft that quotes Vacuumlabs across two lines, and passed it. A check that
# cannot see the thing it checks is worse than no check, because it prints
# reassurance. Newlines are allowed now and a blank line ends a quote, so one
# stray quotation mark cannot swallow a page.
QUOTE = re.compile(r'"([^"]{20,400})"')
REPO_LINK = re.compile(
    r"https://github\.com/dominicrume/[A-Za-z0-9_.-]+/blob/[A-Za-z0-9_.-]+/([^\s)\]]+)")
URL = re.compile(r"https?://\S+")
# "Simon Meier at Digital Asset", "Leonid of C7", "Arpit Karnatak works at X".
# ONE name word is enough, because the sentence that went wrong said "Leonid".
# This over-matches: "Canton of England" would trip it. That is the right way
# round. A false positive costs five seconds of reading. A false negative costs
# a correction in public, under your own name, permanently.
AFFIL = re.compile(
    r"\b([A-Z][a-z'`-]{2,}(?: [A-Z][a-z'`-]+){0,2})\s+"
    r"(?:works at|at|of|from)\s+([A-Z][A-Za-z0-9&.'-]+(?: [A-Z][A-Za-z0-9&.'-]+)*)")


def normalise(text):
    """Quotes get re-typed. Compare on words, not on whitespace or curls."""
    text = (text.replace("’", "'").replace("‘", "'")
                .replace("“", '"').replace("”", '"')
                .replace("—", " ").replace("–", " "))
    return " ".join(text.split()).lower()


def check(draft_text, sources, label, verbose=True):
    """Returns a list of failures. Empty means the draft may be posted."""
    fails = []
    say = (lambda *a: print(*a)) if verbose else (lambda *a: None)

    haystack = normalise("\n".join(sources.values()))

    # 1. quotes. A blank line is a paragraph break, never the inside of a
    # quotation, so it ends one: that keeps an unbalanced quotation mark from
    # matching across half the draft.
    quotes = [q for q in QUOTE.findall(draft_text)
              if len(q.split()) > 4 and "\n\n" not in q]
    say("  quotes of more than four words: %d" % len(quotes))
    for q in quotes:
        if normalise(q) not in haystack:
            fails.append("QUOTE NOT IN ANY SOURCE: \"%s\"" % q[:90])

    # 2 and 3. links into this repository
    links = REPO_LINK.findall(draft_text)
    say("  links into this repository: %d" % len(links))
    head_date = git("log", "-1", "--format=%ad", "--date=short")
    for path in links:
        full = os.path.join(ROOT, path)
        if not os.path.exists(full):
            fails.append("LINKED FILE DOES NOT EXIST: %s" % path)
            continue
        tracked = git("ls-files", "--error-unmatch", path)
        if not tracked:
            fails.append("LINKED FILE IS NOT COMMITTED: %s" % path)
            continue
        if git("status", "--porcelain", path):
            fails.append("LINKED FILE HAS UNCOMMITTED CHANGES: %s" % path)
            continue
        if git("log", "origin/main..HEAD", "--oneline", "--", path):
            fails.append("LINKED FILE IS COMMITTED BUT NOT PUSHED: %s" % path)
            continue
        when = git("log", "-1", "--format=%ad", "--date=short", "--", path)
        behind = git("log", "--oneline", "%s..HEAD" % git(
            "log", "-1", "--format=%H", "--", path), "--", ".")
        n = len(behind.splitlines()) if behind else 0
        say("    %s" % path)
        say("      last changed %s, HEAD is %s, %d commit(s) to the tree since"
            % (when, head_date, n))
        if n:
            say("      ^ SAY OUT LOUD whether any of those %d changed what this"
                " file claims. The tool cannot know." % n)

    # 4. affiliations
    sourced_lines = 0
    for line in draft_text.splitlines():
        for who, org in AFFIL.findall(line):
            if URL.search(line) or "Sources:" in draft_text:
                sourced_lines += 1
                continue
            fails.append(
                "AFFILIATION WITH NO SOURCE ON THE LINE: \"%s\" at \"%s\". "
                "This is the Leonid failure. Put the URL you checked, or cut "
                "the organisation." % (who, org))
    # "0" on its own was ambiguous here: a reader could not tell whether it
    # meant no claims were made or claims were made and none were sourced.
    # The second is a failure and the first is nothing, so they are now
    # different sentences.
    if sourced_lines:
        say("  affiliation claims: %d, each carrying a source on its line"
            % sourced_lines)
    else:
        say("  affiliation claims: none made, so none to source")

    return fails


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2

    # The control runs first, every time. If it does not catch the two
    # failures this file exists for, nothing it says about your draft is worth
    # reading.
    control_fails = check(CONTROL_DRAFT, {"a": "nothing relevant in here"},
                          "control", verbose=False)
    want = ["QUOTE NOT IN ANY SOURCE", "LINKED FILE DOES NOT EXIST",
            "AFFILIATION WITH NO SOURCE"]
    for w in want:
        if not any(f.startswith(w) for f in control_fails):
            print("FAIL the control: this file did not catch %s, which is one "
                  "of the two failures it was written for. Fix the tool "
                  "before trusting it on a draft." % w)
            return 1
    print("control: the three known failures are all caught, so the checks run.")
    print()

    copy = "--copy" in argv
    argv = [a for a in argv if a != "--copy"]

    draft_path = argv[1]
    with open(draft_path) as f:
        raw = f.read()

    # A draft may name where it goes, on a first line reading
    # "Post-To: <url>". The tool strips it, so the body printed and copied is
    # exactly what the recipient sees and the destination never travels with
    # it. Knowing a draft is safe and not knowing where to put it is still
    # friction, and friction is where a step gets skipped.
    destination = None
    draft = raw
    if raw.startswith("Post-To:"):
        first, _, rest = raw.partition("\n")
        destination = first[len("Post-To:"):].strip()
        draft = rest.lstrip("\n")

    sources = {}
    for p in argv[2:]:
        try:
            with open(p) as f:
                sources[p] = f.read()
        except OSError as e:
            print("cannot read source %s: %s" % (p, e))
            return 1

    print("checking %s against %d source file(s)" % (draft_path, len(sources)))
    fails = check(draft, sources, draft_path)
    print()

    if fails:
        print("DO NOT POST. %d problem(s):" % len(fails))
        for f in fails:
            print("  - %s" % f)
        print()
        print("Every one of these is checkable in less time than the")
        print("correction costs. The correction happens in public.")
        return 1

    print("The mechanical checks pass. They do not say the draft is right.")
    print("They say every quote has a source, every link resolves, and every")
    print("affiliation carries one. Read it once more, then post.")

    if destination:
        print()
        print("POST IT AT: %s" % destination)

    if copy:
        r = subprocess.run(  # nosec B603 B607 - literal argv, no shell
            ["pbcopy"], input=draft, text=True)
        if r.returncode == 0:
            print("The body is on your clipboard, without the Post-To line.")
        else:
            print("pbcopy failed, so copy it from the file by hand.")
    elif destination:
        print("Add --copy to put the body on your clipboard.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
