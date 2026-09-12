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


def alternatives(src):
    """The rule names inside devnet_ledger's RULES pattern.

    The pattern is written as several adjacent r"..." literals so it fits the
    line length, and the alternation bars fall at the seams. A first version of
    this read the source with one regex, found four of the six, and reported
    the other two as drift: a check failing on its own bug rather than on the
    code, which is the worst kind, because it teaches you to distrust the
    check. So join the literals first, strip the grouping parens, split on the
    bar.
    """
    block = re.search(r"RULES = re\.compile\(\s*(.*?)\)\s*\n\s*\n", src, re.S)
    if not block:
        return []
    joined = "".join(re.findall(r'r"([^"]*)"', block.group(1)))
    return [a for a in joined.strip("()").split("|") if a]


charge = section("    choice Charge :", "    -- | The same rules, recorded")
# Adjust states a rule too, and devnet_ledger's regex matches it. It is not a
# Charge fence, so it is held separately rather than being allowed to look like
# drift in either direction.
adjust_rules = re.findall(r'assertMsg\s+"([^"]+)"',
                          section("    choice Adjust :", "template KyaMandateProposal"))
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

# The THIRD copy, which is the one people actually see.
#
# MockLedger.charge in step-2-agent/agent.py restates the same rules in Python.
# Its docstring says it "mirrors the assertions in KyaMandate.daml, line for
# line", and until this check existed nothing held it to that. The mock is what
# the demo runs and what most tests run, so a rule that drifts there is a rule
# that drifts in front of the reader while every Daml test stays green.
mock_src = open(os.path.join(ROOT, "step-2-agent", "agent.py")).read()
mock_charge = mock_src[mock_src.index("    def charge(self, amount, payee):"):]
mock_charge = mock_charge[:mock_charge.index("\n    def ")]
mock_said = re.findall(r'return "REFUSED", "([^"]+)"', mock_charge)

print()
print("and the Python mirror, which is what the demo actually runs")
check(bool(mock_said), "MockLedger.charge still refuses with named rules (%d)"
      % len(mock_said))

# The mock refuses one thing the Daml choice body does not: a revoked mandate.
# On the ledger Revoke is consuming, so there is no contract left to charge
# against and no assertion is needed. The mock has no such thing as an archived
# contract, so it carries the rule explicitly. Named here rather than filtered
# silently, because an unexplained exception is how a real drift gets waved
# through.
NOT_IN_DAML = ["Revoke: mandate no longer active on the ledger"]
mock_rules = [m for m in mock_said if m not in NOT_IN_DAML]
check(all(any(n in m for n in NOT_IN_DAML) or m in asserted for m in mock_said),
      "  every rule the mock states is a rule the contract states"
      + ("" if all(m in asserted for m in mock_rules)
         else ": %s" % [m for m in mock_rules if m not in asserted]))
missing_from_mock = [m for m in asserted if m not in mock_said]
check(not missing_from_mock,
      "  and every rule the contract enforces, the mock enforces too"
      + (": missing %s" % missing_from_mock if missing_from_mock else ""))
check(mock_rules == [m for m in asserted if m in mock_rules],
      "  in the same order, so the same attempt gets the same reason on both")

# The FOURTH copy, and the one that reaches a real receipt.
#
# step-2-agent/devnet_ledger.py cannot read the rule off the ledger on the
# Charge path, because a failed assertMsg aborts and there is nothing to read.
# So it regex-matches the assertion message out of the gRPC error string. If a
# rule is renamed in the Daml, the regex silently stops matching and _rule()
# falls through to `m[:110]`: the receipt's `rule` field becomes a truncated
# error string instead of a rule name, on the real rail, with every test green.
#
# This copy is the reason TryCharge exists. A ChargeRefused contract carries
# the rule as a field, so it is read rather than parsed. Until the DevNet path
# is wired onto TryCharge, this check is what stands between a rename and a
# meaningless `rule` in somebody's audit trail.
dn_src = open(os.path.join(ROOT, "step-2-agent", "devnet_ledger.py")).read()
dn_said = alternatives(dn_src)

print()
print("and the regex that names the rule on the real rail")
check(bool(dn_said), "devnet_ledger still lists the assertion messages (%d)"
      % len(dn_said))
missing_from_dn = [m for m in asserted if m not in dn_said]
check(not missing_from_dn,
      "  every rule Charge can abort on is one the receipt can still name"
      + (": missing %s" % missing_from_dn if missing_from_dn else ""))
stale_in_dn = [m for m in dn_said if m not in asserted and m not in adjust_rules]
check(not stale_in_dn,
      "  and it matches nothing the contract no longer says"
      + (": %s" % stale_in_dn if stale_in_dn else ""))

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
