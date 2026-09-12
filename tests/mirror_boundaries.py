#!/usr/bin/env python3
"""The Python mirror refuses at the same boundaries as the Daml.

tests/fence_parity.py holds all four copies of the spending rules to each other
by MESSAGE and by ORDER. That is not the same as holding them to each other by
BEHAVIOUR, and the difference is not academic: flipping `>` to `>=` in one Daml
copy passed fence_parity, passed fence_lint and passed every Daml script, and
made a charge landing exactly on the cap refused by one path and accepted by
the other. `testChargeAndTryChargeAgreeOnTheCapBoundary` closed that for the
two Daml copies. This closes it for the Python one.

MockLedger.charge is what the demo runs and what most tests run, so a boundary
that drifts there drifts in front of the reader.

The cases are the same cases as the Daml agreement test, deliberately: exactly
on the cap, a hundredth under, a hundredth over, zero, negative, and a payee
nobody authorised. If the two files ever disagree about what the boundary is,
one of these goes red.

What this does NOT do: call the Daml. It pins the mock to the boundaries the
Daml is itself pinned to by bothAgree, which is two padlocks on the same door
rather than one chain between them. Said plainly because the difference matters
if anybody ever changes the boundary on purpose -- they will have to change it
in both places, and both suites will tell them so.

Run: python3 tests/mirror_boundaries.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "step-2-agent"))

from agent import MockLedger                                  # noqa: E402

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def verdict(prespend, amount, payee="customer", cap=100.0, **kw):
    """One attempt against a fresh mandate, after an optional earlier spend."""
    led = MockLedger()
    led.open_mandate(cap=cap, allowed=["customer", "partner"], **kw)
    if prespend:
        outcome, rule = led.charge(prespend, "customer")
        assert outcome == "ACCEPTED", "setup spend was refused: %s" % rule
    return led.charge(amount, payee)


print("the cap boundary, from both sides")
# Charge asserts `spent + amount <= cap`, so landing exactly on the cap is
# ALLOWED. This is the case that diverged in the Daml and the one most likely
# to be got wrong again, in either file.
check(verdict(0, 100.0)[0] == "ACCEPTED",
      "exactly the cap is allowed: spent + amount <= cap")
check(verdict(0, 99.99)[0] == "ACCEPTED", "  a hundredth under is allowed")
outcome, rule = verdict(0, 100.01)
check(outcome == "REFUSED" and rule == "charge would exceed the cap",
      "  a hundredth over is refused, by the cap rule (%s)" % rule)
check(verdict(60.0, 40.0)[0] == "ACCEPTED",
      "reaching the cap exactly after an earlier spend is allowed")
check(verdict(60.0, 40.01)[0] == "REFUSED",
      "  and a hundredth past it is not")

print()
print("the amount boundary")
outcome, rule = verdict(0, 0.0)
check(outcome == "REFUSED" and rule == "amount must be positive",
      "zero is not a positive amount (%s)" % rule)
check(verdict(0, -0.01)[0] == "REFUSED", "  negative is refused")
check(verdict(0, 0.01)[0] == "ACCEPTED",
      "  and the smallest positive amount is allowed")

print()
print("the allow-list, which is about WHO and not about how much")
outcome, rule = verdict(0, 10.0, payee="stranger")
check(outcome == "REFUSED" and rule == "payee is not on the allow-list",
      "an unauthorised payee is refused, by the allow-list rule (%s)" % rule)
check(verdict(0, 10.0, payee="partner")[0] == "ACCEPTED",
      "  and the same amount to an authorised one is allowed")

print()
print("which rule fires first, when more than one would")
# The order is the order Charge states them, and it is what a reader is told
# happened. An attempt that is both over the cap and to a stranger must report
# the cap, because the cap assertion comes first in the choice body.
outcome, rule = verdict(0, 500.0, payee="stranger")
check(rule == "charge would exceed the cap",
      "over the cap AND unauthorised reports the cap, as Charge orders them (%s)"
      % rule)
outcome, rule = verdict(0, -1.0, payee="stranger")
check(rule == "amount must be positive",
      "  and a negative amount beats the allow-list, for the same reason (%s)"
      % rule)

print()
print("the period window, which is a second ceiling under the first")
outcome, rule = verdict(0, 20.0, cap=100.0, period_limit=20.0,
                        period_seconds=86400)
check(outcome == "ACCEPTED", "exactly the period limit is allowed")
outcome, rule = verdict(0, 20.01, cap=100.0, period_limit=20.0,
                        period_seconds=86400)
check(outcome == "REFUSED" and rule == "charge would exceed the period limit",
      "  a hundredth over it is refused, by the period rule (%s)" % rule)
# The window is the tighter ceiling here, so it must fire even though the total
# cap has plenty of room. A mirror that checked only the cap would pass every
# test above this line.
check(verdict(0, 50.0, cap=100.0, period_limit=20.0,
              period_seconds=86400)[1] == "charge would exceed the period limit",
      "  and it fires while the total cap still has room")

print()
if fails:
    print("FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("the demo refuses exactly where the contract refuses, at every edge")
print("either of them could have been got wrong at.")
