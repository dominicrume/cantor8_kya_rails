"""A tamper-evident record of what an agent was refused, not only what it did.

Most audit logs record what happened. The artefact anyone checking your system
actually asks for is the opposite: **what was attempted and stopped.** And a
log written by the party being checked can be edited afterwards, so each entry
here is sealed to the one before it. Change any entry and every seal after it
breaks.

    from knowyouragenticai_receipts import Chain

    chain = Chain()
    chain.stamp(what="payout to supplier", amount="10.0", payee="Chidi",
                rule="inside the cap", outcome="ACCEPTED",
                approved_by="principal", ledger="production")
    chain.stamp(what="payout to an unknown account", amount="5.0",
                payee="Stranger", rule="payee is not on the allow-list",
                outcome="REFUSED", approved_by="principal", ledger="production")

    chain.verify()          # (True, 0)
    chain.head              # the one value that stands for the whole chain

Check a file without writing any code:

    python -m knowyouragenticai_receipts verify receipts.json
    python -m knowyouragenticai_receipts selftest      # prove this build matches the spec

The format is specified in full in SPEC.md, in about a page, and is roughly
twenty lines to implement in any language.

WHAT THIS DOES NOT DO, said here because a format that oversells itself is
worse than none:

  * It is not signed. It proves internal consistency, not origin -- anyone can
    produce a valid chain saying anything, and a forged one verifies. Bind the
    final seal to something you do not control if origin matters. The reference
    application publishes it on a Canton ledger.
  * It does not prove a rule was enforced. `rule` is a string. The guarantee
    comes from wherever the decision was actually made.
  * It makes editing detectable, not deletion. Publish the head somewhere else
    if discarding the whole chain matters.

Zero dependencies: the whole format is `json` and `hashlib`. A dependency here
would be a dependency in everyone's audit trail.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Iterable, Mapping, Sequence

__version__ = "1.0.0"
__all__ = ["canonical", "seal", "verify", "assert_ascii", "Chain",
           "NonAsciiInReceipt", "BrokenChain", "GENESIS"]

GENESIS = "GENESIS"


class NonAsciiInReceipt(ValueError):
    """A hashed field carried a character outside ASCII.

    Raised before sealing, never after. Python escapes non-ASCII to \\uXXXX and
    JavaScript's JSON.stringify emits the raw character, so the same receipt
    would seal to two different hashes and the chain would verify in one
    language and go red in the other.
    """


class BrokenChain(ValueError):
    """Refusing to append to a chain that does not verify.

    Extending a chain whose history has been altered produces more entries that
    look correct on their own while resting on something that is not. The break
    must be dealt with, not built on.
    """


def canonical(obj: Any) -> str:
    """The exact bytes that get hashed: sorted keys, no spaces, ASCII-escaped."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def seal(body: Mapping[str, Any], prev: str) -> str:
    """sha256(canonical(body) + prev), lowercase hex.

    `body` is the receipt without its own `seal` key. `prev` is the previous
    receipt's seal, or GENESIS for the first.
    """
    return hashlib.sha256((canonical(body) + prev).encode()).hexdigest()


def _non_ascii_field(value: Any) -> bool:
    """Is there a character above 0x7E anywhere in here, however deeply nested?

    Nested values used to be skipped, so {"what": "Pay \\u20a6500"} was rejected
    and {"what": {"note": "Pay \\u20a6500"}} was not. Every implementation
    escapes nested strings consistently, so nothing sealed wrongly -- but the
    rule did not do what its own name said.
    """
    if isinstance(value, str):
        return not value.isascii()
    if isinstance(value, Mapping):
        return any(_non_ascii_field(k) or _non_ascii_field(v)
                   for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(_non_ascii_field(v) for v in value)
    return False


def _first_non_ascii(d: Mapping[str, Any]) -> tuple[str | None, Any]:
    for key, value in d.items():
        if _non_ascii_field(key) or _non_ascii_field(value):
            return key, value
    return None, None


def assert_ascii(d: Mapping[str, Any]) -> None:
    """Raise NonAsciiInReceipt if any key or value, at any depth, is not ASCII."""
    field, value = _first_non_ascii(d)
    if field is None:
        return
    text = value if isinstance(value, str) else canonical(value)
    bad = [c for c in text if not c.isascii()]
    raise NonAsciiInReceipt(
        "field %r contains %s, which would seal differently in another "
        "language. Render symbols at display time, not inside the seal."
        % (field, ", ".join(repr(c) for c in bad[:3])))


def _position(r: Any, index: int) -> int:
    """Where a receipt is, for reporting: its own `n` when that is usable, and
    otherwise its 1-based place in the list. A receipt too damaged to carry a
    number still has to be locatable."""
    if isinstance(r, Mapping) and isinstance(r.get("n"), int):
        return r["n"]
    return index


def verify(receipts: Sequence[Any]) -> tuple[bool, int]:
    """(True, 0) if the chain holds, else (False, where it first fails).

    NEVER RAISES. This is the function you point at a file someone else gave
    you, so malformed input is an answer, not an exception: a list of nulls, a
    list of strings, a receipt missing its seal, all come back as a verdict.
    It used to raise AttributeError on any of those.

    The position is the receipt's own `n` when that is a usable integer, and
    otherwise its 1-based place in the list -- so a receipt too damaged to
    carry a number still gets located.
    """
    prev = GENESIS
    for index, r in enumerate(receipts, start=1):
        where = _position(r, index)
        if not isinstance(r, Mapping):
            return False, where
        body = {k: v for k, v in r.items() if k != "seal"}
        try:
            expected = seal(body, prev)
        except (TypeError, ValueError):
            return False, where          # unserialisable content is not a receipt
        if r.get("prev") != prev or r.get("seal") != expected:
            return False, where
        prev = r["seal"]
    return True, 0


class Chain:
    """An append-only list of sealed receipts."""

    def __init__(self, receipts: Iterable[Mapping[str, Any]] | None = None,
                 approved_by: str = "", ledger: str = "") -> None:
        """`approved_by` and `ledger` are set once, here, because they describe
        the desk rather than the payment. Recording ten payments should not
        mean repeating who authorised them ten times."""
        self.receipts: list[dict[str, Any]] = [dict(r) for r in (receipts or [])]
        self.approved_by = approved_by
        self.ledger = ledger

    def allowed(self, what: str, amount: str, currency: str, payee: str,
                rule: str, **kw: Any) -> dict[str, Any]:
        """Record a payment that went through, and why it was allowed."""
        return self.stamp(what=what, amount=amount, currency=currency,
                          payee=payee, rule=rule, outcome="ACCEPTED", **kw)

    def refused(self, what: str, amount: str, currency: str, payee: str,
                rule: str, **kw: Any) -> dict[str, Any]:
        """Record a payment that was STOPPED, and what stopped it.

        This is the half an ordinary log throws away, and the half anyone
        checking your system actually asks about.
        """
        return self.stamp(what=what, amount=amount, currency=currency,
                          payee=payee, rule=rule, outcome="REFUSED", **kw)

    def stamp(self, what: str, amount: str, currency: str, payee: str,
              rule: str, outcome: str, approved_by: str | None = None,
              ledger: str | None = None, instrument: str = "",
              at: str | None = None) -> dict[str, Any]:
        """Append one receipt and return it.

        Most of the time you want `allowed()` or `refused()` instead; this is
        the full-control version.

        `currency` is REQUIRED. It used to default to "CC" -- Canton Coin --
        so anyone recording dollars sealed them as Canton Coin, permanently and
        silently. A currency nobody chose is worse than an argument nobody
        wanted to type.

        `amount` must be a STRING. A float that survives one language's JSON
        encoder is not a float that survives all of them, and the seal computed
        over "1.0" is not the seal computed over "1". Passing 1/3 used to be
        accepted and silently stored as "0.3333333333333333".

        Refuses to append to a chain that does not verify (BrokenChain). That
        costs a full verification per stamp -- about 10ms per 2000 receipts --
        and the alternative is writing new entries on top of a broken history.
        """
        if not isinstance(amount, str):
            raise TypeError(
                "amount must be a string, got %s. A number here would be "
                "re-formatted differently by different JSON encoders and the "
                "seal would not survive the trip. Pass \"%s\"."
                % (type(amount).__name__, amount))
        ok, bad = self.verify()
        if not ok:
            raise BrokenChain(
                "receipt %s does not verify, so this chain cannot be extended. "
                "Deal with the break rather than building on it." % bad)

        r: dict[str, Any] = {
            "n": len(self.receipts) + 1, "what": what, "amount": amount,
            "payee": payee, "currency": currency, "instrument": instrument,
            "rule": rule, "outcome": outcome,
            "approved_by": self.approved_by if approved_by is None else approved_by,
            "ledger": self.ledger if ledger is None else ledger,
            "at": at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "prev": self.receipts[-1]["seal"] if self.receipts else GENESIS,
        }
        assert_ascii(r)                       # before sealing, never after
        r["seal"] = seal(r, r["prev"])
        self.receipts.append(r)
        return r

    def verify(self) -> tuple[bool, int]:
        return verify(self.receipts)

    @property
    def head(self) -> str:
        """The final seal: the one value that stands for the whole chain."""
        return self.receipts[-1]["seal"] if self.receipts else GENESIS

    def __len__(self) -> int:
        return len(self.receipts)

    def __repr__(self) -> str:
        ok, bad = self.verify()
        state = "verified" if ok else "BROKEN at %s" % bad
        head = self.head[:8] + "..." if self.receipts else GENESIS
        return "<Chain %d receipts, head %s, %s>" % (len(self.receipts), head, state)
