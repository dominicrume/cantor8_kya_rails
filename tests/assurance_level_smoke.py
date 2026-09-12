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
    ANCHORED, LEDGER_RECORDED, SELF_ATTESTED, Chain, Policy, assurance, guard)

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
print("the refusal on a ledger, which is the other half of the question")
# A refusal written by assertMsg aborts the transaction, so it leaves nothing
# behind and the receipt saying REFUSED is the operator writing about itself.
# KyaMandate.TryCharge commits the refusal as a ChargeRefused contract, and the
# receipt can carry the contract id. That id is still written by the producer:
# what it buys is that it points at something a reader can go and check, and
# only that reader's finding may raise the level.
ledgered = Chain(approved_by="the mandate", ledger="Canton")
ledgered.allowed(what="settle", amount="10.00", currency="USD", payee="m1",
                 rule="inside the cap")
ledgered.refused(what="settle", amount="999.00", currency="USD", payee="m1",
                 rule="charge would exceed the cap",
                 ledger_ref="00a1b2c3::ChargeRefused")
check(ledgered.verify()[0], "a chain carrying a ledger_ref still verifies")
check("ledger_ref" in ledgered.receipts[1] and "ledger_ref" not in ledgered.receipts[0],
      "  and the field is present only on the entry that has one")
check(assurance(ledgered.receipts) == SELF_ATTESTED,
      "naming a contract id does NOT raise the level on its own")
check(assurance(ledgered.receipts, refusals_confirmed=True) == SELF_ATTESTED,
      "  nor does finding the refusals, while the chain itself could be swapped")
check(assurance(ledgered.receipts, anchor_confirmed=True) == ANCHORED,
      "  nor does anchoring, which says nothing about whether a refusal happened")
check(assurance(ledgered.receipts, anchor_confirmed=True,
                refusals_confirmed=True) == LEDGER_RECORDED,
      "only both findings together reach ledger-recorded")
check(LEDGER_RECORDED == "ledger-recorded" and LEDGER_RECORDED != "ledger-enforced",
      "  and it is named for what it establishes: records, not enforcement")

print()
print("and nothing in the repository offers a level the spec rules out")
# docs/what-this-proves.md carried a table with a `ledger-enforced` rung,
# reached by writing `assertMsg` into the `ledger` field, and a closing line
# telling readers to "read the `ledger` field on every entry before you read
# anything else". Both survived the commit that added SPEC 6a, because 6a was
# checked against SPEC.md and against the code, and nothing looked at the page
# whose whole job is to tell a reader what they may conclude.
BANNED = "ledger-enforced"
for name in sorted(os.listdir(os.path.join(ROOT, "docs"))) + ["../README.md"]:
    if not name.endswith(".md"):
        continue
    path = os.path.join(ROOT, "docs", name)
    text = open(path).read()
    offered = [ln.strip() for ln in text.splitlines()
               if BANNED in ln and "no `ledger-enforced`" not in ln
               and "had a rung called" not in ln]
    check(not offered,
          "%s does not offer a %s level%s"
          % (name, BANNED, "" if not offered else ": " + offered[0][:60]))

print()
print("a level is never offered for something that was not established")
check(assurance([{"n": 1, "seal": "nonsense", "prev": "GENESIS"}]) == "unverified",
      "a chain that does not hold has no assurance level at all")
check("ledger-enforced" not in (SELF_ATTESTED, ANCHORED, LEDGER_RECORDED),
      "there is no ledger-enforced level to hand out")
spec = open(os.path.join(ROOT, "SPEC.md")).read()
check("derived, never declared" in spec.lower() or "derived" in spec,
      "the spec says the level is derived")
check("**MUST** report `self-attested` by default" in spec,
      "  and makes self-attested the default a verifier MUST report")
check("There is deliberately no `ledger-enforced` level" in spec,
      "  and rules out ledger-enforced by name, rather than leaving a gap")

print()
if fails:
    print("FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("the level is what the verifier established. A producer cannot write their")
print("way up it, which is the only thing that makes the word worth reading.")
