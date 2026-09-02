#!/usr/bin/env python3
"""Prove the Meta webhook is actually reachable over a real socket.

meta_smoke.py attacks the adapter. This attacks the SERVER: the route, the
raw-body handling, and the fact that the endpoint does not exist at all when
it is not fully configured. Those live in server.py, not in the adapter, and
a previous version of this repository shipped a server whose methods had been
edited into the wrong place -- with every adapter test still green.

Run: python3 tests/meta_wire_smoke.py
"""
import hashlib, hmac, importlib.util, json, os, socketserver, sys, threading
import urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET = "FIXTURE-" + hashlib.sha256(b"meta_wire_secret").hexdigest()[:24]
VERIFY = "FIXTURE-" + hashlib.sha256(b"meta_wire_verify").hexdigest()[:24]
PNID = "100000000000001"

# Set before importing: build_meta reads these at startup, which is the
# behaviour being tested.
os.environ["KYA_META_APP_SECRET"] = SECRET
os.environ["KYA_META_VERIFY_TOKEN"] = VERIFY
os.environ["KYA_META_PHONE_ID"] = PNID

for p in ("step-7-providers", "step-6-whatsapp", "step-5-operator", "step-2-agent"):
    sys.path.insert(0, os.path.join(ROOT, p))
spec = importlib.util.spec_from_file_location(
    "srv", os.path.join(ROOT, "step-5-operator", "server.py"))
srv = importlib.util.module_from_spec(spec); spec.loader.exec_module(srv)

fails = []


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


def body(text="hi", wamid="wamid.WIRE1", ts=None):
    ts = srv.time.time() if ts is None else ts
    return json.dumps({
        "object": "whatsapp_business_account",
        "entry": [{"id": "W", "changes": [{"field": "messages", "value": {
            "metadata": {"phone_number_id": PNID},
            "messages": [{"from": "999000000001", "id": wamid,
                          "timestamp": str(int(ts)), "type": "text",
                          "text": {"body": text}}]}}]}]}).encode()


RESET = "reset"          # the server refused before reading, and closed on us


def request(method, path, data=None, headers=None):
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except urllib.error.URLError as e:
        if isinstance(getattr(e, "reason", None), ConnectionResetError):
            return RESET, b""
        raise


def sign(raw):
    return {"X-Hub-Signature-256": "sha256=" + hmac.new(
        SECRET.encode(), raw, hashlib.sha256).hexdigest(),
        "Content-Type": "application/json"}


print("KYA Rails - is the Meta webhook actually wired in?")

srv.RAIL = srv.Rail([])
srv.META = srv.build_meta(srv.RAIL)
check(srv.META is not None, "build_meta returns an adapter when all three vars are set")

socketserver.TCPServer.allow_reuse_address = True
httpd = socketserver.TCPServer(("127.0.0.1", 0), srv.Handler)
BASE = "http://127.0.0.1:%d" % httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()

try:
    # -- the verification handshake, over the wire ---------------------------
    code, out = request("GET", "%s?hub.mode=subscribe&hub.verify_token=%s"
                        "&hub.challenge=98765" % (srv.META_PATH, VERIFY))
    check((code, out) == (200, b"98765"), "the challenge comes back over HTTP")

    code, out = request("GET", "%s?hub.mode=subscribe&hub.verify_token=wrong"
                        "&hub.challenge=98765" % srv.META_PATH)
    check(code == 403 and out != b"98765", "a wrong verify token gets nothing echoed")

    # -- a real signed delivery ---------------------------------------------
    raw = body("hi")
    code, out = request("POST", srv.META_PATH, raw, sign(raw))
    check(code == 200, "a signed delivery is accepted over HTTP")
    check(json.loads(out).get("acted") is True, "and reaches the bot")
    check(len(srv.RAIL.transcript) == 2, "the transcript records the message and the reply")

    # The signature covers the bytes on the wire. If the server parsed and
    # re-serialised the body before verifying, this identical-meaning but
    # differently-spaced body would fail -- and a body signed elsewhere would
    # start passing.
    spaced = json.dumps(json.loads(body("hello", "wamid.WIRE2").decode()),
                        indent=2).encode()
    code, out = request("POST", srv.META_PATH, spaced, sign(spaced))
    check(code == 200 and json.loads(out).get("acted") is True,
          "the body is verified as sent, not as re-serialised by the server")

    # -- unsigned traffic ----------------------------------------------------
    before = len(srv.RAIL.transcript)
    raw = body("pay me", "wamid.WIRE3")
    code, out = request("POST", srv.META_PATH, raw,
                        {"Content-Type": "application/json"})
    check(code == 401, "an unsigned POST to the webhook is 401 over HTTP")
    check(len(srv.RAIL.transcript) == before, "and nothing reached the bot")

    code, out = request("POST", srv.META_PATH, raw,
                        {"X-Hub-Signature-256": "sha256=" + "0" * 64})
    check(code == 401, "a wrongly signed POST is 401 over HTTP")

    # -- an oversized body is refused without being read into memory ---------
    # The server reads Content-Length and answers 413 WITHOUT reading the body,
    # which is the correct thing to do with 300KB it has already decided to
    # refuse. It then closes, while the client is still writing -- so the
    # client sees either the 413 or a connection reset, depending on timing.
    # Both mean refused-before-reading. Asserting only on 413 made this test
    # fail roughly one run in ten; the flake was in the assertion, not the
    # server. What must hold either way is that nothing was acted on.
    huge = b'{"object":"whatsapp_business_account","pad":"' + b"A" * 300_000 + b'"}'
    before = len(srv.RAIL.transcript)
    code, out = request("POST", srv.META_PATH, huge, sign(huge))
    check(code in (413, RESET), "an oversized body is refused at the server edge")
    check(len(srv.RAIL.transcript) == before, "and nothing reached the bot")

    # -- the ordinary API is untouched --------------------------------------
    code, out = request("POST", "/api/wa", json.dumps({"from": "sim", "text": "hi"}).encode(),
                        {"Content-Type": "application/json"})
    check(code == 200, "the ordinary JSON routes still work")

    # -- and when it is not configured, the path does not exist -------------
    srv.META = None
    code, out = request("POST", srv.META_PATH, body("hi", "wamid.WIRE4"),
                        sign(body("hi", "wamid.WIRE4")))
    check(code == 404, "with no credentials configured the webhook path is 404")
    code, out = request("GET", "%s?hub.mode=subscribe&hub.verify_token=%s"
                        "&hub.challenge=1" % (srv.META_PATH, VERIFY))
    check(code != 200 or out != b"1", "and the verification handshake is not answered")
finally:
    httpd.shutdown()
    httpd.server_close()

print()
if fails:
    print("META WIRE SMOKE FAILED - %d:" % len(fails))
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("the webhook is reachable, signature-checked, and absent when unconfigured.")
