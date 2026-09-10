#!/usr/bin/env python3
"""You cannot prove an agent did not overspend unless you can prove what
"over" meant.

Until the policy was sealed, this format proved the wrong half. A receipt
reading REFUSED, "over the cap" showed the agent was stopped, but nothing in
the chain said what the cap was -- so an operator who set it to a million
produced a record indistinguishable from one who set it to five. The refusal
was evidence of caution, not of a limit.

The policy is now the first receipt. Every later entry hashes it through
`prev`, so raising the cap after the fact breaks every seal that follows.
Nothing in the verifier had to learn about policies: it already refuses a chain
whose first entry moved.

Four claims here, and the third is the product.

**The rules are in the record**, in text a person can read, not only a hash
they must take on faith.

**A refusal is enforced, not noted.** The wrapped function is not called. A
guard that recorded REFUSED and paid anyway would produce a chain that reads
correctly and describes something that did not happen.

**Rewriting the policy breaks the chain** -- the cap, the allow-list, deleting
it, and softening a refusal, each caught at the entry it was done to.

**The record says who refused.** Self-attested and ledger-enforced must never
look alike, because the reader's whole job is deciding how much to believe it.

Run: python3 tests/policy_smoke.py
"""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "pkg", "src"))

from knowyouragenticai_receipts import (                    # noqa: E402
    Policy, PolicyError, Refused, guard, attempt, verify, Chain)

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def fresh(**kw):
    kw.setdefault("cap", "100.00")
    kw.setdefault("currency", "USD")
    kw.setdefault("allow", ["acme"])
    p = Policy(**kw)
    return p, p.open()


print("the rules are IN the record, readable, not only hashed")
p, chain = fresh(period_seconds=86400, note="demo")
first = chain.receipts[0]
check(first["outcome"] == "POLICY", "entry 1 is the policy")
check(first["n"] == 1 and first["prev"] == "GENESIS", "  and it is genuinely first")
check("cap=100.00 USD" in first["rule"], "the cap is stated in the entry")
check("allow=[acme]" in first["rule"], "the allow-list is stated")
check("period=86400s" in first["rule"], "the period is stated")
check(first["currency"] == "USD", "the currency is the one that was chosen")

print()
print("a refusal is ENFORCED, not merely recorded")
p, chain = fresh()
ran = []


@guard(p, chain, what="refund a customer")
def refund(amount, payee):
    ran.append((amount, payee))
    return "sent"


check(refund("40.00", "acme") == "sent", "an allowed call runs and returns")
for amount, payee, why in [("90.00", "acme", "over the cap"),
                           ("1.00", "stranger", "off the allow-list"),
                           ("-5.00", "acme", "a negative amount"),
                           ("0", "acme", "a zero amount")]:
    try:
        refund(amount, payee)
        check(False, "%s was refused" % why)
    except Refused as e:
        check(True, "%s is refused (%s)" % (why, e.rule[:44]))
check(ran == [("40.00", "acme")],
      "the function ran ONCE: no refusal ever reached it (%d call(s))" % len(ran))
check(str(p.spent) == "40.00", "only what was allowed counts as spent")

print()
print("the refusal is on the record too, with the rule that caused it")
outcomes = [r["outcome"] for r in chain.receipts]
check(outcomes == ["POLICY", "ACCEPTED", "REFUSED", "REFUSED", "REFUSED", "REFUSED"],
      "every attempt is an entry, refusals included")
check(all(r["rule"] for r in chain.receipts), "every entry names its rule")
check(verify(chain.receipts)[0], "the chain verifies as written")

print()
print("rewriting the policy breaks the chain -- this is the product")
rs = chain.receipts
for label, mutate, where in [
        ("the cap is raised", lambda t: t[0].__setitem__("rule", "cap=9999999.00 USD; allow=[acme]"), 1),
        ("the allow-list is widened", lambda t: t[0].__setitem__("payee", "acme,stranger"), 1),
        ("the currency is swapped", lambda t: t[0].__setitem__("currency", "JPY"), 1),
        ("a refusal is softened", lambda t: t[2].__setitem__("outcome", "ACCEPTED"), 3),
]:
    t = copy.deepcopy(rs)
    mutate(t)
    ok, bad = verify(t)
    check(not ok and bad == where, "%s -> breaks at entry %s" % (label, bad))

t = copy.deepcopy(rs)
del t[0]
check(not verify(t)[0], "the policy cannot be removed: the chain stops verifying")

print()
print("the record says WHO refused, and never blurs it")
check("self-attested" in chain.receipts[1]["ledger"],
      "an in-process refusal is labelled self-attested")
p2, c2 = fresh()
attempt(p2, c2, "on-ledger payout", "10.00", "acme",
        enforced_by="canton devnet (an independent party refused)")
check("independent party" in c2.receipts[1]["ledger"],
      "a ledger refusal says so, so a reader can weigh the two differently")
check(chain.receipts[1]["ledger"] != c2.receipts[1]["ledger"],
      "the two are never written the same way")

print()
print("a policy nobody can state is refused up front")
for kw, why in [({"cap": 100.0}, "a float cap"),
                ({"cap": "-1"}, "a negative cap"),
                ({"cap": "abc"}, "a cap that is not a number"),
                ({"allow": []}, "an empty allow-list"),
                ({"period_seconds": -1}, "a negative period")]:
    try:
        fresh(**kw)
        check(False, "%s is refused" % why)
    except PolicyError:
        check(True, "%s is refused, with the field named" % why)

print()
print("a policy declared halfway through binds nothing before it")
c = Chain()
c.stamp(what="a payment made earlier", amount="5.00", payee="someone",
        currency="USD", instrument="x", rule="no policy was in force",
        outcome="ACCEPTED", approved_by="nobody", ledger="none")
try:
    Policy(cap="1.00", currency="USD", allow=["acme"]).open(c)
    check(False, "opening a policy on a used chain is refused")
except PolicyError as e:
    check("already has" in str(e), "opening a policy on a used chain is refused")

print()
if fails:
    print("FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("the rules the agent ran under are in the record, and cannot be changed")
print("afterwards by the person the record is about.")
