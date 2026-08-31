#!/usr/bin/env python3
"""Attack the Breet webhook. An endpoint that confirms deposits causes payouts.

Every test here is someone who has found the URL.

Run: python3 tests/breet_smoke.py
"""
import importlib.util, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in ("step-7-providers", "step-6-whatsapp", "step-5-operator", "step-2-agent"):
    sys.path.insert(0, os.path.join(ROOT, p))
spec = importlib.util.spec_from_file_location(
    "srv", os.path.join(ROOT, "step-5-operator", "server.py"))
srv = importlib.util.module_from_spec(spec); spec.loader.exec_module(srv)
from breet import BreetAdapter, BREET_IPS

SECRET = "sk_test_the_real_secret"
GOOD_IP = sorted(BREET_IPS)[0]
ACCT = "GTB 0123456789 / CHIDI OKAFOR"
fails = []


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


def setup():
    rail = srv.Rail([])
    rail.desk.approved = [ACCT]
    deal = rail.cycle.open_deal("Chidi", "USDT", "TRC20", 10.0, 1250.0, ACCT,
                                None, rail.desk.approved)
    return rail, BreetAdapter(rail.cycle, SECRET), deal


def event(**kw):
    d = {"id": "evt_1", "event": "trade.completed", "asset": "USDT",
         "cryptoAmount": 10.0, "txHash": "0xabc123",
         "destinationAddress": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
         "isWrongAssetDeposit": False}
    d.update(kw)
    return d


H = {"x-webhook-secret": SECRET}
print("KYA Rails - Breet webhook under attack")

# --- authentication ---------------------------------------------------------
rail, a, deal = setup()
code, r = a.handle({"x-webhook-secret": "wrong"}, GOOD_IP, event())
check(code == 401, "a wrong secret is rejected with 401")
check("reason" not in r and r.get("error") == "unauthorised",
      "the rejection leaks nothing about why")

rail, a, deal = setup()
code, r = a.handle({}, GOOD_IP, event())
check(code == 401, "a missing secret header is rejected")

rail, a, deal = setup()
code, r = a.handle(H, "203.0.113.9", event())
check(code == 401, "a request from outside the provider's IP range is rejected")

try:
    BreetAdapter(rail.cycle, "")
    check(False, "an empty secret is refused at construction")
except ValueError:
    check(True, "an empty secret is refused at construction")

# --- the happy path ---------------------------------------------------------
rail, a, deal = setup()
code, r = a.handle(H, GOOD_IP, event())
check(code == 200 and r.get("acted") is True, "a valid completed deposit confirms the deal")
check(rail.cycle.deals[deal["reference"]]["state"] == "DEPOSITED",
      "the deal moves to DEPOSITED")

# --- replay -----------------------------------------------------------------
code, r = a.handle(H, GOOD_IP, event())
check(code == 200 and r.get("acted") is False and "duplicate" in r["reason"],
      "a replayed delivery does not confirm twice")

# --- event types ------------------------------------------------------------
rail, a, deal = setup()
code, r = a.handle(H, GOOD_IP, event(event="trade.pending"))
check(r.get("acted") is False, "a pending trade confirms nothing")
check(rail.cycle.deals[deal["reference"]]["state"] == "QUOTED", "the deal has not moved")

rail, a, deal = setup()
code, r = a.handle(H, GOOD_IP, event(event="trade.flagged"))
check(r.get("acted") is False, "a flagged trade confirms nothing")

# --- the provider's own warning --------------------------------------------
rail, a, deal = setup()
code, r = a.handle(H, GOOD_IP, event(isWrongAssetDeposit=True))
check(r.get("acted") is False and "wrong-asset" in r["reason"],
      "a wrong-asset deposit is refused even though everything else matches")

# --- attribution ------------------------------------------------------------
rail, a, deal = setup()
code, r = a.handle(H, GOOD_IP, event(destinationAddress="TSomeOtherAddress"))
check(r.get("acted") is False, "a deposit to an address we did not issue is refused")

rail, a, deal = setup()
code, r = a.handle(H, GOOD_IP, event(cryptoAmount=9.5))
check(r.get("acted") is False and "does not match" in r["reason"],
      "an amount that does not match the quote is refused")

rail, a, deal = setup()
code, r = a.handle(H, GOOD_IP, event(asset="BTC"))
check(r.get("acted") is False, "an asset that does not match the deal is refused")

rail, a, deal = setup()
code, r = a.handle(H, GOOD_IP, event(txHash=None))
check(r.get("acted") is False, "no txHash means no confirmation")

rail, a, deal = setup()
code, r = a.handle(H, GOOD_IP, event(id=None))
check(r.get("acted") is False, "an event with no id cannot be deduplicated, so it is refused")

# --- refusals are recorded --------------------------------------------------
rail, a, deal = setup()
a.handle({"x-webhook-secret": "wrong"}, GOOD_IP, event())
a.handle(H, GOOD_IP, event(event="trade.flagged"))
a.handle(H, GOOD_IP, event(id="evt_2"))
check(len(a.log) == 3, "every delivery is logged, accepted or not")
check([e["outcome"] for e in a.log] == ["REJECTED", "REFUSED", "CONFIRMED"],
      "the log distinguishes rejected, refused and confirmed")

print()
if fails:
    print("BREET SMOKE FAILED - %d:" % len(fails))
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("the webhook confirms only what matches a deal we already hold.")
