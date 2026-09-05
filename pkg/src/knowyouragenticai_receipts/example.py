"""The whole idea, in one runnable file.

    python -m knowyouragenticai_receipts example

It lives inside the package on purpose. A README that points at a file which
does not ship is a broken promise to everyone who installed rather than cloned
-- and that is most people. This one is always there.

An agent is given a spending limit and an allow-list. It tries four payments.
Two are fine. Two are not. Every attempt is recorded -- including the two that
were stopped -- and the record cannot be quietly edited afterwards.

That last part is the point. An ordinary log would contain the two payments
that went through. The question anyone checking your system actually asks is
about the other two.
"""
from . import Chain

# What the agent is allowed to do. In a real system these live somewhere the
# agent cannot reach -- a smart contract, a policy service -- which is what
# makes them a limit rather than a suggestion.
CAP = 500.00
ALLOW_LIST = {"Acme Ltd", "Bolt Logistics"}


class Desk:
    """A tiny stand-in for whatever actually holds your money."""

    def __init__(self):
        self.chain = Chain(approved_by="finance", ledger="stripe")
        self.spent = 0.0

    def attempt(self, what, amount, payee):
        """Try one payment. Record it either way -- that is the whole idea."""
        value = float(amount)
        if payee not in ALLOW_LIST:
            self.chain.refused(what=what, amount=amount, currency="USD",
                               payee=payee, rule="payee is not on the allow-list")
            return
        if self.spent + value > CAP:
            self.chain.refused(what=what, amount=amount, currency="USD",
                               payee=payee, rule="would exceed the %.2f cap" % CAP)
            return
        # A real system pays here. The receipt records that it was authorised.
        self.spent += value
        self.chain.allowed(what=what, amount=amount, currency="USD", payee=payee,
                           rule="under the cap, payee on the allow-list")


def run() -> int:
    desk = Desk()
    desk.attempt("invoice 41", "250.00", "Acme Ltd")
    desk.attempt("invoice 42", "150.00", "Bolt Logistics")
    desk.attempt("invoice 43", "400.00", "Acme Ltd")             # over the cap
    desk.attempt("urgent, new supplier", "90.00", "Unknown Co")  # not allow-listed
    chain = desk.chain

    print("What the agent tried, and what happened:\n")
    for r in chain.receipts:
        mark = "  paid   " if r["outcome"] == "ACCEPTED" else "  STOPPED"
        print("%s %6s %s  ->  %-16s %s"
              % (mark, r["amount"], r["currency"], r["payee"], r["rule"]))

    ok, _bad = chain.verify()
    print("\n%d entries, chain verifies: %s" % (len(chain), ok))
    print("chain head: %s" % chain.head)

    # Now tamper with it, the way someone hiding a refusal would.
    print("\nSomeone edits the third entry to hide that it was stopped:")
    chain.receipts[2]["outcome"] = "ACCEPTED"
    ok, bad = chain.verify()
    print("  chain verifies: %s, first bad entry: %s" % (ok, bad))
    print("  %r" % chain)

    print("\nAnd it cannot be quietly extended afterwards either:")
    try:
        chain.allowed(what="invoice 44", amount="10.00", currency="USD",
                      payee="Acme Ltd", rule="under the cap")
        print("  it was extended -- that is a bug, please report it")
        return 1
    except Exception as e:
        print("  %s: %s" % (type(e).__name__, str(e).split(".")[0]))

    print("\nSave it, and anyone can check it without installing anything:")
    print("  drag the file onto the verifier page, or:")
    print("  python -m knowyouragenticai_receipts verify receipts.json")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(run())
