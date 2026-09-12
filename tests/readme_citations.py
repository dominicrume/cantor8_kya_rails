#!/usr/bin/env python3
"""Every line number the README points a judge at must still be that line.

The D1 brief says "be ready to show us the line of Daml that stops it", so the
README names lines. Line numbers rot the moment anything above them moves, and
a judge clicking through to the wrong line is worse than no link at all -- it
turns the strongest claim in the repository into a visible mistake, in front of
the person scoring it.

This is cheap insurance: it re-reads the file and checks that each cited line
still contains what the README says it contains.

Run: python3 tests/readme_citations.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANDATE = os.path.join(ROOT, "step-1-mandate", "daml", "KyaMandate.daml")
TESTS = os.path.join(ROOT, "step-1-mandate", "test", "daml", "KyaTest.daml")
README = os.path.join(ROOT, "README.md")

# The fences a judge is pointed at, by what they say rather than by where they
# sit. The line number is then READ OUT OF THE DAML, not written down here.
#
# It used to be written down here, as a second table of line numbers beside the
# README's. Adding the on-ledger refusal moved every fence about eighty lines
# down, and that meant editing the same numbers in two files to say the same
# thing, with nothing checking the check. A table of line numbers that has to
# be maintained by hand is the exact failure this file exists to catch, so it
# is gone: the phrase is the fixed point, and where it lives is a fact about
# the Daml that gets looked up.
FENCES = [
    "mandate expired",
    "amount must be positive",
    "charge would exceed the cap",
    "payee is not on the allow-list",
    "charge would exceed the period limit",
    "choice Revoke",
]


def locate(daml, phrase):
    """The one line holding this phrase, or None if it is missing or repeated.

    Repeated matters. `refusalReason` now states every rule a second time, in
    words, so "charge would exceed the cap" appears twice in the file. A lookup
    that silently took the first hit would point a judge at whichever copy came
    first, which is how this check would start lying instead of failing.
    """
    hits = [i + 1 for i, line in enumerate(daml)
            if phrase in line and line.lstrip().startswith(("assertMsg", "choice"))]
    return hits[0] if len(hits) == 1 else None


EXPECT = {}

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def check_lines(readme, daml):
    """Each fence is where the README says it is, and nowhere else."""
    cited = sorted({int(n) for n in re.findall(r"KyaMandate\.daml#L(\d+)", readme)})
    check(bool(cited), "the README cites lines in KyaMandate.daml at all")

    EXPECT.clear()
    for phrase in FENCES:
        n = locate(daml, phrase)
        check(n is not None,
              "%r is on exactly one fence line in the Daml" % phrase)
        if n is None:
            continue
        EXPECT[n] = phrase
        check(n in cited,
              "the README points at L%d for %r%s"
              % (n, phrase,
                 "" if n in cited else " (it points at %s)" % cited))

    check(set(cited) <= set(EXPECT),
          "and cites no line that is not one of those fences (cited %s, fences %s)"
          % (cited, sorted(EXPECT)))


def check_pairing(readme, daml):
    """The thing that actually breaks: a link re-pointed at a different line.

    Checking only that a cited line contains what we expect for THAT NUMBER
    passes happily when a link moves to another valid line -- the first version
    of this file did exactly that, and a deliberately corrupted link went
    undetected. So read the code the README QUOTES beside each link, and require
    the file's line to contain it.
    """
    rows = re.findall(r"KyaMandate\.daml#L(\d+)\)[^|\n]*?`([^`]+)`", readme)
    check(len(rows) >= 3, "the README quotes the code beside its links (%d)" % len(rows))
    for n, quoted in rows:
        n = int(n)
        line = daml[n - 1] if n <= len(daml) else ""
        core = quoted.replace("``", "`").strip()
        check(core.split("(")[0].strip() in line,
              "L%d is the line the README quotes (%.44s)" % (n, core))


def check_tests(readme, tests):
    """Every named test the README promises a judge can run."""
    for t in re.findall(r"`(test[A-Za-z0-9_]+)`", readme):
        check((t + " :") in tests or (t + " =") in tests,
              "%s exists in KyaTest.daml" % t)


def main():
    readme = open(README).read()
    daml = open(MANDATE).read().splitlines()
    tests = open(TESTS).read()

    print("the lines the README shows a judge")
    check_lines(readme, daml)
    check_pairing(readme, daml)
    check_tests(readme, tests)
    check(daml_fences(daml) == 6,
          "KyaMandate.daml still has 6 assertMsg fences (found %d)" % daml_fences(daml))

    print()
    if fails:
        print("README CITATIONS FAILED - %d:" % len(fails))
        for f in fails:
            print("  -", f)
        print("\nA judge clicking one of these would land on the wrong line.")
        return 1
    print("every line and test the README points at is still there.")
    return 0


def daml_fences(lines):
    """Fences, not mentions.

    This counted every line containing "assertMsg", which includes the comment
    above ChargeRefused explaining what assertMsg does to a refusal. Prose
    about a fence is not a fence, and a lint that cannot tell the difference
    pushes you to write worse comments to keep it quiet.
    """
    return sum(1 for l in lines
               if l.lstrip().startswith("assertMsg"))


if __name__ == "__main__":
    sys.exit(main())
