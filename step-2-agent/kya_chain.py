"""KYA receipt chain. Stdlib only. The seal math must match verifier.html exactly."""
import json, hashlib, time

class NonAsciiInReceipt(ValueError):
    """A hashed field carried a character Python and JS canonicalise differently."""

def canonical(d):
    # ensure_ascii=True is NOT decoration. Python escapes non-ASCII to \uXXXX;
    # JS JSON.stringify emits the raw character. Same receipt, different bytes,
    # different sha256 -- the chain would verify in Python and go red in the
    # browser. Proven: "\u20a6" seals 89e828df..., "N" raw seals 71e44b13...
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

def _non_ascii_anywhere(value):
    """Is there a character above 0x7E anywhere in here, however deeply nested?

    SPEC.md section 5 says ANY field, and this only looked at the top level:
    {"what": "Pay \u20a6500"} was refused and {"what": {"note": "Pay
    \u20a6500"}} sailed through. The fix reached pkg/ and never reached here --
    the implementation the specification actually names.
    """
    if isinstance(value, str):
        return not value.isascii()
    if isinstance(value, dict):
        return any(_non_ascii_anywhere(k) or _non_ascii_anywhere(v)
                   for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(_non_ascii_anywhere(v) for v in value)
    return False


def _first_non_ascii(d):
    """The first field carrying a character outside ASCII, or (None, None)."""
    for k, v in d.items():
        if _non_ascii_anywhere(k) or _non_ascii_anywhere(v):
            return k, v if isinstance(v, str) else canonical(v)
    return None, None


def assert_ascii(d):
    """Refuse to seal what the verifier cannot reproduce. Guard, not hope.

    Currency SYMBOLS are a display concern: put the code (CC, USD) in the
    receipt and render the glyph in verifier.html."""
    field, text = _first_non_ascii(d)
    if field is None:
        return
    bad = [c for c in text if not c.isascii()]
    raise NonAsciiInReceipt(
        "field %r carries non-ASCII %r. Python would hash it as %s, "
        "the browser as the raw character, and the chain would break "
        "in front of a judge. Use an ASCII currency code."
        % (field, "".join(bad), "".join("\\u%04x" % ord(c) for c in bad)))

def seal(receipt_without_seal, prev_seal):
    return hashlib.sha256((canonical(receipt_without_seal) + prev_seal).encode()).hexdigest()

class Chain:
    def __init__(self):
        self.receipts = []

    def stamp(self, what, amount, payee, rule, outcome, approved_by,
              ledger, currency="CC", instrument="Amulet"):
        r = {
            "n": len(self.receipts) + 1,
            "what": what, "amount": str(amount), "payee": payee,
            "currency": currency,    # ASCII code, never a symbol: see assert_ascii
            "instrument": instrument,
            "rule": rule,            # which mandate line allowed or refused it
            "outcome": outcome,      # ACCEPTED or REFUSED
            "approved_by": approved_by,
            "ledger": ledger,        # which rail produced this: real or MOCKED
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "prev": self.receipts[-1]["seal"] if self.receipts else "GENESIS",
        }
        assert_ascii(r)          # before sealing, never after
        r["seal"] = seal(r, r["prev"])
        self.receipts.append(r)
        return r

    def verify(self):
        prev = "GENESIS"
        for r in self.receipts:
            body = {k: v for k, v in r.items() if k != "seal"}
            if r["prev"] != prev or seal(body, prev) != r["seal"]:
                return False, r["n"]
            prev = r["seal"]
        return True, None

    def write_js(self, path):
        with open(path, "w") as f:
            f.write("const RECEIPTS = " + json.dumps(self.receipts, indent=2) + ";")
