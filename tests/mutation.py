#!/usr/bin/env python3
"""Delete each fence in turn and prove a test goes red.

A green suite says the code passes its tests. It does not say the tests would
notice if a fence were removed -- and that is the only property that matters
for a contract whose whole job is refusing things.

This found a real gap: deleting the cap assertion left testOverCapRefused
passing, because `ensure spent <= cap` catches the same condition. The money
was safe; the test was not. Every fence below is now covered by a test that
distinguishes it.

Run: python3 tests/mutation.py        (slow: one daml test run per fence)
"""
import os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "..", "step-1-mandate")
TESTPKG = os.path.join(PKG, "test")
MANDATE = os.path.join(PKG, "daml", "KyaMandate.daml")
QUOTE = os.path.join(PKG, "daml", "KyaQuote.daml")

# (source file, fence text, a test that MUST fail when that line is deleted)
FENCES = [
    (MANDATE, "mandate expired",                      "testAfterExpiryRefused"),
    (MANDATE, "amount must be positive",              "testAmountMustBePositive"),
    (MANDATE, "charge would exceed the cap",          "testOverCapRefusedByTheCapAssertion"),
    (MANDATE, "payee is not on the allow-list",       "testPayoutRedirectionRefused"),
    (MANDATE, "charge would exceed the period limit", "testPeriodLimitRefusedWithinWindow"),
    (MANDATE, "new cap below what is already spent",  "testAdjustBelowSpentRefused"),
    # KyaQuote: the fences that stop the loss the desk actually took.
    (QUOTE, "quote expired",                          "testStaleQuoteCannotBeFulfilled"),
    (QUOTE, "deposit does not carry this quote",      "testDepositWithoutTheQuoteReferenceIsRefused"),
    (QUOTE, "amount does not match the quote",        "testAmountMustMatchTheQuote"),
    (QUOTE, "payout account does not match",          "testClaimantCannotRedirectToTheirOwnAccount"),
    (QUOTE, "payout account has not been approved",    "testOperatorCannotQuoteToTheirOwnAccount"),
]


def run_suite():
    """Rebuild the mandate, then run the scripts from their own package.

    The test package takes the built DAR as a data-dependency, so a mutated
    mandate only reaches the tests after a rebuild. Skipping the rebuild would
    silently test the previous DAR and report every fence as covered.
    """
    b = subprocess.run(["daml", "build", "--no-legacy-assistant-warning"],
                       cwd=PKG, capture_output=True, text=True)
    if b.returncode != 0:
        return "BUILD FAILED\n" + b.stdout + b.stderr
    p = subprocess.run(["daml", "test", "--no-legacy-assistant-warning"],
                       cwd=TESTPKG, capture_output=True, text=True)
    return p.stdout + p.stderr


def delete_line(path, containing):
    src = open(path).read()
    kept = [l for l in src.splitlines() if containing not in l]
    if len(kept) == len(src.splitlines()):
        return False
    open(path, "w").write("\n".join(kept) + "\n")
    return True


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    backups = {p: tempfile.mktemp(suffix=".daml") for p in (MANDATE, QUOTE)}
    for p, b in backups.items():
        shutil.copy(p, b)
    failures = []
    try:
        baseline = run_suite()
        n = len(re.findall(r"^daml/KyaTest.*: ok", baseline, re.M))
        print("baseline: %d scripts green\n" % n)

        for path, fence, guard in FENCES:
            if only and only not in fence:
                continue
            for p, b in backups.items():
                shutil.copy(b, p)
            if not delete_line(path, fence):
                print("  SKIP  %-38s (assertion not found)" % fence[:38])
                failures.append("%s: assertion text not present" % fence)
                continue
            out = run_suite()
            if guard + ": ok" in out:
                print("  BLIND %-38s -> %s still passes" % (fence[:38], guard))
                failures.append("%s is not covered: %s stays green without it"
                                % (fence, guard))
            elif guard not in out:
                print("  ????  %-38s -> %s did not run" % (fence[:38], guard))
                failures.append("%s: guard test %s did not run" % (fence, guard))
            else:
                print("  ok    %-38s -> %s goes red" % (fence[:38], guard))
    finally:
        for p, b in backups.items():
            shutil.copy(b, p)
            os.unlink(b)

    print()
    if failures:
        print("MUTATION TESTING FAILED - %d fence(s) not covered:" % len(failures))
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("every fence is covered: deleting any one of them turns a test red.")


if __name__ == "__main__":
    main()
