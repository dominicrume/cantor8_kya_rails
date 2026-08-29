"""KYA Rails agent. Attempts charges under a mandate; ledger decides; chain records.
Offline mode: MockLedger mirrors the exact assertions in KyaMandate.daml. MOCKED and says so.
Venue mode: swap MockLedger calls for c8lab.py DevNet calls (see SHORTCUTS.md).

Amounts are sized to what kya-agent-1 actually holds on DevNet (5 CC), so the
same script runs mocked at home and for real at the venue without a rewrite.
Party names match KyaTest.daml exactly: one story, one set of names."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from kya_chain import Chain

SIGNED_BY = "mandate signed by DeskOwner + KyaAgent"

MANDATE = {  # the desk owner's written mandate
    "owner": "DeskOwner", "agent": "KyaAgent",
    "cap": 5.0, "spent": 0.0, "expired": False, "revoked": False,
    "allowed": ["VerifiedCustomer", "LiquidityPartner"],
}

class MockLedger:  # MOCKED: mirrors KyaMandate.daml assertions line for line
    def charge(self, m, amount, payee):
        if m["revoked"]:               return "REFUSED", "Revoke: owner stopped the mandate"
        if m["expired"]:               return "REFUSED", "expiresAt: mandate expired"
        if amount <= 0:                return "REFUSED", "amount must be positive"
        if m["spent"] + amount > m["cap"]: return "REFUSED", "cap: charge would exceed the cap"
        if payee not in m["allowed"]:  return "REFUSED", "allowed: payee is not on the allow-list"
        m["spent"] += amount
        return "ACCEPTED", "cap %.1f, spent %.1f, payee on allow-list" % (m["cap"], m["spent"])

def main():
    print("PLAN: settle two legs inside the mandate -> then four attacks: "
          "over-cap, unverified payee, expired mandate, after revoke -> write receipts")
    L, chain = MockLedger(), Chain()

    # Two legal settlements, then two attacks on the SAME live mandate.
    for what, amount, payee in [
        ("Settle trade 1193, customer leg",  2.0, "VerifiedCustomer"),
        ("Settle trade 1193, liquidity leg", 1.5, "LiquidityPartner"),
        ("ATTACK: overspend past the cap",   3.0, "VerifiedCustomer"),
        ("ATTACK: pay an unverified wallet", 1.0, "UnverifiedWallet"),
    ]:
        outcome, rule = L.charge(MANDATE, amount, payee)
        chain.stamp(what, amount, payee, rule, outcome, SIGNED_BY)

    # Expiry needs its own mandate, exactly as testAfterExpiryRefused uses a
    # fresh one with passTime. Attacking the live mandate after Revoke would
    # report the revoke, and the expiry fence would never be shown.
    expired = dict(MANDATE, spent=0.0, expired=True)
    outcome, rule = L.charge(expired, 1.0, "VerifiedCustomer")
    chain.stamp("ATTACK: charge after the mandate expired", 1.0, "VerifiedCustomer",
                rule, outcome, SIGNED_BY + ", clock past expiresAt")

    MANDATE["revoked"] = True
    outcome, rule = L.charge(MANDATE, 0.5, "VerifiedCustomer")
    chain.stamp("ATTACK: charge after revoke", 0.5, "VerifiedCustomer",
                rule, outcome, "owner exercised Revoke")

    ok, bad = chain.verify()
    chain.write_js(os.path.join(os.path.dirname(__file__), "..", "step-3-verify", "receipts.js"))
    n_ok = sum(1 for r in chain.receipts if r["outcome"] == "ACCEPTED")
    n_no = sum(1 for r in chain.receipts if r["outcome"] == "REFUSED")
    print("STATEMENT: %d receipts, %d accepted, %d refused, chain verifies: %s" %
          (len(chain.receipts), n_ok, n_no, ok))
    print("NUMBERS FOR JUDGES: over-cap refused, unverified payee refused, expired refused, "
          "post-revoke refused. All four fences enforced in the Daml choice body.")
    print("Ledger mode: MOCKED (mirrors KyaMandate.daml; venue swap = c8lab DevNet).")

if __name__ == "__main__":
    main()
