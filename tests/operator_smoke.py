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
    """Every response is watched, so the end of this file can compare what the
    desk SAID against what it actually wrote down."""
    req = urllib.request.Request(BASE + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="GET" if body is None else "POST")
    out = json.loads(urllib.request.urlopen(req, timeout=10).read())
    if isinstance(out, dict) and out.get("outcome") == "REFUSED":
        SEEN_REFUSALS.append((path, out.get("rule", "")))
    return out


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


# Every refusal this test watched the desk hand back. Filled in by call().
SEEN_REFUSALS = []


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

    # The line above passed for months while this one crashed the desk.
    # "unverified" is one of the three names the mock ledger knows, so it
    # survived the NAMES[role] lookup; a payee nobody has ever heard of --
    # which is the actual fraud -- raised KeyError AFTER charge() had already
    # refused it, so the caller got a 500 and NOTHING WAS WRITTEN. The one
    # attempt most worth having in the audit trail was the one thrown away.
    c2 = call("/api/request", {"amount": 1.0, "payee": "Fraudster Ltd",
                               "what": "urgent, new supplier"})
    check(c2.get("outcome") == "REFUSED" and "allow-list" in c2.get("rule", ""),
          "a payee this desk has never heard of is refused, not crashed on")
    check("receipt" in c2 and c2["receipt"]["payee"] == "Fraudster Ltd",
          "and the refusal is SEALED INTO THE CHAIN, naming who was asked for")

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
    # This was `refused == 5`. A hardcoded count does not check what the line
    # says it checks -- it goes red when a NEW refusal case is added, which is
    # the opposite of useful, and it would stay green if a refusal were
    # answered to the caller and never written. So compare the record against
    # what this test actually watched happen.
    on_record = sum(1 for r in s["receipts"] if r["outcome"] == "REFUSED")
    check(on_record == len(SEEN_REFUSALS),
          "every refusal the desk answered is also on its record (%d answered, "
          "%d recorded)" % (len(SEEN_REFUSALS), on_record))
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
