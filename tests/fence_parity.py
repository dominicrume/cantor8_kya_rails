#!/usr/bin/env python3
"""The fence that aborts and the fence that records must say the same thing.

`Charge` refuses with assertMsg, which aborts the transaction and leaves the
ledger empty. `TryCharge` reads the same rules through `refusalReason` and
writes a ChargeRefused contract instead. Two copies of the rules is the price
of having a refusal that survives, and the risk it buys is drift: the ledger
record hands a regulator a reason that is not the reason that fired.

That drift would be silent. Both halves compile, every Daml test passes, and
the wrong word only shows up in a document somebody is relying on.

So the two lists are compared here, by message, and a mismatch fails the build.
The messages are the join, deliberately: they are what ends up in front of a
reader, so they are the thing that has to match.

Run: python3 tests/fence_parity.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DAML = os.path.join(ROOT, "step-1-mandate", "daml", "KyaMandate.daml")

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


src = open(DAML).read()


def section(start, end):
    """The text between two markers, so a rule in Adjust is not read as a rule
    in Charge. Adjust has an assertMsg too, and counting it would make the two
    lists disagree forever over a rule that has nothing to do with charging."""
    a = src.index(start)
    b = src.index(end, a)
    return src[a:b]


charge = section("    choice Charge :", "    -- | The same rules, recorded")
reason = section("refusalReason : KyaMandate", "-- The rolling window")

asserted = re.findall(r'assertMsg\s+"([^"]+)"', charge)
recorded = re.findall(r'=\s*Some\s+"([^"]+)"', reason)

print("the rule that aborts and the rule that is recorded")
check(len(asserted) > 0, "Charge still states its rules with assertMsg (%d)" % len(asserted))
check(len(recorded) > 0, "refusalReason still returns a reason per rule (%d)" % len(recorded))

missing = [m for m in asserted if m not in recorded]
check(not missing,
      "every rule Charge aborts on is a rule TryCharge records"
      + (": missing %s" % missing if missing else ""))

extra = [m for m in recorded if m not in asserted]
check(not extra,
      "and TryCharge records nothing Charge does not enforce"
      + (": %s" % extra if extra else ""))

# Order, not only membership. The first rule that says no is the reason that
# gets written down, so two implementations that refuse in a different order
# hand a reader a different answer for the same attempt. A mandate that is both
# expired and over its cap should report the same rule either way.
check(asserted == recorded,
      "and they fire in the same order, so the same attempt gets the same reason")

# The Daml test that holds each recorded message to its own fence. Without
# these, the lists above could agree with each other and both be wrong.
tests = open(os.path.join(ROOT, "step-1-mandate", "test", "daml", "KyaTest.daml")).read()
for message in asserted:
    check('== "%s"' % message in tests,
          '  "%s" is asserted by a named Daml test' % message)

print()
if fails:
    print("FENCE PARITY FAILED - %d:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("the refusal a regulator reads names the rule that actually fired.")
