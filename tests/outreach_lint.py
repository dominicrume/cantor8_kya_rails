#!/usr/bin/env python3
"""Anything we are about to send a stranger is short, plain, and in their words.

Two replies sat unsent for two days and the first drafts of both were wrong in
the same way: 254 and 281 words, average sentence 13 and 18, one sentence of 57
words. They explained our mechanism to people who had not asked about it. One
of them had asked twice, in plain words, for us to stop doing that.

They also used none of the other person's vocabulary. Mr_Tuddles wrote
"deterministic settlement", "agentic registry" and "porting to Canton
natively". Federico named the thing "RejectedAttempt" and named its
"trade-off". Neither draft contained a single one of those. Replying to
somebody in your own vocabulary is a way of not listening, and it reads like
one.

So the limits are checked rather than remembered:

  * 200 words a block. Their posts are three sentences; ours were a page.
  * 20 words a sentence, and an average under 12.
  * their words, not only ours.

`hard word` here means long AND not in the small common list below. The list is
short on purpose: this is a smell test, not a reading grade, and it is allowed
to be crude because the fix is always the same, which is to write a shorter
sentence.

Run: python3 tests/outreach_lint.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMON = set("""a about after all also an and any are as ask at back be been before but by
call came can check code come could day deal decide did do does done down each
end even every few find first for from get give go got had has have he her here
him his how i if in into is it its just keep know last leave let like little
long look made make man many may me might money more most much must my name
need never new next no not now of off old on one only or other our out over own
part pay people place put ran read real record rest right run said same say see
send set she should show side small so some stop such take tell than that the
their them then there these they thing think this those thought three through
time to too took two under up us use used very want was way we well went were
what when where which while who why will with word work would write you your
built build rule rules refuse refused refusal page file drop test tests ledger
agent agents payment payments""".split())
def hard(w):
    w = re.sub(r"[^a-z]", "", w.lower())
    return bool(w) and w not in COMMON and len(w) > 7
def blocks_in(path):
    return re.findall(r"```\n(.*?)\n```", open(path).read(), re.S)


fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


# Whatever is currently drafted to send. Renamed when it goes out, so this
# list is the outbox rather than an archive: a lint that checks a sent message
# is checking something nobody can act on.
TARGETS = [p for p in [
    os.path.join(ROOT, "docs", "outreach", "sent-2026-09-13.md"),
    os.path.join(ROOT, "docs", "outreach",
                 "post-what-a-ledger-does-not-record.md"),
    os.path.join(ROOT, "docs", "outreach", "ask-cantor8-for-devnet.md"),
    os.path.join(ROOT, "docs", "outreach", "webinar-wednesday-16-sept.md"),
] if os.path.exists(p)]

# Words the RECIPIENT used, which a reply has to contain or it is not a reply
# to them. Keyed by file, because the rule only applies to a reply: a new topic
# has no addressee, and demanding somebody's vocabulary in a post they have not
# written yet is the check misfiring rather than the draft being wrong.
THEIRS = {
    "sent-2026-09-13.md": ["deterministic settlement", "agentic registry",
                           "porting to Canton", "RejectedAttempt", "trade-off"],
    "post-what-a-ledger-does-not-record.md": [],
    "ask-cantor8-for-devnet.md": [],
    "webinar-wednesday-16-sept.md": [],
}

for path in TARGETS:
    name = os.path.basename(path)
    print("what we are about to send: %s" % name)
    text = open(path).read()
    blocks = blocks_in(path)
    check(bool(blocks), "  it has something to paste (%d block(s))" % len(blocks))
    for i, b in enumerate(blocks, 1):
        b = re.sub(r"https?://\S+", "LINK", b)
        sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+", b.replace("\n", " "))
                 if x.strip()]
        words = b.split()
        lens = [len(x.split()) for x in sents] or [0]
        longest = max(sents, key=lambda x: len(x.split())) if sents else ""
        check(len(words) <= 200,
              "  block %d is %d words (limit 200)" % (i, len(words)))
        check(sum(lens) / len(lens) <= 12,
              "  block %d averages %.1f words a sentence (limit 12)"
              % (i, sum(lens) / len(lens)))
        check(max(lens) <= 20,
              "  block %d's longest sentence is %d words (limit 20): %s"
              % (i, max(lens), longest[:56]))
    # Inside the paste blocks, not anywhere in the file. The prose above them
    # explains who these people are and naturally repeats their vocabulary, so
    # checking the whole file passed while the reply itself said none of it.
    # The mutation harness caught that: swapping "agentic registry" out of the
    # block left this green, because the word was still in my own notes.
    sent = "\n".join(blocks).lower()
    wanted = THEIRS.get(name)
    check(wanted is not None,
          "  %s is listed in THEIRS, so somebody decided whether it is a reply"
          % name)
    missing = [t for t in (wanted or []) if t.lower() not in sent]
    check(not missing,
          "  the blocks use their words, not only ours"
          + (": missing %s" % missing if missing else "")
          if wanted else "  no addressee, so no vocabulary is required")
    print()

# No em dashes. A standing rule, and outreach is where it matters most.
for path in TARGETS:
    check("\u2014" not in open(path).read(),
          "%s has no em dashes" % os.path.basename(path))

print()
if fails:
    print("FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("short enough to read, plain enough to follow, and in the vocabulary of")
print("the person it is addressed to.")
