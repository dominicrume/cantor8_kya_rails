#!/usr/bin/env python3
"""The DevNet path, exercised without DevNet.

step-2-agent/devnet_ledger.py is the only code that talks to real Canton, and
it is the only code here that no suite could run: it needs a secret, a network
and a validator. So it was changed by reading it and hoping, which is how the
`rule` field on the real rail came to be a regex over a gRPC error string that
nothing checked.

Everything in charge() except the HTTP call is pure parsing, and parsing can be
tested. `_submit` is replaced with a function returning a recorded-shape
transaction, and what comes back out of charge() is checked.

What this does NOT test, said plainly so nobody reads it as more than it is:
whether Canton returns transactions of this shape. The shapes here are written
from the JSON API's documented form and from what _created already assumed. If
Canton changes them, this suite stays green and the rail breaks. It covers our
half of the contract, which was previously covered by nothing.

Run: python3 tests/devnet_parse_smoke.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "step-2-agent"))

# devnet_ledger imports the organisers' toolkit and reads env at call time, not
# at import time. If that ever changes this raises loudly rather than skipping,
# because a suite that silently skips the only test of the real rail is worse
# than not having one.
os.environ.setdefault("C8_CLIENT_SECRET", "not-used-by-these-tests")
sys.path.insert(0, os.path.expanduser("~/hackathon-toolkit"))
import devnet_ledger as dn                                    # noqa: E402

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def created(entity, cid, payload=None):
    return {"CreatedTreeEvent": {"value": {
        "templateId": "abc123:KyaMandate:" + entity,
        "contractId": cid,
        "createArgument": payload or {}}}}


def tx(*events):
    return {"transaction": {"events": list(events)}}


def ledger_returning(ok, response):
    """A DevNetLedger whose only network call is replaced."""
    led = dn.DevNetLedger.__new__(dn.DevNetLedger)
    led.cid = "old-mandate-cid"
    led.revoked = False
    led.move_coin = False
    led.last_ledger_ref = "left over from a previous call"
    dn._submit = lambda *a, **k: (ok, response)
    return led


print("a refusal that was recorded on the ledger")
led = ledger_returning(True, tx(
    created("ChargeRefused", "refusal-cid-1",
            {"rule": "charge would exceed the cap", "amount": "95000.0"}),
    created("KyaMandate", "new-mandate-cid")))
outcome, rule = led.charge(95000.0, "customer")
check(outcome == "REFUSED", "is reported REFUSED (%s)" % outcome)
check(rule == "charge would exceed the cap",
      "  and names the rule READ OFF THE CONTRACT, not parsed from an error")
check(led.last_ledger_ref == "refusal-cid-1",
      "  and carries the contract id a reader can look up (%r)"
      % led.last_ledger_ref)
check(led.cid == "new-mandate-cid",
      "  and follows the mandate to its new id, since TryCharge consumes it")

print()
print("an accepted charge")
led = ledger_returning(True, tx(
    created("ChargeRecord", "record-cid"),
    created("KyaMandate", "next-mandate-cid")))
outcome, rule = led.charge(1.0, "customer")
check(outcome == "ACCEPTED", "is reported ACCEPTED (%s)" % outcome)
check(led.last_ledger_ref == "",
      "  and claims no refusal reference, because there was no refusal")
check(led.cid == "next-mandate-cid", "  and follows the mandate")

print()
print("the distinction that has to survive: a refusal is not a failure")
# A revoked mandate, an auth problem or a dropped connection all come back
# REFUSED. None of them is a refusal RECORDED on the ledger, and dressing one
# up as one would put a reference in a receipt that points at nothing.
led = ledger_returning(False, "CONTRACT_NOT_ACTIVE: the mandate was archived")
led.revoked = True
outcome, rule = led.charge(1.0, "customer")
check(outcome == "REFUSED", "a failed submission is still REFUSED")
check(led.last_ledger_ref == "",
      "  but carries NO ledger reference, because nothing was committed")
check("no longer active" in rule, "  and says what happened (%s)" % rule[:44])

led = ledger_returning(False, "UNAUTHENTICATED: token rejected")
led.revoked = True
outcome, rule = led.charge(1.0, "customer")
check(led.last_ledger_ref == "", "an auth failure carries no reference either")

print()
print("a shape we did not expect")
# A ChargeRefused whose rule cannot be read is a contract we do not understand.
# Inventing a plausible rule for it would be the single worst thing this file
# could do, because it would look exactly like evidence.
led = ledger_returning(True, tx(
    created("ChargeRefused", "refusal-cid-2", {"amount": "1.0"}),
    created("KyaMandate", "m2")))
outcome, rule = led.charge(1.0, "customer")
check(outcome == "REFUSED", "is still REFUSED")
check("unreadable" in rule, "  and says the rule is unreadable rather than guessing")
check(led.last_ledger_ref == "refusal-cid-2",
      "  while still pointing at the contract, so a person can go and read it")

print()
print("the JSON API has spelled the payload key more than one way")
for key in ("createArgument", "createArguments"):
    led = ledger_returning(True, tx(
        {"CreatedTreeEvent": {"value": {
            "templateId": "x:KyaMandate:ChargeRefused", "contractId": "c",
            key: {"rule": "payee is not on the allow-list"}}}},
        created("KyaMandate", "m")))
    outcome, rule = led.charge(1.0, "stranger")
    check(rule == "payee is not on the allow-list", "  %s is read" % key)

print()
print("and it exercises TryCharge, not Charge")
sent = {}


def capture(commands, **kw):
    sent["choice"] = commands[0]["ExerciseCommand"]["choice"]
    return True, tx(created("KyaMandate", "m"))


led = dn.DevNetLedger.__new__(dn.DevNetLedger)
led.cid, led.revoked, led.move_coin = "c", False, False
dn._submit = capture
led.charge(1.0, "customer")
check(sent.get("choice") == "TryCharge",
      "the choice exercised is TryCharge (%s)" % sent.get("choice"))

print()
if fails:
    print("FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("the real rail reads the rule off the ledger, and never claims a")
print("reference for a refusal that was not recorded there.")
