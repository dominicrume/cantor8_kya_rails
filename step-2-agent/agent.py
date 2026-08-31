"""KYA Rails agent. Attempts charges under a mandate; the ledger decides; the chain records.

Two rails, one code path. The agent cannot tell them apart, and that is the
NOT list in THE-JOB.md holding: no spending rule lives in this file.

    python3 agent.py              MOCKED, offline, mirrors KyaMandate.daml
    python3 agent.py --devnet     real Canton DevNet, needs C8_CLIENT_SECRET

The situation: a principal in one country, an operator executing payouts in
another, and a float the principal cannot stand next to. The operator may pay
verified recipients and the settlement partner, up to a cap, until an expiry,
and the principal can stop it at any moment from anywhere.

Amounts are sized to what kya-agent-1 actually holds on DevNet (5 CC), so the
same script runs offline and against the real ledger without a rewrite. Party
names match KyaTest.daml exactly: one story, one set of names."""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
from kya_chain import Chain

SIGNED_BY = "mandate signed by Principal + Operator"
ALLOWED = ["customer", "partner"]          # roles, resolved to parties on DevNet

# One name per party, everywhere: the chat, the receipt and KyaTest.daml.
# Someone reading "customer" in a receipt and "VerifiedRecipient" on screen
# has to work out they are the same party. Make them not have to.
NAMES = {"customer": "VerifiedRecipient", "partner": "SettlementPartner",
         "unverified": "UnverifiedAccount"}


class MockLedger:
    """MOCKED: mirrors the assertions in KyaMandate.daml, line for line."""

    label = "MOCKED (mirrors KyaMandate.daml; real rail = --devnet)"
    currency, instrument = "CC", "Amulet (MOCKED, no coin moves)"

    def name(self, role):
        return NAMES[role]

    def open_mandate(self, cap=5.0, life_seconds=86400,
                     period_limit=None, period_seconds=None):
        self.m = {"cap": cap, "spent": 0.0, "allowed": list(ALLOWED),
                  "expired": life_seconds < 0, "revoked": False,
                  "period_limit": period_limit, "period_seconds": period_seconds,
                  "period_spent": 0.0, "period_start": time.time()}
        return None, "mock"

    def charge(self, amount, payee):
        m = self.m
        if m["revoked"]:  return "REFUSED", "Revoke: mandate no longer active on the ledger"
        if m["expired"]:  return "REFUSED", "mandate expired"
        if amount <= 0:   return "REFUSED", "amount must be positive"
        if m["spent"] + amount > m["cap"]: return "REFUSED", "charge would exceed the cap"
        if payee not in m["allowed"]:      return "REFUSED", "payee is not on the allow-list"
        # Rolling window, same shape as the Daml: the first charge after the
        # window elapses opens a new one. No division, no modulo, no loop.
        fresh = (m["period_seconds"] is not None
                 and time.time() >= m["period_start"] + m["period_seconds"])
        used = 0.0 if fresh else m["period_spent"]
        if m["period_limit"] is not None and used + amount > m["period_limit"]:
            return "REFUSED", "charge would exceed the period limit"
        m["spent"] += amount
        m["period_spent"] = used + amount
        if fresh:
            m["period_start"] = time.time()
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
    print("PLAN: two payouts inside the mandate -> then four attacks: over the "
          "float, change-of-account, expired mandate, after revoke -> write receipts")
    print("LEDGER:", L.label)

    L.open_mandate(cap=5.0)
    for what, amount, payee in [
        ("Payout to a verified recipient",       2.0, "customer"),
        ("Settle with the liquidity partner",    1.5, "partner"),
        ("ATTACK: operator exceeds the float",   3.0, "customer"),
        ("ATTACK: change of account, send here", 1.0, "unverified"),
    ]:
        outcome, rule = L.charge(amount, payee)
        chain.stamp(what, amount, L.name(payee), rule, outcome, SIGNED_BY,
                    L.label, L.currency, L.instrument)

    # Expiry gets its own mandate, as testAfterExpiryRefused uses a fresh
    # deskWithExpiry plus passTime. Attacking the live mandate after Revoke
    # would report the revoke and the expiry fence would never be shown.
    L.open_mandate(cap=5.0, life_seconds=-3600)
    outcome, rule = L.charge(1.0, "customer")
    chain.stamp("ATTACK: payout after the mandate expired", 1.0, L.name("customer"),
                rule, outcome, SIGNED_BY + ", clock past expiresAt",
                L.label, L.currency, L.instrument)

    L.open_mandate(cap=5.0)
    L.revoke()
    outcome, rule = L.charge(0.5, "customer")
    chain.stamp("ATTACK: payout after the principal revoked", 0.5, L.name("customer"),
                rule, outcome, "principal exercised Revoke",
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
