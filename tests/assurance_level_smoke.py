#!/usr/bin/env python3
"""The level is what the verifier established, never what the document claims.

A chain that holds proves nothing was edited. It does not prove who decided,
and until those are told apart both are answered in the strongest word the
format has.

The mechanism is one rule: **derive, never read.** A level a producer could
write down is a level a producer could assert into being, and the format would
then record the over-claim rather than prevent it. So `ledger` may read
"Canton DevNet, an independent validator refused this" in a chain no ledger
ever saw -- every seal verifies, and the level is still `self-attested`.

There is deliberately no `ledger-enforced`. Whether an assertion actually ran
is not a property of the document and no commitment scheme reaches it, which
is the same limit that stops a proof of solvency establishing that the assets
exist. Offering the level would be offering a word the reader could mistake
for one we established.

Run: python3 tests/assurance_level_smoke.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "pkg", "src"))

from knowyouragenticai_receipts import (                    # noqa: E402
    ANCHORED, SELF_ATTESTED, Chain, Policy, assurance, guard)

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def honest():
    p = Policy(cap="100.00", currency="USD", allow=["acme"])
    c = p.open()

    @guard(p, c)
    def pay(amount, payee):
        return "ok"
    pay("10.00", "acme")
    return c


print("a chain that holds is self-attested, and says so")
c = honest()
check(assurance(c.receipts) == SELF_ATTESTED, "a holding chain reports self-attested")
check(assurance(c.receipts, anchor_confirmed=True) == ANCHORED,
      "the reader's own confirmation, and only that, raises it to anchored")

print()
print("nothing inside the document can raise the level")
loud = Chain()
loud.stamp(what="payout", amount="10.00", payee="acme", currency="USD",
           instrument="settled on Canton DevNet, block 4417213",
           rule="an independent Canton validator authorised this",
           outcome="ACCEPTED",
           approved_by="Canton DevNet consensus, not the applicant",
           ledger="Canton DevNet (real Canton) -- an independent party decided this")
check(loud.verify()[0], "the lying chain genuinely verifies -- the seals are correct")
check(assurance(loud.receipts) == SELF_ATTESTED,
      "every field claims an independent decider; the level is still self-attested")

for field in ("ledger", "approved_by", "instrument", "rule"):
    other = Chain()
    body = dict(what="x", amount="1.00", payee="a", currency="USD",
                instrument="i", rule="r", outcome="ACCEPTED",
                approved_by="p", ledger="l")
    body[field] = "anchored on Canton MainNet by an independent validator"
    other.stamp(**body)
    check(assurance(other.receipts) == SELF_ATTESTED,
          "a claim in `%s` does not raise the level" % field)

print()
print("a level is never offered for something that was not established")
check(assurance([{"n": 1, "seal": "nonsense", "prev": "GENESIS"}]) == "unverified",
      "a chain that does not hold has no assurance level at all")
check("ledger-enforced" not in (SELF_ATTESTED, ANCHORED),
      "there is no ledger-enforced level to hand out")
spec = open(os.path.join(ROOT, "SPEC.md")).read()
check("derived, never declared" in spec.lower() or "derived" in spec,
      "the spec says the level is derived")
check("**MUST** report `self-attested` by default" in spec,
      "  and makes self-attested the default a verifier MUST report")
check("There is deliberately no `ledger-enforced` level" in spec,
      "  and says why there is no third level, rather than leaving a gap")

print()
if fails:
    print("FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("the level is what the verifier established. A producer cannot write their")
print("way up it, which is the only thing that makes the word worth reading.")
