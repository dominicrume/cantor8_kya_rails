#!/usr/bin/env python3
"""tools/anchor_timestamp.py: an outside timestamp that a stranger can check.

Offline. The one REAL reply is stored in the repo: DigiCert's signed answer for
anchors/2026-11-26/ANCHOR.disclosure.json. Everything that needs a service uses a
MOCKED local one, which says what the test needs it to say.

Checking a signature needs the `openssl` program. Where it is missing the
openssl tests print SKIP, and the run says so at the end: a check that could not
run is never reported as one that passed.

    python3 tests/anchor_timestamp_smoke.py
"""
import contextlib
import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location("anchor_timestamp", os.path.join(ROOT, "tools", "anchor_timestamp.py"))
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)

REAL = os.path.join(ROOT, "anchors", "2026-11-26", "ANCHOR.disclosure.json")
FAILS, SKIPS = [], []


def check(ok, label):
    print("  %s %s" % ("PASS" if ok else "FAIL", label))
    if not ok:
        FAILS.append(label)


def skip(label):
    print("  SKIP %s" % label)
    SKIPS.append(label)


def quiet(fn, *args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = fn(*args)
    return rc, out.getvalue()


openssl = at.find_openssl()
real_reply = open(REAL + ".tsr", "rb").read()

print("the request is built by hand and openssl agrees with it")
digest = bytes.fromhex("11" * 32)
if openssl:
    ref = subprocess.run([openssl, "ts", "-query", "-digest", digest.hex(), "-sha256", "-no_nonce", "-cert"],
                         capture_output=True).stdout
    check(at.build_request(digest) == ref, "byte for byte the same as openssl's own request (no nonce)")
    with tempfile.TemporaryDirectory() as tmp:
        q = os.path.join(tmp, "q.tsq")
        open(q, "wb").write(at.build_request(digest, 0x1234ABCD))
        shown = subprocess.run([openssl, "ts", "-query", "-in", q, "-text"], capture_output=True, text=True)
        text = shown.stdout + shown.stderr
        block = text.split("Message data:")[-1].split("Policy OID")[0]
        shown_bytes = re.findall(r"(?<![0-9A-Za-z])[0-9a-f]{2}(?![0-9A-Za-z])", block)
        check("".join(shown_bytes) == digest.hex() and "Nonce: 0x1234ABCD" in text
              and "Certificate required: yes" in text,
              "openssl reads our request back: our digest, our nonce, and it asks for the signer's certificate")
else:
    skip("request compared with openssl's (no openssl with `ts`)")
try:
    at.build_request(b"short")
    check(False, "a digest that is not 32 bytes is refused")
except ValueError:
    check(True, "a digest that is not 32 bytes is refused")

print("the status of a reply")
check(at.status_of(real_reply) == 0, "the stored real reply says granted (0)")
refused = at._tlv(0x30, at._tlv(0x30, b"\x02\x01\x02"))
check(at.status_of(refused) == 2, "a hand-made refusal reads as 2")
for label, junk in (("nothing", b""), ("text", b"<html>no</html>"), ("a cut-off reply", real_reply[:12])):
    try:
        at.status_of(junk)
        check(False, "%s is rejected, not read as granted" % label)
    except ValueError:
        check(True, "%s is rejected, not read as granted" % label)

print("checking the REAL reply, with controls that must fail")
if openssl and at.find_cafile():
    state, detail = at.verify_reply(REAL, REAL + ".tsr")
    check(state == at.VERIFIED, "the stored real reply verifies against the real file (%s)" % detail)
    with tempfile.TemporaryDirectory() as tmp:
        edited = os.path.join(tmp, "edited.json")
        data = bytearray(open(REAL, "rb").read())
        data[40] ^= 1
        open(edited, "wb").write(bytes(data))
        state, _ = at.verify_reply(edited, REAL + ".tsr")
        check(state == at.FAILED, "CONTROL: one flipped bit in the file and it no longer verifies")
        broken = os.path.join(tmp, "broken.tsr")
        raw = bytearray(real_reply)
        raw[len(raw) - 40] ^= 1
        open(broken, "wb").write(bytes(raw))
        state, _ = at.verify_reply(REAL, broken)
        check(state == at.FAILED, "CONTROL: one flipped bit in the reply and it no longer verifies")
else:
    skip("real reply verification (no openssl with `ts`, or no certificate bundle)")

print("the three answers: a check that cannot run never says VERIFIED")
saved = at.find_openssl
at.find_openssl = lambda: None
state, _ = at.verify_reply(REAL, REAL + ".tsr")
rc, out = quiet(at.cmd_verify, REAL, None)
at.find_openssl = saved
check(state == at.CANNOT_CHECK and rc == 2 and "VERIFIED" not in out.replace("CANNOT CHECK", ""),
      "with no openssl the answer is CANNOT CHECK, exit 2, never VERIFIED")


class Mock(BaseHTTPRequestHandler):
    """MOCKED timestamp service. `reply` is what it answers; `seen` is what it was sent."""
    reply = b""
    seen = []

    def log_message(self, format, *args):
        return

    def do_POST(self):
        Mock.seen.append(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        self.send_response(200)
        self.send_header("Content-Length", str(len(Mock.reply)))
        self.end_headers()
        self.wfile.write(Mock.reply)


server = HTTPServer(("127.0.0.1", 0), Mock)
threading.Thread(target=server.serve_forever, daemon=True).start()
URL = "http://127.0.0.1:%d/" % server.server_address[1]

print("stamping, against a MOCKED service")
with tempfile.TemporaryDirectory() as tmp:
    marker = b"SECRET-FILE-CONTENT-4f9c1e"
    mine = os.path.join(tmp, "mine.json")
    open(mine, "wb").write(b'{"x": "' + marker + b'"}')

    def nothing_saved():
        return not os.path.exists(mine + ".tsr") and not os.path.exists(mine + ".tsq")

    for label, reply, words in (("a refusal (status 2)", refused, "refused the request (status 2)"),
                                ("garbage", b"<html>oops</html>", "NOT TIMESTAMPED"),
                                ("an empty reply", b"", "NOT TIMESTAMPED")):
        Mock.reply, Mock.seen = reply, []
        rc, out = quiet(at.cmd_stamp, mine, URL, None)
        check(rc == 1 and words in out and nothing_saved(), "%s: reported (%s), nothing saved" % (label, words))
    check(all(marker not in body for body in Mock.seen) or not Mock.seen,
          "the file's content never left: only a hash was sent")
    Mock.reply, Mock.seen = real_reply, []
    rc, out = quiet(at.cmd_stamp, mine, URL, None)
    if openssl and at.find_cafile():
        check(rc == 1 and "did not verify" in out and nothing_saved(),
              "CONTROL: a genuine reply that belongs to a DIFFERENT file is refused, nothing saved")
    else:
        skip("a genuine reply for a different file is refused (no openssl)")
    check(len(Mock.seen) == 1 and marker not in Mock.seen[0] and len(Mock.seen[0]) < 100,
          "the request that was sent is a short hash request (%d bytes), not the file" % len(Mock.seen[0]))
server.shutdown()
rc, out = quiet(at.cmd_stamp, mine if os.path.exists(mine) else REAL, "http://127.0.0.1:1/", None)
check(rc == 1 and "NOT TIMESTAMPED" in out, "an unreachable service is reported, not hidden")
rc, out = quiet(at.cmd_stamp, REAL, "ftp://example.org/", None)
check(rc == 1 and "must start with http" in out, "a service URL that is not http or https is refused")
for stray in (REAL + ".tsq.tmp",):
    shutil.rmtree(stray, ignore_errors=True)

print()
if FAILS:
    print("FAILED: %d" % len(FAILS))
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
if SKIPS:
    print("ALL THAT COULD RUN PASSED. %d check(s) could NOT run and are not counted as passed:" % len(SKIPS))
    for s in SKIPS:
        print("  -", s)
    sys.exit(0)
print("ALL GREEN")
