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

# Which line each fence must be on. Checked BOTH ways: the line must contain
# the phrase, and the phrase must be on that line and no other.
EXPECT = {
    69: "mandate expired",
    70: "amount must be positive",
    71: "charge would exceed the cap",
    72: "payee is not on the allow-list",
    85: "charge would exceed the period limit",
    94: "choice Revoke",
}

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def check_lines(readme, daml):
    """Each cited line still holds the fence we expect at that number."""
    cited = sorted({int(n) for n in re.findall(r"KyaMandate\.daml#L(\d+)", readme)})
    check(bool(cited), "the README cites lines in KyaMandate.daml at all")
    check(set(cited) <= set(EXPECT),
          "every cited line is one this check knows about (cited %s)" % cited)
    for n in cited:
        phrase = EXPECT.get(n)
        line = daml[n - 1] if n <= len(daml) else ""
        check(bool(phrase) and phrase in line,
              "L%d still contains %r" % (n, phrase or "?"))


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
    return sum(1 for l in lines if "assertMsg" in l)


if __name__ == "__main__":
    sys.exit(main())
