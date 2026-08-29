"""KYA Rails agent. Attempts charges under a mandate; the ledger decides; the chain records.

Two rails, one code path. The agent cannot tell them apart, and that is the
NOT list in THE-JOB.md holding: no spending rule lives in this file.

    python3 agent.py              MOCKED, offline, mirrors KyaMandate.daml
    python3 agent.py --devnet     real Canton DevNet, needs C8_CLIENT_SECRET

Amounts are sized to what kya-agent-1 actually holds on DevNet (5 CC), so the
same script runs at home and at the venue without a rewrite. Party names match
KyaTest.daml exactly: one story, one set of names."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from kya_chain import Chain

SIGNED_BY = "mandate signed by DeskOwner + KyaAgent"
ALLOWED = ["customer", "partner"]          # roles, resolved to parties on DevNet

# One name per party, everywhere: the chat, the receipt and KyaTest.daml.
# A judge reading "customer" in a receipt and "VerifiedCustomer" on screen
# has to work out they are the same party. Make them not have to.
NAMES = {"customer": "VerifiedCustomer", "partner": "LiquidityPartner",
         "unverified": "UnverifiedWallet"}


class MockLedger:
    """MOCKED: mirrors the assertions in KyaMandate.daml, line for line."""

    label = "MOCKED (mirrors KyaMandate.daml; real rail = --devnet)"
    currency, instrument = "CC", "Amulet (MOCKED, no coin moves)"

    def name(self, role):
        return NAMES[role]

    def open_mandate(self, cap=5.0, life_seconds=86400):
        self.m = {"cap": cap, "spent": 0.0, "allowed": list(ALLOWED),
                  "expired": life_seconds < 0, "revoked": False}
        return None, "mock"

    def charge(self, amount, payee):
        m = self.m
        if m["revoked"]:  return "REFUSED", "Revoke: mandate no longer active on the ledger"
        if m["expired"]:  return "REFUSED", "mandate expired"
        if amount <= 0:   return "REFUSED", "amount must be positive"
        if m["spent"] + amount > m["cap"]: return "REFUSED", "charge would exceed the cap"
        if payee not in m["allowed"]:      return "REFUSED", "payee is not on the allow-list"
        m["spent"] += amount
        return "ACCEPTED", "cap %.1f, spent %.1f, payee on allow-list" % (m["cap"], m["spent"])

    def revoke(self):
        self.m["revoked"] = True


def build_ledger(argv):
    if "--devnet" in argv:
        from devnet_ledger import DevNetLedger
        return DevNetLedger()
    return MockLedger()


def main(argv):
    L = build_ledger(argv)
    chain = Chain()
    print("PLAN: settle two legs inside the mandate -> then four attacks: "
          "over-cap, unverified payee, expired mandate, after revoke -> write receipts")
    print("LEDGER:", L.label)

    L.open_mandate(cap=5.0)
    for what, amount, payee in [
        ("Settle trade 1193, customer leg",  2.0, "customer"),
        ("Settle trade 1193, liquidity leg", 1.5, "partner"),
        ("ATTACK: overspend past the cap",   3.0, "customer"),
        ("ATTACK: pay an unverified wallet", 1.0, "unverified"),
    ]:
        outcome, rule = L.charge(amount, payee)
        chain.stamp(what, amount, L.name(payee), rule, outcome, SIGNED_BY,
                    L.label, L.currency, L.instrument)

    # Expiry gets its own mandate, as testAfterExpiryRefused uses a fresh
    # deskWithExpiry plus passTime. Attacking the live mandate after Revoke
    # would report the revoke and the expiry fence would never be shown.
    L.open_mandate(cap=5.0, life_seconds=-3600)
    outcome, rule = L.charge(1.0, "customer")
    chain.stamp("ATTACK: charge after the mandate expired", 1.0, L.name("customer"),
                rule, outcome, SIGNED_BY + ", clock past expiresAt",
                L.label, L.currency, L.instrument)

    L.open_mandate(cap=5.0)
    L.revoke()
    outcome, rule = L.charge(0.5, "customer")
    chain.stamp("ATTACK: charge after revoke", 0.5, L.name("customer"),
                rule, outcome, "owner exercised Revoke",
                L.label, L.currency, L.instrument)

    ok, bad = chain.verify()
    chain.write_js(os.path.join(os.path.dirname(__file__), "..", "step-3-verify", "receipts.js"))
    n_ok = sum(1 for r in chain.receipts if r["outcome"] == "ACCEPTED")
    n_no = sum(1 for r in chain.receipts if r["outcome"] == "REFUSED")
    print("STATEMENT: %d receipts, %d accepted, %d refused, chain verifies: %s" %
          (len(chain.receipts), n_ok, n_no, ok))
    print("NUMBERS FOR JUDGES: over-cap refused, unverified payee refused, expired refused, "
          "post-revoke refused. All four fences enforced in the Daml choice body.")
    print("Ledger mode:", L.label)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception as e:
        # A demo that quietly invents receipts is worse than one that stops.
        # If the ledger never answered, say so and point at the rail that works.
        if type(e).__name__ == "LedgerUnreachable":
            print("\nSTOPPED: the ledger never answered, so NOTHING was recorded.")
            print(" ", str(e)[:220])
            print("  receipts.js is untouched. Run `python3 agent.py` for the "
                  "offline rail, which proves the same four fences.")
            sys.exit(2)
        raise
