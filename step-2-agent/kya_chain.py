"""KYA receipt chain. Stdlib only. The seal math must match verifier.html exactly."""
import json, hashlib, time

def canonical(d):
    return json.dumps(d, sort_keys=True, separators=(",", ":"))

def seal(receipt_without_seal, prev_seal):
    return hashlib.sha256((canonical(receipt_without_seal) + prev_seal).encode()).hexdigest()

class Chain:
    def __init__(self):
        self.receipts = []

    def stamp(self, what, amount, payee, rule, outcome, approved_by):
        r = {
            "n": len(self.receipts) + 1,
            "what": what, "amount": str(amount), "payee": payee,
            "rule": rule,            # which mandate line allowed or refused it
            "outcome": outcome,      # ACCEPTED or REFUSED
            "approved_by": approved_by,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "prev": self.receipts[-1]["seal"] if self.receipts else "GENESIS",
        }
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
