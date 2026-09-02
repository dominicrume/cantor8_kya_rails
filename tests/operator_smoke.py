#!/usr/bin/env python3
"""Drive the operator rail over HTTP and prove the fences reach the screen.

The interface is where the fences either hold or quietly stop mattering, so
this exercises the same endpoints the phone does.

Run: python3 tests/operator_smoke.py
"""
import json, os, subprocess, sys, tempfile, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, "..", "step-5-operator", "server.py")
PORT = "8421"
BASE = "http://127.0.0.1:" + PORT


def _http(url, **kw):
    """urlopen, restricted to http. Bandit flags bare urlopen because it will
    happily open file:// and ftp://; every URL here is our own test server, and
    saying so in code is better than saying so in a comment."""
    if not url.startswith(("http://127.0.0.1", "http://localhost")):
        raise ValueError("refusing a non-local URL: %r" % url)
    return urllib.request.urlopen(url, **kw)


def call(path, body=None):
    req = urllib.request.Request(BASE + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="GET" if body is None else "POST")
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


# --ephemeral, and a KYA_STORE pointed somewhere harmless as a second line of
# defence. Persistence is the server's default, so a test that spawns it
# without saying otherwise writes into the operator's real desk journal --
# which is exactly what happened once and is why both are here. What this
# file tests is whether the fences reach the screen; tests/store_smoke.py
# tests persistence.
env = dict(os.environ, KYA_PORT=PORT,
           KYA_STORE=os.path.join(tempfile.mkdtemp(), "never-used.db"))
proc = subprocess.Popen([sys.executable, SERVER, "--ephemeral"], env=env,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
fails = []


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


try:
    for _ in range(40):                     # wait for the port
        try:
            call("/api/state"); break
        except Exception:
            time.sleep(0.25)

    print("KYA Rails - operator interface smoke test")
    s = call("/api/open", {"cap": 5.0, "period_limit": 3.0, "period_seconds": 86400})
    check(s["open"] is True, "mandate opens")
    check(abs(s["remaining"] - 5.0) < 1e-9, "float shows the full cap before any payout")
    check([r["key"] for r in s["recipients"]] == ["customer", "partner"],
          "only authorised accounts are offered")

    a = call("/api/request", {"amount": 2.0, "payee": "customer", "what": "payout 1"})
    check(a["outcome"] == "ACCEPTED", "payout inside the mandate is paid")
    check("seal" in a["receipt"], "an accepted payout is sealed")

    s = call("/api/state")
    check(abs(s["remaining"] - 3.0) < 1e-9, "float falls by the amount paid")

    b = call("/api/request", {"amount": 1.5, "payee": "customer", "what": "same window"})
    check(b["outcome"] == "REFUSED" and "period" in b["rule"],
          "period limit refuses while the cap still has room")

    c = call("/api/request", {"amount": 1.0, "payee": "unverified",
                              "what": "customer says this is their new account"})
    check(c["outcome"] == "REFUSED" and "allow-list" in c["rule"],
          "an account not on the allow-list is refused")

    d = call("/api/request", {"amount": 1.0, "payee": "customer",
                              "what": "note with a curly quote ’ in it"})
    check("error" in d, "a receipt that could not be verified is never sealed")

    call("/api/revoke", {})
    e = call("/api/request", {"amount": 0.5, "payee": "customer", "what": "after revoke"})
    check(e["outcome"] == "REFUSED", "nothing is paid after the principal revokes")

    # --- the quote desk: the fraud the desk actually lost money to ---
    q = call("/api/quote", {"customer": "Blessing", "rate": 1250, "amount": 10,
                            "payout_account": "UBA 2233445566 / BLESSING ADEYEMI"})
    check("reference" in q, "a quote is issued to an approved account")
    ref = q["reference"]

    bad = call("/api/quote", {"customer": "Jennifer", "rate": 1250, "amount": 10,
                              "payout_account": "OPAY 5555555555 / THE OPERATOR"})
    check("error" in bad and "approved" in bad["error"],
          "the operator cannot quote to an account the principal never approved")

    claim = call("/api/fulfil", {"reference": ref, "amount": 10,
                                 "claimed_account": "OPAY 9999999999 / UNKNOWN",
                                 "what": "claimant with a screenshot"})
    check(claim["outcome"] == "REFUSED" and "payout account does not match" in claim["rule"],
          "a claimant cannot redirect someone else's deposit to their own account")

    paid = call("/api/fulfil", {"reference": ref, "amount": 10,
                                "claimed_account": "UBA 2233445566 / BLESSING ADEYEMI",
                                "what": "settle Blessing"})
    check(paid["outcome"] == "PAID", "the real customer is paid to the account on the quote")

    twice = call("/api/fulfil", {"reference": ref, "amount": 10,
                                 "claimed_account": "UBA 2233445566 / BLESSING ADEYEMI",
                                 "what": "second attempt on the same deposit"})
    check(twice["outcome"] == "REFUSED" and "already been paid" in twice["rule"],
          "the same quote cannot pay twice -- the other half of the real loss")

    s = call("/api/state")
    check(all(r.get("ledger") for r in s["receipts"]),
          "every receipt on the operator's screen names its ledger")
    refused = sum(1 for r in s["receipts"] if r["outcome"] == "REFUSED")
    check(refused == 5, "every refusal is on the operator's own record (got %d)" % refused)
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()

print()
if fails:
    print("OPERATOR SMOKE FAILED - %d:" % len(fails))
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("operator interface: the fences reach the screen, and every refusal is recorded.")
