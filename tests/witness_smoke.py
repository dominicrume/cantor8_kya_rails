#!/usr/bin/env python3
"""A witness catches what a pin on the same disk cannot: whoever can delete the
chain can delete the pins. A witness is a separate process holding a key the
agent never has (SPEC 6g).

Built failure first: with no witness, delete-and-restart is accepted. Then each
attack is thrown at a REAL witness server on a local port: delete and restart,
replace history with another valid chain, forge or edit a witnessed pin, take
the witness away, tamper with the witness's own log, and feed the server bad
input. Last, the key is hunted for in every response, with a positive control
proving the hunt can find one.

What this does NOT show: a transparency log (the MAC is symmetric, so only
someone holding the key can check it), a key the agent cannot reach on a single
machine without a separate user, or anything about a network witness beyond
localhost. Python only, no conformance vector.

Run: python3 tests/witness_smoke.py
"""
import http.client
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pkg", "src"))
from knowyouragenticai_receipts import Chain, head_pin, mcp, witness  # noqa: E402

FAILS = []
SEEN = []          # every response body we ever received, hunted for the key at the end


def check(ok, label):
    print("  %s %s" % ("PASS" if ok else "FAIL", label))
    if not ok:
        FAILS.append(label)


def text_of(result):
    t = result["content"][0]["text"]
    SEEN.append(t)
    return json.loads(t)


def stamp(save, url=None, payee="acme"):
    mcp.SESSION_CHAIN = Chain()          # a fresh process each time
    args = {"what": "pay", "amount": "1.00", "currency": "USD", "payee": payee,
            "rule": "cap", "outcome": "ACCEPTED", "save_path": save}
    if url:
        args["witness_url"] = url
    r = mcp.handle_stamp(args)
    return not r.get("isError"), text_of(r)


def verify(save, url, key_file=None):
    args = {"file_path": save, "witness_url": url}
    if key_file:
        args["witness_key_file"] = key_file
    return text_of(mcp.handle_verify(args))


def count(path):
    if not os.path.exists(path):
        return 0
    with open(path) as f:
        return len(json.load(f))


def log_lines(path):
    with open(path) as f:
        return [ln for ln in f.read().splitlines() if ln.strip()]


def raw(port, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(method, path, body=body, headers=headers or {})
    resp = conn.getresponse()
    data = resp.read().decode()
    SEEN.append(data)
    conn.close()
    return resp.status, data


tmp = tempfile.mkdtemp(prefix="witness_smoke_")
key_path = os.path.join(tmp, "witness.key")
log_path = os.path.join(tmp, "witness.log")
save = os.path.join(tmp, "chain", "receipts.json")
os.makedirs(os.path.dirname(save))

print("the key file")
witness.make_key(key_path)
check(stat.S_IMODE(os.stat(key_path).st_mode) == 0o600, "a new key file is mode 0600")
try:
    witness.make_key(key_path)
    check(False, "make_key refuses to overwrite a key")
except FileExistsError:
    check(True, "make_key refuses to overwrite a key")
short = os.path.join(tmp, "short.key")
with open(short, "wb") as f:
    f.write(b"abc")
try:
    witness.load_key(short)
    check(False, "a key shorter than 16 bytes is rejected")
except ValueError:
    check(True, "a key shorter than 16 bytes is rejected")
KEY = witness.load_key(key_path)
NEEDLE_GUARD = open(key_path).read().strip()

server = witness.make_server("127.0.0.1", 0, KEY, log_path)
server.daemon_threads = True
PORT = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()
URL = "http://127.0.0.1:%d" % PORT

print("the failure, built first: no witness, delete and restart is accepted")
ctl = os.path.join(tmp, "control", "receipts.json")
os.makedirs(os.path.dirname(ctl))
for _ in range(3):
    stamp(ctl)
os.remove(ctl)
ok, _ = stamp(ctl)
check(ok and count(ctl) == 1, "control: with no witness the restarted chain is accepted (1 receipt)")

print("a witnessed chain, normal use")
for i in range(3):
    ok, body = stamp(save, URL)
    check(ok, "stamp %d with a witness is accepted" % (i + 1))
check(len(log_lines(log_path)) == 3, "the witness recorded one pin per write (3)")
pins, err = witness.fetch_pins(URL)
check(err is None and [p["n"] for p in pins] == [1, 2, 3], "the witness lists pins n=1,2,3")
v = verify(save, URL, key_path)
wc = v["witness_check"]
check(wc["matched"] and wc["macs_checked"] and wc["pins"] == 3, "verify with the key: matched, MACs checked")
v = verify(save, URL)
check(v["witness_check"]["matched"] and not v["witness_check"]["macs_checked"],
      "verify without the key matches but says the MACs were NOT checked")
check("assurance" not in json.dumps(v).replace("does not raise the assurance level", ""),
      "verify does not claim an assurance level from a witness")
check(text_of(mcp.handle_verify({"file_path": save}))["witness_check"] is None,
      "no witness_url, no witness_check")
good_chain = open(save, "rb").read()
good_lines = log_lines(log_path)

print("attack 1: delete the chain and start again")
os.remove(save)
ok, body = stamp(save, URL)
check(not ok and "truncated or restarted" in body["error"], "refused: truncated or restarted")
check(not os.path.exists(save), "refused BEFORE writing: no chain file was created")
check(log_lines(log_path) == good_lines, "the witness log did not change")

print("attack 2: replace history with another valid chain")
mallory = Chain()
for _ in range(3):
    mallory.stamp("pay", "1.00", "USD", "mallory", "cap", "ACCEPTED")
with open(save, "w") as f:
    json.dump(mallory.receipts, f)
ok, body = stamp(save, URL)
check(not ok and "replaced" in body["error"], "refused: replaced")
check(count(save) == 3, "nothing was appended to the replaced chain")
msg = witness.post_pin(URL, head_pin(mallory.receipts))
check(msg is not None and "409" in msg and "different seal" in msg,
      "the witness itself refuses the regenerated head (409)")
check(log_lines(log_path) == good_lines, "the witness log still did not change")
v = verify(save, URL, key_path)
check(not v["witness_check"]["matched"] and "replaced" in v["witness_check"]["reason"],
      "verify reports the replaced chain")
with open(save, "wb") as f:
    f.write(good_chain)

print("attack 3: forge or edit a witnessed pin (needs the key to catch)")
real = witness.fetch_pins(URL)[0]
real_chain = json.loads(good_chain)
ok_real, _ = witness.check_witnessed(real_chain, real, KEY)
check(ok_real, "control: the real pins pass for the real chain with the right key")
forged = [dict(head_pin(mallory.receipts), t=1, mac="0" * 64)]
ok_f, why = witness.check_witnessed(mallory.receipts, forged, KEY)
check(not ok_f and "MAC" in why, "a pin with an invented MAC is rejected")
edited = [dict(real[0], t=real[0]["t"] + 1)] + real[1:]
ok_e, why = witness.check_witnessed(real_chain, edited, KEY)
check(not ok_e and "MAC" in why, "editing only the witness's timestamp breaks the MAC")
moved = [dict(real[0], seal=mallory.receipts[0]["seal"])] + real[1:]
ok_m, why = witness.check_witnessed(real_chain, moved, KEY)
check(not ok_m and "MAC" in why, "swapping in another seal under a real MAC is rejected")
other_key = os.urandom(32).hex().encode()
ok_k, why = witness.check_witnessed(real_chain, real, other_key)
check(not ok_k and "MAC" in why, "the right pins under the wrong key are rejected")
malformed = [{"n": True, "seal": "x", "t": 1, "mac": "m"}, "text", None, {"n": 1}]
check(all(not witness.check_witnessed(real_chain, [m], KEY)[0] for m in malformed),
      "malformed witnessed pins fail instead of raising")

print("attack 4: tamper with the witness's own log")
with open(log_path) as f:
    text = f.read()
first = json.loads(text.splitlines()[0])
with open(log_path, "w") as f:
    f.write(text.replace(first["seal"], "f" * 64, 1))
ok, body = stamp(save, URL)
check(not ok and "Nothing was written" in body["error"], "a damaged witness log stops the writer")
check(count(save) == 3, "and nothing was written")
body9 = json.dumps({"n": 9, "seal": "a" * 64})
status, _ = raw(PORT, "POST", "/pins", body9, {"Content-Length": str(len(body9))})
check(status == 500, "the witness does not record on top of a log it cannot trust")
with open(log_path, "w") as f:
    f.write(text)

print("attack 5: take the witness away")
dead = socket.socket()
dead.bind(("127.0.0.1", 0))
dead_port = dead.getsockname()[1]
dead.close()
DEAD = "http://127.0.0.1:%d" % dead_port
ok, body = stamp(save, DEAD)
check(not ok and "could not be reached" in body["error"], "stamp fails closed when the witness is unreachable")
check(count(save) == 3, "nothing was written")
v = verify(save, DEAD)
check(not v["witness_check"]["matched"], "verify does not report a match without a witness")
ok, body = stamp(save, "file:///etc/hostname")
check(not ok and "http" in body["error"], "a non-http witness URL is refused")

print("the witness refuses bad input")
GOOD = {"n": 7, "seal": "b" * 64}
st1, b1 = raw(PORT, "POST", "/pins", json.dumps(GOOD), {"Content-Length": str(len(json.dumps(GOOD)))})
st2, b2 = raw(PORT, "POST", "/pins", json.dumps(GOOD), {"Content-Length": str(len(json.dumps(GOOD)))})
check(st1 == 201 and st2 == 200 and json.loads(b1) == json.loads(b2), "a repeat of a recorded pin returns the same entry")
conflict = {"n": 7, "seal": "c" * 64}
st, b = raw(PORT, "POST", "/pins", json.dumps(conflict), {"Content-Length": str(len(json.dumps(conflict)))})
check(st == 409, "a different seal at a recorded count is a 409")
bad_bodies = [
    {"n": True, "seal": "x"}, {"n": -1, "seal": "x"}, {"n": "1", "seal": "x"},
    {"n": 1}, {"n": 1, "seal": ""}, {"n": 1, "seal": "z" * 129}, [1, 2], "text", None,
]
for b in bad_bodies:
    body = json.dumps(b)
    st, _ = raw(PORT, "POST", "/pins", body, {"Content-Length": str(len(body))})
    check(st == 400, "400 for %s" % body[:40])
st, _ = raw(PORT, "POST", "/pins", b"{not json", {"Content-Length": "9"})
check(st == 400, "400 for a body that is not JSON")
st, _ = raw(PORT, "POST", "/pins", b"x", {"Content-Length": str(witness.MAX_BODY + 1)})
check(st == 400, "400 for a body over the size cap")
st, _ = raw(PORT, "GET", "/elsewhere")
check(st == 404, "404 for any other path")
check(len(log_lines(log_path)) == len(good_lines) + 1, "bad input recorded nothing (only the one valid pin was added)")

print("a witness that lies, or that stops answering writes (a stub server, not ours)")


def stub(pins, post_status):
    class H(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def _send(self, code, obj):
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._send(200, {"pins": pins})

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            self._send(post_status, {"error": "stub refuses"})

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]


srv, surl = stub([], 500)
late = os.path.join(tmp, "late", "receipts.json")
os.makedirs(os.path.dirname(late))
ok, body = stamp(late, surl)
check(not ok and body["error"].startswith("Stamped and saved, but NOT witnessed"),
      "a witness that refuses the write after the save is reported as NOT witnessed")
check(count(late) == 1, "and the report is honest that the receipt was saved")
srv.shutdown()

fake_pins = [dict(head_pin(mallory.receipts[:i + 1]), t=1, mac="0" * 64) for i in range(3)]
with open(save, "w") as f:
    json.dump(mallory.receipts, f)
srv, furl = stub(fake_pins, 201)
v = verify(save, furl, key_path)["witness_check"]
check(not v["matched"] and v["macs_checked"] and "MAC" in v["reason"],
      "verify through the tool, with the key: a fake witness's pins are caught by their MACs")
v = verify(save, furl)["witness_check"]
check(v["matched"] and not v["macs_checked"],
      "LIMIT, shown on purpose: without the key a fake witness is believed, and the result says MACs were not checked")
srv.shutdown()
with open(save, "wb") as f:
    f.write(good_chain)

print("the real command line, as its own process")


def cli_first_line():
    """The line `serve` prints must reach a pipe at once: output to a file is block
    buffered, and an operator who cannot see the port cannot use the witness."""
    env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "pkg", "src"))
    proc = subprocess.Popen(
        [sys.executable, "-B", "-m", "knowyouragenticai_receipts.witness", "serve",
         "--key-file", key_path, "--log", os.path.join(tmp, "cli.log"), "--port", "0"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    got = []
    reader = threading.Thread(target=lambda: got.append(proc.stdout.readline()), daemon=True)
    reader.start()
    reader.join(8)
    proc.kill()
    proc.wait()
    return got[0] if got else ""


line = cli_first_line()
check("witness listening on http://127.0.0.1:" in line, "serve prints its address immediately, not at exit")
check(NEEDLE_GUARD not in line, "and the first line does not show the key")

print("the key is nowhere in anything the witness or the tool said")
needle = open(key_path).read().strip()
blob = "\n".join(SEEN)
check(needle not in blob, "the key does not appear in any response body")
check(needle in "\n".join(SEEN + ["planted " + needle]),
      "positive control: the hunt would have found a planted key")

server.shutdown()
shutil.rmtree(tmp, ignore_errors=True)
if FAILS:
    print("\nFAILED: %d" % len(FAILS))
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("\nALL GREEN")
