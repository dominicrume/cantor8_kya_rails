"""The rules that were in force, sealed into the chain that records them.

A receipt saying REFUSED, "over the cap" proves the agent was stopped. It does
not prove what the cap was. An operator who set it to a million can produce the
same record as one who set it to five, and a reader holding only the chain
cannot tell them apart -- so "the agent did not overspend" is unprovable, which
is the one thing this format exists to prove.

The fix is not a new field. It is to make the policy the FIRST RECEIPT: entry
one, outcome POLICY, carrying the rules as text. Every later entry hashes it
through `prev`, so changing the cap after the fact breaks every seal in the
chain. Nothing in the verifier had to be taught about policies -- it already
refuses a chain whose first entry moved.

    p = Policy(cap="100.00", currency="USD", allow=["acme"], period_seconds=86400)
    chain = p.open()          # entry 1 IS the policy
    p.check("40.00", "acme")  # (True, "within the cap and on the allow-list")

What this does NOT do is enforce anything on anyone else's behalf. `check`
answers a question; `guard` acts on the answer; and both run inside the
operator's own process. A refusal recorded here is the operator's own system
saying no, which is worth strictly less than an independent party saying no --
see `enforced_by` in guard.py, which never lets the two look alike.
"""
from __future__ import annotations

import threading
import time
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from . import Chain

__all__ = ["Policy", "PolicyError"]

POLICY = "POLICY"


class PolicyError(ValueError):
    """A policy that cannot be stated is a policy nobody can check."""


def _amount(value: Any, field: str) -> Decimal:
    """Money as Decimal, from a string, or not at all.

    Floats are refused for the reason `stamp` refuses them: 0.1 + 0.2 is not
    0.3, and a cap that is silently 100.00000000000001 is a cap nobody set.
    """
    if isinstance(value, float):
        raise PolicyError(
            "%s must be a string, not a float. 0.1 + 0.2 is not 0.3, and a "
            "limit nobody typed is a limit nobody agreed. Pass \"%s\"."
            % (field, value))
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise PolicyError("%s is not a number: %r" % (field, value)) from None
    if d < 0:
        raise PolicyError("%s cannot be negative (%s)" % (field, d))
    return d


class Policy:
    """What the agent is allowed to do, in a form a stranger can re-hash."""

    def __init__(self, cap: str, currency: str, allow: Iterable[str],
                 period_seconds: int = 0, expires_at: str = "",
                 note: str = "") -> None:
        self.cap = _amount(cap, "cap")
        self.currency = str(currency)
        self.allow = tuple(sorted({str(a) for a in allow}))
        if not self.allow:
            raise PolicyError(
                "an empty allow-list permits nobody. If that is deliberate, "
                "say so with a payee nothing will match, so the record shows "
                "a choice rather than an omission.")
        if int(period_seconds) < 0:
            raise PolicyError("period_seconds cannot be negative")
        self.period_seconds = int(period_seconds)
        self.expires_at = str(expires_at)
        self.note = str(note)
        self._spent = Decimal(0)
        self._window_start = 0.0
        # check() reads the budget and commit() writes it, with a receipt
        # sealed in between. Two callers could both pass the check before
        # either committed, and both would be inside the cap on their own
        # reading and over it together. CPython's GIL made that window small
        # enough that eight threads never reproduced it -- which is luck, not
        # a guarantee, and free-threaded builds remove even the luck. The lock
        # is re-entrant so a caller may hold it around its own critical
        # section without deadlocking on ours.
        self.lock = threading.RLock()

    # ---------------------------------------------------------------- text
    def as_text(self) -> str:
        """The policy as one ASCII line, which is what gets sealed.

        Sorted, explicit, and readable by the person the record is handed to.
        A structure only a parser can read would be sealed just as well and
        checked by nobody.
        """
        bits = ["cap=%s %s" % (self.cap, self.currency),
                "allow=[%s]" % ",".join(self.allow)]
        if self.period_seconds:
            bits.append("period=%ds" % self.period_seconds)
        if self.expires_at:
            bits.append("expires=%s" % self.expires_at)
        if self.note:
            bits.append("note=%s" % self.note)
        return "; ".join(bits)

    # --------------------------------------------------------------- chain
    def open(self, chain: Chain | None = None, approved_by: str = "",
             ledger: str = "") -> Chain:
        """Start a chain whose first entry is this policy.

        Refuses a chain that already has entries: a policy stated halfway
        through binds only what follows it, and a reader would have no way to
        see that the earlier receipts were made under something else.
        """
        chain = Chain() if chain is None else chain
        if len(chain):
            raise PolicyError(
                "this chain already has %d receipt(s). A policy declared after "
                "the fact binds nothing before it; start a new chain."
                % len(chain))
        chain.stamp(
            what="policy in force",
            amount=str(self.cap),
            payee=",".join(self.allow),
            currency=self.currency,
            instrument="policy",
            rule=self.as_text(),
            outcome=POLICY,
            approved_by=approved_by or "the principal, before the agent ran",
            ledger=ledger or "self-attested (no ledger)",
        )
        self._window_start = time.time()
        return chain

    # --------------------------------------------------------------- rules
    def check(self, amount: str, payee: str, now: float | None = None
              ) -> tuple[bool, str]:
        """(allowed, the rule that decided it). Never raises on a refusal --
        a refusal is an answer, not an error, and it has to be recordable."""
        now = time.time() if now is None else now
        try:
            value = _amount(amount, "amount")
        except PolicyError as e:
            return False, str(e)
        self._roll(now)
        for rule in (self._positive, self._on_allow_list, self._unexpired, self._under_cap):
            ok, why = rule(value, payee, now)
            if not ok:
                return False, why
        return True, ("within the cap (%s of %s %s used) and on the allow-list"
                      % (self._spent, self.cap, self.currency))

    # Each rule answers for itself. Split out of `check` when it reached ten
    # branches: a single function deciding four independent questions is one
    # nobody can read a refusal out of, and the refusal text is the part the
    # reader of a receipt actually needs.
    def _roll(self, now: float) -> None:
        """A new period starts the budget again -- the rolling window, same
        shape as the Daml."""
        if self.period_seconds and now - self._window_start >= self.period_seconds:
            self._window_start, self._spent = now, Decimal(0)

    def _positive(self, value: Decimal, _payee: str, _now: float) -> tuple[bool, str]:
        if value <= 0:
            return False, "amount must be positive (%s)" % value
        return True, ""

    def _on_allow_list(self, _value: Decimal, payee: str, _now: float) -> tuple[bool, str]:
        if payee not in self.allow:
            return False, "payee is not on the allow-list: %s" % payee
        return True, ""

    def _unexpired(self, _value: Decimal, _payee: str, now: float) -> tuple[bool, str]:
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
        if self.expires_at and stamp >= self.expires_at:
            return False, "the mandate expired at %s" % self.expires_at
        return True, ""

    def _under_cap(self, value: Decimal, _payee: str, _now: float) -> tuple[bool, str]:
        if self._spent + value > self.cap:
            return False, ("would exceed the cap: %s + %s > %s %s"
                           % (self._spent, value, self.cap, self.currency))
        return True, ""

    def commit(self, amount: str) -> None:
        """Only what the rules allowed is counted as spent."""
        self._spent += _amount(amount, "amount")

    @property
    def spent(self) -> Decimal:
        return self._spent

    def __repr__(self) -> str:
        return "<Policy %s>" % self.as_text()
