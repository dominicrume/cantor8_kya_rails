#!/usr/bin/env python3
"""Get an outside timestamp for a file, and check one.

WHY. An anchor in our own GitHub repo can be rewritten by us. A timestamp from a
third party (RFC 3161) is a reply signed by THEIR key, with THEIR clock, saying
"this exact file existed no later than this time". We cannot backdate it or
rewrite it, and a stranger can check it without trusting us.

WHAT IT SENDS. Only the SHA-256 hash of the file. Never the file.

WHAT IT PROVES. The file existed no later than the time in the reply. It does not
say who wrote the file, that its content is true, or that nothing was deleted
from the chain before it. It is one more independent witness, not a signature
by us.

Standard library only. Building and sending the request, and reading the status,
need nothing else. CHECKING the signature needs the `openssl` program (the
standard library cannot verify a CMS signature). With no usable openssl the answer
is CANNOT CHECK, never VERIFIED.

    python3 tools/anchor_timestamp.py stamp  anchors/2026-11-26/ANCHOR.disclosure.json
    python3 tools/anchor_timestamp.py verify anchors/2026-11-26/ANCHOR.disclosure.json
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess  # nosec B404 - fixed argv, no shell
import sys
import tempfile
import urllib.error
import urllib.request

DEFAULT_TSA = "http://timestamp.digicert.com"   # plain http is fine: the reply is signed
SHA256_OID = bytes.fromhex("0609608648016503040201")
CA_CANDIDATES = ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt",
                 "/etc/pki/tls/certs/ca-bundle.crt")
OPENSSL_CANDIDATES = ("/usr/local/opt/openssl@3/bin/openssl", "/opt/homebrew/opt/openssl@3/bin/openssl")
VERIFIED, FAILED, CANNOT_CHECK = "VERIFIED", "FAILED", "CANNOT CHECK"


# ---------------------------------------------------------------- DER, just enough
def _tlv(tag: int, body: bytes) -> bytes:
    n = len(body)
    if n < 128:
        length = bytes([n])
    else:
        raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
        length = bytes([0x80 | len(raw)]) + raw
    return bytes([tag]) + length + body


def _integer(n: int) -> bytes:
    return _tlv(0x02, n.to_bytes((n.bit_length() + 8) // 8, "big"))


def build_request(digest: bytes, nonce: int | None = None) -> bytes:
    """An RFC 3161 TimeStampReq for a SHA-256 digest, asking for the signer's certificate."""
    if len(digest) != 32:
        raise ValueError("a SHA-256 digest is 32 bytes")
    imprint = _tlv(0x30, _tlv(0x30, SHA256_OID + b"\x05\x00") + _tlv(0x04, digest))
    body = b"\x02\x01\x01" + imprint
    if nonce is not None:
        body += _integer(nonce)
    return _tlv(0x30, body + b"\x01\x01\xff")


def _read(data: bytes, pos: int) -> tuple[int, bytes, int]:
    """(tag, body, next position) of the DER element at `pos`. ValueError if it does not fit."""
    if pos + 2 > len(data):
        raise ValueError("truncated")
    tag, first = data[pos], data[pos + 1]
    start = pos + 2
    length = first
    if first & 0x80:
        count = first & 0x7F
        if count == 0 or count > 4 or start + count > len(data):
            raise ValueError("bad length")
        length = int.from_bytes(data[start:start + count], "big")
        start += count
    if start + length > len(data):
        raise ValueError("truncated")
    return tag, data[start:start + length], start + length


def status_of(reply: bytes) -> int:
    """PKIStatus of a TimeStampResp: 0 granted, 1 granted with modifications, 2 or more refused."""
    tag, body, _ = _read(reply, 0)
    tag2, info, _ = _read(body, 0)
    tag3, status, _ = _read(info, 0)
    if (tag, tag2, tag3) != (0x30, 0x30, 0x02):
        raise ValueError("not a TimeStampResp")
    return int.from_bytes(status, "big")


# ---------------------------------------------------------------- the network
def post(tsa: str, request: bytes) -> bytes:
    """Send the request, return the reply bytes. Raises OSError or ValueError."""
    if not tsa.startswith(("http://", "https://")):
        raise ValueError("the timestamp service URL must start with http:// or https://")
    req = urllib.request.Request(  # nosec B310 - scheme checked above
        tsa, data=request, method="POST",
        headers={"Content-Type": "application/timestamp-query"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:  # nosec B310
            return bytes(r.read(1_000_000))
    except urllib.error.URLError as e:
        raise OSError("could not reach the timestamp service: %s" % e) from None


# ---------------------------------------------------------------- checking, via openssl
def _has_ts(program: str) -> bool:
    try:
        r = subprocess.run([program, "ts", "-help"], capture_output=True, text=True, timeout=10)  # nosec B603
    except (OSError, subprocess.SubprocessError):
        return False
    return "Usage: ts" in (r.stdout + r.stderr)


def find_openssl() -> str | None:
    """An openssl that has the `ts` command (macOS LibreSSL may not), or None."""
    for candidate in (os.environ.get("OPENSSL"), shutil.which("openssl"), *OPENSSL_CANDIDATES):
        if candidate and _has_ts(candidate):
            return candidate
    return None


def find_cafile() -> str | None:
    return next((c for c in CA_CANDIDATES if os.path.exists(c)), None)


def _run(argv: list[str]) -> tuple[int, str]:
    r = subprocess.run(argv, capture_output=True, text=True, timeout=60)  # nosec B603 - fixed argv
    return r.returncode, r.stdout + r.stderr


def gen_time(openssl: str, reply_path: str) -> str:
    _, out = _run([openssl, "ts", "-reply", "-in", reply_path, "-text"])
    found = re.search(r"Time stamp: (.+)", out)
    return found.group(1).strip() if found else "unknown"


def _signer_chain(openssl: str, reply_path: str, work: str) -> str | None:
    """The certificates the TSA put inside its own reply, as a PEM file, or None."""
    token, pem = os.path.join(work, "t.der"), os.path.join(work, "chain.pem")
    rc1, _ = _run([openssl, "ts", "-reply", "-in", reply_path, "-token_out", "-out", token])
    rc2, _ = _run([openssl, "pkcs7", "-inform", "DER", "-in", token, "-print_certs", "-out", pem])
    return pem if rc1 == 0 and rc2 == 0 and os.path.exists(pem) else None


def _prerequisites(cafile: str | None) -> tuple[str, str, str]:
    """(openssl, certificate bundle, "") or ("", "", why a check cannot run here)."""
    openssl, ca = find_openssl(), cafile or find_cafile()
    if not openssl:
        return "", "", "no openssl with the `ts` command was found; install OpenSSL 1.1 or newer"
    if not ca:
        return "", "", "no certificate bundle was found; pass --cafile"
    return openssl, ca, ""


def _verdict(rc: int, out: str, openssl: str, reply_path: str) -> tuple[str, str]:
    if rc == 0 and "Verification: OK" in out:
        return VERIFIED, "signed at %s" % gen_time(openssl, reply_path)
    why = [line for line in out.splitlines() if "error" in line.lower() or "FAILED" in line]
    return FAILED, (why[-1] if why else "openssl did not verify the reply")[:160]


def verify_reply(data_path: str, reply_path: str, query_path: str | None = None,
                 cafile: str | None = None) -> tuple[str, str]:
    """(VERIFIED | FAILED | CANNOT CHECK, detail). VERIFIED only if openssl said so."""
    openssl, ca, why_not = _prerequisites(cafile)
    if why_not:
        return CANNOT_CHECK, why_not
    with tempfile.TemporaryDirectory() as work:
        chain = _signer_chain(openssl, reply_path, work)
        what = ["-queryfile", query_path] if query_path else ["-data", data_path]
        argv = [openssl, "ts", "-verify", *what, "-in", reply_path, "-CAfile", ca]
        rc, out = _run(argv + (["-untrusted", chain] if chain else []))
        return _verdict(rc, out, openssl, reply_path)


# ---------------------------------------------------------------- the commands
def _sha256_file(path: str) -> bytes:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.digest()


def _write(path: str, data: bytes) -> None:
    with open(path, "wb") as f:
        f.write(data)


def fetch_reply(path: str, tsa: str) -> tuple[bytes, bytes, str | None]:
    """(request, reply, problem). A reply is returned only if the service said granted."""
    request = build_request(_sha256_file(path), int.from_bytes(os.urandom(8), "big") >> 1)
    try:
        reply = post(tsa, request)
        status = status_of(reply)
    except (OSError, ValueError) as e:
        return request, b"", str(e)
    if status not in (0, 1):
        return request, b"", "the timestamp service refused the request (status %d)" % status
    return request, reply, None


def cmd_stamp(path: str, tsa: str, cafile: str | None) -> int:
    request, reply, problem = fetch_reply(path, tsa)
    if problem:
        print("NOT TIMESTAMPED: " + problem)
        return 1
    with tempfile.TemporaryDirectory() as work:
        q, r = os.path.join(work, "q.tsq"), os.path.join(work, "r.tsr")
        _write(q, request)
        _write(r, reply)
        state, detail = verify_reply(path, r, query_path=q, cafile=cafile)
    if state == FAILED:
        print("NOT TIMESTAMPED: the reply did not verify against this file (%s). Nothing was saved." % detail)
        return 1
    _write(path + ".tsq", request)
    _write(path + ".tsr", reply)
    print("%s: %s" % (state, detail))
    print("saved %s.tsr and %s.tsq" % (path, path))
    if state == CANNOT_CHECK:
        print("The reply is saved but UNVERIFIED on this machine. Run `verify` where openssl is installed.")
    print("Anyone can check it with: python3 tools/anchor_timestamp.py verify %s" % path)
    return 0


def cmd_verify(path: str, cafile: str | None) -> int:
    reply = path + ".tsr"
    if not os.path.exists(reply):
        print("%s: there is no %s" % (CANNOT_CHECK, reply))
        return 2
    state, detail = verify_reply(path, reply, cafile=cafile)
    print("%s: %s" % (state, detail))
    if state == VERIFIED:
        print("This proves the file existed no later than that time, by the timestamp service's own clock and key.")
        print("It does not say who wrote the file or that its content is true.")
    return {VERIFIED: 0, FAILED: 1}.get(state, 2)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="anchor_timestamp", description=(__doc__ or "").split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("stamp", help="get a timestamp for a file (sends only its hash)")
    st.add_argument("file")
    st.add_argument("--tsa", default=DEFAULT_TSA)
    vf = sub.add_parser("verify", help="check <file>.tsr against <file>")
    vf.add_argument("file")
    for p in (st, vf):
        p.add_argument("--cafile")
    args = ap.parse_args(argv)
    if not os.path.isfile(args.file):
        print("no such file: %s" % args.file)
        return 2
    if args.cmd == "stamp":
        return cmd_stamp(args.file, args.tsa, args.cafile)
    return cmd_verify(args.file, args.cafile)


if __name__ == "__main__":
    sys.exit(main())
