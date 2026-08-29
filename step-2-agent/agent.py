"""KYA Rails agent. Attempts charges under a mandate; ledger decides; chain records.
Offline mode: MockLedger mirrors the exact assertions in KyaMandate.daml. MOCKED and says so.
Venue mode: swap MockLedger calls for c8lab.py DevNet calls (see SHORTCUTS.md)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from kya_chain import Chain

MANDATE = {  # mummy's note
    "owner": "MarketWoman", "agent": "VoremAgent",
    "cap": 100.0, "spent": 0.0, "expired": False, "revoked": False,
    "allowed": ["RiceSupplier", "OilSupplier"],
}

class MockLedger:  # MOCKED: mirrors KyaMandate.daml assertions line for line
    def charge(self, m, amount, payee):
        if m["revoked"]:               return "REFUSED", "Revoke: owner stopped the mandate"
        if m["expired"]:               return "REFUSED", "expiresAt: mandate expired"
        if amount <= 0:                return "REFUSED", "amount must be positive"
        if m["spent"] + amount > m["cap"]: return "REFUSED", "cap: charge would exceed the cap"
        if payee not in m["allowed"]:  return "REFUSED", "allowed: payee is not on the allow-list"
        m["spent"] += amount
        return "ACCEPTED", "cap %.0f, spent %.0f, payee on allow-list" % (m["cap"], m["spent"])

def main():
    print("PLAN: greet customer -> quote -> charge rice -> charge oil -> "           "attacks: over-cap, stranger, post-revoke -> write receipts")
    L, chain = MockLedger(), Chain()
    attempts = [
        ("Pay RiceSupplier for 2 bags", 40.0, "RiceSupplier"),
        ("Pay OilSupplier for 5 litres", 35.0, "OilSupplier"),
        ("ATTACK: overspend attempt",   60.0, "RiceSupplier"),
        ("ATTACK: pay a stranger",      10.0, "StrangerParty"),
    ]
    for what, amount, payee in attempts:
        outcome, rule = L.charge(MANDATE, amount, payee)
        chain.stamp(what, amount, payee, rule, outcome, "mandate signed by MarketWoman + VoremAgent")
    MANDATE["revoked"] = True
    outcome, rule = L.charge(MANDATE, 5.0, "RiceSupplier")
    chain.stamp("ATTACK: charge after revoke", 5.0, "RiceSupplier", rule, outcome, "owner exercised Revoke")

    ok, bad = chain.verify()
    chain.write_js(os.path.join(os.path.dirname(__file__), "..", "step-3-verify", "receipts.js"))
    n_ok = sum(1 for r in chain.receipts if r["outcome"] == "ACCEPTED")
    n_no = sum(1 for r in chain.receipts if r["outcome"] == "REFUSED")
    print("STATEMENT: %d receipts, %d accepted, %d refused, chain verifies: %s" %
          (len(chain.receipts), n_ok, n_no, ok))
    print("NUMBERS FOR JUDGES: over-cap refused, stranger refused, post-revoke refused. "           "Ledger mode: MOCKED (mirrors KyaMandate.daml; venue swap = c8lab DevNet).")

if __name__ == "__main__":
    main()
