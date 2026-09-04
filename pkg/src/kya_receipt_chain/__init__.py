"""A tamper-evident receipt chain that records refusals, not only successes.

Most audit logs record what happened. This records what was *attempted and
stopped*, which is the artefact anyone checking your system actually asks for
-- and it seals each entry to the one before, so editing history is detectable.

    from kya_receipt_chain import Chain

    chain = Chain()
    chain.stamp(what="payout to supplier", amount="10.0", payee="Chidi",
                rule="inside the cap", outcome="ACCEPTED",
                approved_by="principal", ledger="production")
    chain.stamp(what="payout to an unknown account", amount="5.0",
                payee="Stranger", rule="payee is not on the allow-list",
                outcome="REFUSED", approved_by="principal", ledger="production")

    ok, first_bad = chain.verify()      # (True, 0)

The format is specified in full at SPEC.md in the repository, in about a page.
It is roughly twenty lines to implement, and there are conformance vectors so a
new implementation can prove itself:

    python -m kya_receipt_chain          # self-test against the shipped vectors

WHAT THIS DOES NOT DO, stated here because a format that oversells itself is
worse than none:

  * It is not signed. It proves internal consistency, not origin -- anyone can
    produce a valid chain saying anything, and a forged one verifies. Bind the
    final seal to something you do not control if origin matters. The reference
    application publishes it on a Canton ledger.
  * It does not prove a rule was enforced. `rule` is a string. The guarantee
    comes from wherever the decision was made.
  * It makes editing detectable, not deletion. Publish the final seal somewhere
    else if discarding the whole chain matters.

Zero dependencies, by design: the whole format is `json` and `hashlib`. A
dependency here would be a dependency in everyone's audit trail.
"""
import hashlib, json, time

__version__ = "1.0.0"
__all__ = ["canonical", "seal", "verify", "assert_ascii", "Chain",
           "NonAsciiInReceipt", "GENESIS"]

GENESIS = "GENESIS"


class NonAsciiInReceipt(ValueError):
    """A hashed field carried a character outside ASCII.

    Raised before sealing, never after. Python escapes non-ASCII to \\uXXXX and
    JavaScript's JSON.stringify emits the raw character, so the same receipt
    would seal to two different hashes and the chain would verify in one
    language and go red in the other.
    """


def canonical(obj):
    """The exact bytes that get hashed: sorted keys, no spaces, ASCII-escaped."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def seal(body, prev):
    """sha256(canonical(body) + prev), lowercase hex.

    `body` is the receipt without its own `seal` key. `prev` is the previous
    receipt's seal, or GENESIS for the first.
    """
    return hashlib.sha256((canonical(body) + prev).encode()).hexdigest()


def _first_non_ascii(d):
    for key, value in d.items():
        for text in (key, value):
            if isinstance(text, str) and not text.isascii():
                return key, text
    return None, None


def assert_ascii(d):
    """Raise NonAsciiInReceipt if any key or string value is not ASCII."""
    field, text = _first_non_ascii(d)
    if field is None:
        return
    bad = [c for c in text if not c.isascii()]
    raise NonAsciiInReceipt(
        "field %r contains %s, which would seal differently in another "
        "language. Render symbols at display time, not inside the seal."
        % (field, ", ".join(repr(c) for c in bad[:3])))


def verify(receipts):
    """(True, 0) if the chain holds, else (False, n of the first bad receipt).

    Both the seal and the `prev` link are checked. A chain whose seals all
    recompute but whose links do not line up is not a chain.
    """
    prev = GENESIS
    for r in receipts:
        body = {k: v for k, v in r.items() if k != "seal"}
        if r.get("prev") != prev or seal(body, prev) != r.get("seal"):
            return False, r.get("n")
        prev = r["seal"]
    return True, 0


class Chain:
    """An append-only list of sealed receipts."""

    def __init__(self, receipts=None):
        self.receipts = list(receipts or [])

    def stamp(self, what, amount, payee, rule, outcome, approved_by, ledger,
              currency="CC", instrument="", at=None):
        """Append one receipt and return it.

        `amount` is a string on purpose. A float that survives one language's
        JSON encoder is not a float that survives all of them, and a seal
        computed over "1.0" is not the seal computed over "1".
        """
        r = {"n": len(self.receipts) + 1, "what": what, "amount": str(amount),
             "payee": payee, "currency": currency, "instrument": instrument,
             "rule": rule, "outcome": outcome, "approved_by": approved_by,
             "ledger": ledger,
             "at": at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "prev": self.receipts[-1]["seal"] if self.receipts else GENESIS}
        assert_ascii(r)                       # before sealing, never after
        r["seal"] = seal(r, r["prev"])
        self.receipts.append(r)
        return r

    def verify(self):
        return verify(self.receipts)

    @property
    def head(self):
        """The final seal: the one value that stands for the whole chain."""
        return self.receipts[-1]["seal"] if self.receipts else GENESIS

    def __len__(self):
        return len(self.receipts)
