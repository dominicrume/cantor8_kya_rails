"""The shortest thing that shows what this is for.

    python3 -m knowyouragenticai_receipts refusal

Four lines of setup, three attempted payments, one of which is allowed. The
other two never reach the function -- which is the whole point, and the part a
log cannot show you.
"""
from __future__ import annotations

import json

from .guard import Refused, guard
from .policy import Policy

BAR = "-" * 68


def run() -> int:
    print(__doc__.strip().splitlines()[0])
    print(BAR)

    policy = Policy(cap="100.00", currency="USD", allow=["acme"],
                    period_seconds=86400)
    chain = policy.open()
    print("policy sealed as receipt #1:  %s" % policy.as_text())
    print(BAR)

    reached = []

    @guard(policy, chain, what="refund a customer")
    def refund(amount: str, payee: str) -> str:
        reached.append((amount, payee))     # a real one would call Stripe here
        return "sent %s to %s" % (amount, payee)

    for amount, payee in [("40.00", "acme"), ("90.00", "acme"), ("1.00", "stranger")]:
        try:
            print("  ALLOWED   %-9s -> %-9s %s" % (amount, payee, refund(amount, payee)))
        except Refused as e:
            print("  REFUSED   %-9s -> %-9s %s" % (amount, payee, e.rule))

    print(BAR)
    print("the function was reached %d time(s): %s" % (len(reached), reached))
    ok, bad = chain.verify()
    print("%d receipts, chain verifies: %s" % (len(chain), ok if ok else "NO (%s)" % bad))
    print()
    print("Save it and check it yourself -- no install, no account, no node:")
    print("  python3 -m knowyouragenticai_receipts refusal --json > chain.json")
    print("  then drop chain.json on https://dominicrume.github.io/cantor8_kya_rails/")
    print()
    print("Raise the cap in that file before you do, and the page will name the")
    print("entry it broke at. That is the difference between a log and a record.")
    return 0


def run_json() -> int:
    policy = Policy(cap="100.00", currency="USD", allow=["acme"],
                    period_seconds=86400)
    chain = policy.open()

    @guard(policy, chain, what="refund a customer")
    def refund(amount: str, payee: str) -> str:
        return "sent"

    for amount, payee in [("40.00", "acme"), ("90.00", "acme"), ("1.00", "stranger")]:
        try:
            refund(amount, payee)
        except Refused:
            pass
    print(json.dumps(chain.receipts, indent=2))
    return 0
