#!/usr/bin/env python3
"""You can decline to show a refusal. You cannot conceal that it happened.

Prevention says the door was locked. This is the other question a regulator,
an insurer or a counterparty asks: show me everything the agent tried and was
stopped from doing, and let me check it without trusting you.

Until this existed a chain was all or nothing. Slicing the refusals out
produced a file that failed verification, because every seal covers the one
before it. Handing over the whole chain disclosed every accepted payment too,
which for a regulated issuer is the reason they could not use it.

The design rests on two rules.

**Position, outcome, prev and seal are never withheld.** If an entry could be
hidden entirely, "here are my three refusals" would be indistinguishable from
a chain that had thirty.

**The document declares what it is showing.** That is what makes a withheld
entry's outcome checkable at all, because a withheld body cannot be
recomputed. A document promising to show every refusal cannot also withhold
one, and the check names the entry.

Everything below is an attack on those two. The ones that matter most are
deleting a refusal, and withholding a refusal while claiming to show them all.

Run: python3 tests/disclosure_smoke.py
"""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "pkg", "src"))

from knowyouragenticai_receipts import (                      # noqa: E402
    Policy, Refused, check_disclosure, disclose, guard, refusals_only, verify,
    what_this_reveals)
from knowyouragenticai_receipts.disclose import (             # noqa: E402
    EVERY_REFUSAL, WITHHELD, summary)

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def a_chain():
    """Two payments that went through, two that were stopped."""
    p = Policy(cap="100.00", currency="USD", allow=["acme"])
    c = p.open()

    @guard(p, c)
    def pay(amount, payee):
        return "ok"

    pay("10.00", "acme")
    for amount, payee in [("999.00", "acme"), ("5.00", "stranger")]:
        try:
            pay(amount, payee)
        except Refused:
            pass
    pay("20.00", "acme")
    return c.receipts


def refused_index(doc):
    return next(i for i, e in enumerate(doc["entries"])
                if e["outcome"] == "REFUSED")


receipts = a_chain()
doc = disclose(receipts)

print("the refusals travel, the book stays shut")
ok, why = check_disclosure(doc)
check(ok, "a disclosure verifies (%s)" % (why or "clean"))
check(verify([r for r in receipts if r["outcome"] == "REFUSED"])[0] is False,
      "  where slicing the refusals out by hand produces a file that does not")

accepted = [e for e in doc["entries"] if e["outcome"] == "ACCEPTED"]
check(len(accepted) == 2, "the two accepted payments are still listed")
check(all("body" not in e for e in accepted), "  with no body")
check(all(e.get(WITHHELD) for e in accepted), "  marked withheld")
check(all("amount" not in e.get("body", {}) for e in accepted),
      "  and no accepted body travels")

# Withholding a body is not the same as withholding its contents. A refusal
# reads "would exceed the cap: 10.00 + 999.00", and the 10.00 is the accepted
# payment two entries above, quoted verbatim inside an entry being shown. It
# cannot be redacted, because editing a shown body breaks its seal. It can
# only be pointed at, so the producer decides knowingly.
warnings = what_this_reveals(receipts, doc)
check(len(warnings) == 1, "the leak check finds exactly the real one (%d)" % len(warnings))
check("10.00" in warnings[0] and "amount" in warnings[0],
      "  and names it: %s" % warnings[0][:74])
check(all("acme" not in w for w in warnings),
      "  and does not flag the allow-list, which the policy shows on purpose")

shown = [e for e in doc["entries"] if "body" in e]
check(all(refusals_only(e) for e in shown),
      "everything shown in full is a refusal or the policy in force")
check(doc["entries"][0]["outcome"] == "POLICY" and "body" in doc["entries"][0],
      "  the policy IS shown, because a refusal citing the cap needs the cap")
check(any("cap" in e["body"]["rule"] for e in shown if e["outcome"] == "REFUSED"),
      "  and a shown refusal carries the rule that stopped it")
check(all(e.get("outcome") for e in doc["entries"]),
      "every entry declares its outcome, shown or withheld")
check(doc["disclosing"] == EVERY_REFUSAL,
      "the document declares what it is showing")

print()
print("attacks on what was removed")

t = copy.deepcopy(doc)
del t["entries"][refused_index(t)]
ok, why = check_disclosure(t)
check(not ok, "deleting a refusal is caught (%s)" % why[:52])

# A careless deletion leaves the count wrong and is caught on that alone, so
# the position check above it is never exercised. The mutation harness said so:
# removing the check left this suite green, reported BLIND. A careful attacker
# fixes the count and the shown total, and only the 1..n sequence catches them.
t = copy.deepcopy(doc)
i = refused_index(t)
del t["entries"][i]
t["count"] = len(t["entries"])
t["shown"] = sum(1 for e in t["entries"] if "body" in e)
t["head"] = t["entries"][-1]["seal"]
ok, why = check_disclosure(t)
check(not ok, "a tidied-up deletion is still caught (%s)" % why[:56])
check("numbered" in why or "follow" in why,
      "  by the position sequence, not by a count that was corrected")

# The links alone catch a deletion, so the position check was not the thing
# doing the work, and the harness reported it BLIND twice before this test
# existed. What it actually guards is a document whose links are intact and
# whose numbering lies: renumber a refusal and it appears to have happened
# earlier in the run than it did, which is a statement about sequence a reader
# would otherwise believe.
t = copy.deepcopy(doc)
for offset, e in enumerate(t["entries"]):
    e["n"] = offset + 10          # links untouched, numbering false
ok, why = check_disclosure(t)
check(not ok and "numbered" in why,
      "renumbering entries while leaving the links intact is caught (%s)" % why[:52])

t = copy.deepcopy(doc)
t["entries"].reverse()
check(not check_disclosure(t)[0], "reordering is caught")

t = copy.deepcopy(doc)
t["count"] = 99
ok, why = check_disclosure(t)
check(not ok, "a count that does not match the entries is caught (%s)" % why[:40])

print()
print("attacks on what was shown")

t = copy.deepcopy(doc)
i = refused_index(t)
t["entries"][i]["body"]["rule"] = "a routine check, nothing unusual"
ok, why = check_disclosure(t)
check(not ok, "softening the rule on a shown refusal is caught (%s)" % why[:44])

t = copy.deepcopy(doc)
i = refused_index(t)
t["entries"][i]["outcome"] = "ACCEPTED"
ok, why = check_disclosure(t)
check(not ok, "relabelling a shown refusal is caught (%s)" % why[:44])

t = copy.deepcopy(doc)
t["entries"][refused_index(t)]["outcome"] = ""
ok, why = check_disclosure(t)
check(not ok and "may never" in why, "an entry may never withhold its outcome")

print()
print("attacks on what was withheld, which is the hard half")

t = copy.deepcopy(doc)
i = refused_index(t)
t["entries"][i].pop("body")
t["entries"][i][WITHHELD] = True
ok, why = check_disclosure(t)
check(not ok and "claims to show" in why,
      "withholding a refusal while promising to show them all is caught")
check(str(t["entries"][i]["n"]) in why, "  and the offending entry is named")

# The residual limit, asserted so nobody mistakes it for a guarantee.
t = copy.deepcopy(doc)
i = refused_index(t)
t["entries"][i].pop("body")
t["entries"][i][WITHHELD] = True
t["entries"][i]["outcome"] = "ACCEPTED"
t["disclosing"] = "a chosen subset"
t["shown"] = sum(1 for e in t["entries"] if "body" in e)
ok, _why = check_disclosure(t)
check(ok, "a withheld entry relabelled ACCEPTED under a subset claim still "
          "verifies, which is the residual limit, not a bug")
check("cannot be recomputed" in
      __import__("knowyouragenticai_receipts.disclose", fromlist=["x"]).__doc__,
      "  the limit is written down where a reader will find it")

print()
print("what a person is told")
line = summary(doc)
check("5 entries" in line and "withheld" in line, "the summary says the counts: %s" % line)
t = copy.deepcopy(doc)
t["disclosing"] = "a chosen subset"
i = refused_index(t)
t["entries"][i].pop("body")
t["entries"][i][WITHHELD] = True
check("refusal" in summary(t),
      "  and when a refusal is held back it says so: %s" % summary(t)[-90:])

print()
if fails:
    print("FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("the refusals can be handed over on their own, nothing can be removed")
print("from them without detection, and the accepted payments stay shut.")
