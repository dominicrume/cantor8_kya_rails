#!/usr/bin/env python3
"""Prove the Breet webhook is reachable, and that its IP check survives HTTP.

breet_smoke.py attacks the adapter with an IP handed to it directly. Over a
real socket the IP has to come from somewhere, and that is where this class
of check usually dies: the server sits behind a proxy, someone reads
X-Forwarded-For to get the "real" caller, and the provider's allowlist
becomes a header any attacker can set.

So the cases that matter here are the ones about where the address came from.

Run: python3 tests/breet_wire_smoke.py
"""
import hashlib, importlib.util, json, os, socketserver, sys, threading
import urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET = "FIXTURE-" + hashlib.sha256(b"breet_wire").hexdigest()[:24]
ACCT = "GTB 0123456789 / CHIDI OKAFOR"

os.environ["KYA_BREET_SECRET"] = SECRET
for p in ("step-7-providers", "step-6-whatsapp", "step-5-operator", "step-2-agent"):
    sys.path.insert(0, os.path.join(ROOT, p))
spec = importlib.util.spec_from_file_location(
    "srv", os.path.join(ROOT, "step-5-operator", "server.py"))
srv = importlib.util.module_from_spec(spec); spec.loader.exec_module(srv)
from breet import BREET_IPS

GOOD_IP = sorted(BREET_IPS)[0]
fails = []


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


def fresh(require_ip=True, trust_proxy=False):
    """A server-side rail and adapter, as build_breet would make them."""
    os.environ["KYA_BREET_REQUIRE_IP"] = "1" if require_ip else "0"
    os.environ["KYA_BREET_TRUST_PROXY"] = "1" if trust_proxy else "0"
    srv.RAIL = srv.Rail([])
    srv.RAIL.desk.approved = [ACCT]
    deal = srv.RAIL.cycle.open_deal("Chidi", "USDT", "TRC20", 10.0, 1250.0,
                                    ACCT, None, srv.RAIL.desk.approved)
    srv.BREET = srv.build_breet(srv.RAIL)
    return deal


def event(**kw):
    d = {"id": "evt_wire_1", "event": "trade.completed", "asset": "USDT",
         "cryptoAmount": 10.0, "txHash": "0xabc123",
         "destinationAddress": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
         "isWrongAssetDeposit": False}
    d.update(kw)
    return json.dumps(d).encode()


def post(path, data, headers):
    req = urllib.request.Request(BASE + path, data=data, method="POST",
                                 headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}


H = {"x-webhook-secret": SECRET, "Content-Type": "application/json"}
print("KYA Rails - is the Breet webhook actually wired in?")

deal = fresh()
check(srv.BREET is not None, "build_breet returns an adapter when the secret is set")

socketserver.TCPServer.allow_reuse_address = True
httpd = socketserver.TCPServer(("127.0.0.1", 0), srv.Handler)
BASE = "http://127.0.0.1:%d" % httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()

try:
    # -- the allowlist is real over the wire --------------------------------
    # The test client is on 127.0.0.1, which is not a Breet address. With the
    # allowlist on, a perfectly valid delivery must still be refused.
    code, r = post(srv.BREET_PATH, event(), H)
    check(code == 401, "a correct secret from a non-provider IP is still 401")
    check(srv.RAIL.cycle.deals[deal["reference"]]["state"] == "QUOTED",
          "and the deal is untouched")

    # -- the spoof this wiring makes possible -------------------------------
    # Proxy trust is OFF. Claiming to be Breet in a header must change nothing.
    deal = fresh(require_ip=True, trust_proxy=False)
    code, r = post(srv.BREET_PATH, event(),
                   dict(H, **{"X-Forwarded-For": GOOD_IP}))
    check(code == 401, "X-Forwarded-For claiming a provider IP is ignored")
    check(srv.RAIL.cycle.deals[deal["reference"]]["state"] == "QUOTED",
          "and confirms nothing")

    # Several hops, the attacker's own value first. Even with trust ON, only
    # the LAST entry counts -- the one a real proxy would have appended.
    deal = fresh(require_ip=True, trust_proxy=True)
    code, r = post(srv.BREET_PATH, event(),
                   dict(H, **{"X-Forwarded-For": "%s, 203.0.113.9" % GOOD_IP}))
    check(code == 401, "with proxy trust on, an attacker-supplied first hop is ignored")

    # -- and the legitimate proxy path still works --------------------------
    deal = fresh(require_ip=True, trust_proxy=True)
    code, r = post(srv.BREET_PATH, event(),
                   dict(H, **{"X-Forwarded-For": "203.0.113.9, " + GOOD_IP}))
    check(code == 200 and r.get("acted") is True,
          "a proxy's own last hop from a provider IP is accepted")
    check(srv.RAIL.cycle.deals[deal["reference"]]["state"] == "DEPOSITED",
          "and the deal moves to DEPOSITED")

    # -- the documented local-demo mode -------------------------------------
    deal = fresh(require_ip=False)
    code, r = post(srv.BREET_PATH, event(), H)
    check(code == 200 and r.get("acted") is True,
          "with the allowlist off, a local delivery is accepted")
    code, r = post(srv.BREET_PATH, event(id="evt_wire_2"),
                   {"x-webhook-secret": "wrong", "Content-Type": "application/json"})
    check(code == 401, "and the header secret is still required")

    # -- shapes ------------------------------------------------------------
    deal = fresh(require_ip=False)
    code, r = post(srv.BREET_PATH, b"{not json", H)
    check(code == 200 and r.get("acted") is False,
          "a body that does not parse is refused, not 500")
    code, r = post(srv.BREET_PATH, b"{not json",
                   {"x-webhook-secret": "wrong", "Content-Type": "application/json"})
    check(code == 401, "and an unauthenticated caller learns nothing about the shape")

    huge = b'{"pad":"' + b"A" * 300_000 + b'"}'
    code, r = post(srv.BREET_PATH, huge, H)
    check(code == 413, "an oversized body is refused at the server edge")

    # -- the other routes are untouched -------------------------------------
    code, r = post("/api/wa", json.dumps({"from": "sim", "text": "hi"}).encode(),
                   {"Content-Type": "application/json"})
    check(code == 200, "the ordinary JSON routes still work")

    # -- unconfigured means absent ------------------------------------------
    srv.BREET = None
    code, r = post(srv.BREET_PATH, event(id="evt_wire_3"), H)
    check(code == 404, "with no secret configured the webhook path is 404")
finally:
    httpd.shutdown()
    httpd.server_close()

print()
if fails:
    print("BREET WIRE SMOKE FAILED - %d:" % len(fails))
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("the deposit webhook is reachable, and its allowlist survives a proxy.")
