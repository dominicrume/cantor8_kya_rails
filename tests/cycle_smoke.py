#!/usr/bin/env python3
"""Drive the whole OTC cycle over HTTP, in the order a desk actually works it.

Not a unit test of four contracts. The desk's failures happen BETWEEN steps --
paying before the deposit is confirmed, paying before the off-taker's naira
arrives, sending crypto to a wallet that came in on WhatsApp this morning --
so this walks the cycle and attacks the joins.

Run: python3 tests/cycle_smoke.py
"""
import json, os, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, "..", "step-5-operator", "server.py")
PORT = "8422"
BASE = "http://127.0.0.1:" + PORT

TRC = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
CUSTOMER_ACCT = "GTB 0123456789 / CHIDI OKAFOR"


def call(path, body=None):
    req = urllib.request.Request(BASE + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="GET" if body is None else "POST")
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


proc = subprocess.Popen([sys.executable, SERVER], env=dict(os.environ, KYA_PORT=PORT),
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
fails = []


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


try:
    for _ in range(40):
        try:
            call("/api/state"); break
        except Exception:
            time.sleep(0.25)

    print("KYA Rails - the OTC cycle, end to end")
    call("/api/open", {"cap": 100000.0})
    call("/api/approve", {"account": CUSTOMER_ACCT})

    # --- leg 1: the deposit instruction ---
    bad_net = call("/api/deal", {"customer": "Chidi", "asset": "USDT",
        "network": "BEP20", "amount": 10, "rate": 1250,
        "payout_account": CUSTOMER_ACCT})
    check("error" in bad_net and "no approved address" in bad_net["error"],
          "a network the desk holds no address for is refused")

    no_memo = call("/api/deal", {"customer": "Chidi", "asset": "XRP",
        "network": "XRPL", "amount": 10, "rate": 1250,
        "payout_account": CUSTOMER_ACCT})
    check("error" in no_memo and "memo" in no_memo["error"],
          "a memo-required network is refused without a memo")

    deal = call("/api/deal", {"customer": "Chidi", "asset": "USDT",
        "network": "TRC20", "amount": 10, "rate": 1250,
        "payout_account": CUSTOMER_ACCT})
    check("reference" in deal, "a deal opens for an approved asset and network")
    check(deal["depositAddress"] == TRC, "the customer gets the right address for their chain")
    ref = deal["reference"]

    # --- the join that costs money: paying before the deposit is in ---
    early = call("/api/pay", {"reference": ref, "amount": 10,
                              "claimed_account": CUSTOMER_ACCT})
    check(early["outcome"] == "REFUSED" and "deposit has not been confirmed" in early["rule"],
          "paying before the deposit is confirmed is refused")

    call("/api/deposit-confirmed", {"reference": ref})

    # --- leg 2: the off-taker ---
    fresh_wallet = call("/api/offtaker", {"reference": ref, "offtaker": "Supplier A",
        "address": "TNewAddressTheySentOnWhatsAppThisMorning"})
    check(fresh_wallet["outcome"] == "REFUSED" and "not approved" in fresh_wallet["rule"],
          "crypto cannot go to an off-taker wallet that arrived this morning")

    sent = call("/api/offtaker", {"reference": ref, "offtaker": "Supplier A", "address": TRC})
    check(sent["outcome"] == "SENT", "crypto goes to the approved off-taker wallet")

    before_naira = call("/api/pay", {"reference": ref, "amount": 10,
                                     "claimed_account": CUSTOMER_ACCT})
    check(before_naira["outcome"] == "REFUSED" and "naira has not been received" in before_naira["rule"],
          "paying the customer before the off-taker's naira arrives is refused")

    short = call("/api/naira", {"reference": ref, "received": 10000})
    check(short["outcome"] == "REFUSED" and "short of the amount agreed" in short["rule"],
          "short naira is refused, not negotiated at 2am")

    full = call("/api/naira", {"reference": ref, "received": 12500})
    check(full["outcome"] == "RECEIVED", "full naira is accepted")

    # --- leg 3: the customer payout, and the fraud ---
    claim = call("/api/pay", {"reference": ref, "amount": 10,
                              "claimed_account": "OPAY 9999999999 / UNKNOWN"})
    check(claim["outcome"] == "REFUSED" and "payout account does not match" in claim["rule"],
          "a claimant cannot redirect the payout at the last step either")

    paid = call("/api/pay", {"reference": ref, "amount": 10, "claimed_account": CUSTOMER_ACCT})
    check(paid["outcome"] == "PAID", "the customer is paid, and only now")

    again = call("/api/pay", {"reference": ref, "amount": 10, "claimed_account": CUSTOMER_ACCT})
    check(again["outcome"] == "REFUSED" and "already been paid" in again["rule"],
          "the cycle cannot pay twice")

    # --- the customer's view: the link you send on WhatsApp ---
    cust = call("/api/customer?ref=" + ref)
    check(cust["depositAddress"] == TRC and cust["network"] == "TRC20",
          "the customer sees the address and the network they must use")
    check(cust["payoutAccount"] == CUSTOMER_ACCT,
          "the customer sees the account they will be paid to")
    check(cust["state"] == "PAID", "the customer sees where the deal has got to")
    check(cust.get("receipt") and cust["receipt"]["seal"],
          "the customer gets their sealed receipt")
    leaked = [k for k in ("offtaker", "nairaReceived", "opened", "expiresAt")
              if k in cust]
    check(not leaked, "the desk's internals are not on the customer's page (%s)" % leaked)

    missing = None
    try:
        call("/api/customer?ref=KYA-DOESNOTEXIST")
    except Exception as e:
        missing = getattr(e, "code", None)
    check(missing == 404, "an unknown reference is a 404, not someone else's deal")

    s = call("/api/state")
    d = [x for x in s["deals"] if x["reference"] == ref][0]
    check(d["state"] == "PAID", "the deal ends in PAID with the whole path on record")
    check(sum(1 for r in s["receipts"] if r["outcome"] == "REFUSED") >= 4,
          "every refused attempt along the way is a sealed receipt")
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()

print()
if fails:
    print("CYCLE SMOKE FAILED - %d:" % len(fails))
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("the cycle holds at every join, and every refusal is on record.")
