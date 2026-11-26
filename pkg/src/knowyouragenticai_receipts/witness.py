"""An off-box witness for pins (SPEC 6g).

A pin kept on the chain's own disk is only as safe as that disk. A witness is a
separate process, run as another user or on another machine, that records each
pin it is sent and answers with a MAC (a keyed hash) over the count, the seal
and its own clock. The agent that writes the chain never holds the key, so it
cannot forge a witnessed pin, and a chain regenerated from nothing cannot match
a head the witness already saw: the witness refuses a second, different seal at
a count it has already recorded.

WHAT THIS IS NOT. It is not a transparency log such as Sigstore Rekor, and it is
not signed in the public-key sense. The MAC is symmetric: whoever verifies a
witnessed pin must hold the same key as the witness, so a stranger cannot check
it and has to trust the witness operator. The standard library has no
asymmetric signing, and this package is standard library only, so a key the
agent cannot touch means a separate process or user, not an HSM. The witness
clock is the witness's own. Python only; no conformance vector.

Run a witness:
    python3 -m knowyouragenticai_receipts.witness make-key witness.key
    python3 -m knowyouragenticai_receipts.witness serve --key-file witness.key --log witness.log
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping, Sequence

from . import check_pins

MIN_KEY_BYTES = 16
MAX_BODY = 4096
MAX_SEAL = 128
TIMEOUT = 5.0
_PREFIX = b"knowyouragenticai-witness-1\n"


def _signed_bytes(entry: Mapping[str, Any]) -> bytes:
    core = {"n": entry["n"], "seal": entry["seal"], "t": entry["t"]}
    return _PREFIX + json.dumps(core, sort_keys=True, separators=(",", ":")).encode("utf-8")


def mac_entry(key: bytes, entry: Mapping[str, Any]) -> str:
    """The MAC the witness puts on one entry. Key bytes are never logged or printed."""
    return hmac.new(key, _signed_bytes(entry), hashlib.sha256).hexdigest()


def load_key(path: str) -> bytes:
    """Read a key file. Raises ValueError if it is too short to be a key."""
    with open(path, "rb") as f:
        key = f.read().strip()
    if len(key) < MIN_KEY_BYTES:
        raise ValueError("the key file is shorter than %d bytes" % MIN_KEY_BYTES)
    return key


def make_key(path: str) -> None:
    """Create a key file, mode 0600. Refuses to overwrite one that exists."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(os.urandom(32).hex().encode("ascii") + b"\n")


def _int_n(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _pin_ok(pin: Any) -> bool:
    if not isinstance(pin, Mapping) or not _int_n(pin.get("n")):
        return False
    seal = pin.get("seal")
    return isinstance(seal, str) and 0 < len(seal) <= MAX_SEAL


def _entry_ok(entry: Any) -> bool:
    return (_pin_ok(entry) and isinstance(entry.get("t"), int)
            and not isinstance(entry.get("t"), bool) and isinstance(entry.get("mac"), str))


def _mac_holds(key: bytes, entry: Mapping[str, Any]) -> bool:
    try:
        return hmac.compare_digest(entry["mac"].encode("ascii"), mac_entry(key, entry).encode("ascii"))
    except (UnicodeError, TypeError):
        return False


class Witness:
    """Records pins in an append-only log. Fails closed on a log it cannot trust."""

    def __init__(self, key: bytes, log_path: str) -> None:
        self._key = key
        self._log = log_path
        self._lock = threading.Lock()

    def entries(self) -> list[dict[str, Any]]:
        """Every recorded entry. ValueError if a line is damaged or fails its own MAC."""
        if not os.path.exists(self._log):
            return []
        out: list[dict[str, Any]] = []
        with open(self._log, "r", encoding="utf-8") as f:
            for number, line in enumerate(f, start=1):
                if line.strip():
                    out.append(self._parse(line, number))
        return out

    def _parse(self, line: str, number: int) -> dict[str, Any]:
        try:
            entry = json.loads(line)
        except ValueError:
            raise ValueError("witness log is unreadable at line %d" % number) from None
        if not _entry_ok(entry) or not _mac_holds(self._key, entry):
            raise ValueError("witness log line %d does not carry a valid MAC" % number)
        return dict(entry)

    def record(self, pin: Any) -> tuple[int, dict[str, Any]]:
        """(status, body). 201 recorded, 200 already recorded, 400 bad pin,
        409 a different seal was already recorded at this count, 500 log untrusted."""
        if not _pin_ok(pin):
            return 400, {"error": "a pin is {\"n\": count, \"seal\": final seal}"}
        with self._lock:
            try:
                existing = self.entries()
            except (OSError, ValueError) as e:
                return 500, {"error": str(e)}
            for seen in existing:
                if seen["n"] == pin["n"]:
                    if seen["seal"] == pin["seal"]:
                        return 200, seen
                    return 409, {"error": "conflict: this witness already recorded a different seal at n=%d" % pin["n"]}
            return 201, self._append(pin)

    def _append(self, pin: Mapping[str, Any]) -> dict[str, Any]:
        entry: dict[str, Any] = {"n": pin["n"], "seal": pin["seal"], "t": int(time.time())}
        entry["mac"] = mac_entry(self._key, entry)
        with open(self._log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return entry


def _handler_for(witness: Witness) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # silent
            return

        def _send(self, status: int, body: Any) -> None:
            data = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _read_pin(self) -> tuple[Any, str | None]:
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                return None, "a Content-Length is required"
            if length < 0 or length > MAX_BODY:
                return None, "the body must be at most %d bytes" % MAX_BODY
            try:
                return json.loads(self.rfile.read(length)), None
            except ValueError:
                return None, "the body is not JSON"

        def do_GET(self) -> None:
            if self.path != "/pins":
                self._send(404, {"error": "not found"})
                return
            try:
                self._send(200, {"pins": witness.entries()})
            except (OSError, ValueError) as e:
                self._send(500, {"error": str(e)})

        def do_POST(self) -> None:
            if self.path != "/pins":
                self._send(404, {"error": "not found"})
                return
            pin, err = self._read_pin()
            if err:
                self._send(400, {"error": err})
                return
            self._send(*witness.record(pin))

    return Handler


def make_server(host: str, port: int, key: bytes, log_path: str) -> ThreadingHTTPServer:
    """A witness server, not yet serving. Port 0 picks a free port."""
    return ThreadingHTTPServer((host, port), _handler_for(Witness(key, log_path)))


def _request(url: str, payload: Any | None) -> tuple[int, Any, str | None]:
    """(status, parsed body, transport error). Proxies are ignored on purpose."""
    if not url.startswith(("http://", "https://")):
        return 0, None, "the witness URL must start with http:// or https://"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(  # nosec B310 - scheme checked above
        url.rstrip("/") + "/pins", data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=TIMEOUT) as r:  # nosec B310
            return r.status, json.loads(r.read(MAX_BODY * 256)), None
    except urllib.error.HTTPError as e:
        return e.code, _json_or_none(e.read(MAX_BODY)), None
    except (OSError, ValueError) as e:
        return 0, None, "%s: %s" % (type(e).__name__, e)


def _json_or_none(raw: bytes) -> Any:
    try:
        return json.loads(raw)
    except ValueError:
        return None


def fetch_pins(url: str) -> tuple[list[Any] | None, str | None]:
    """The witness's recorded entries, or (None, why it could not be read)."""
    status, body, err = _request(url, None)
    if err:
        return None, "the witness could not be reached (%s)" % err
    if status != 200 or not isinstance(body, dict) or not isinstance(body.get("pins"), list):
        return None, "the witness answered %d with something that is not a pin list" % status
    return body["pins"], None


def post_pin(url: str, pin: Mapping[str, Any]) -> str | None:
    """None if the witness recorded the pin, else why it did not."""
    status, body, err = _request(url, dict(pin))
    if err:
        return "the witness could not be reached (%s)" % err
    if status in (200, 201):
        return None
    reason = body.get("error", "") if isinstance(body, dict) else ""
    return "the witness refused the pin (%d): %s" % (status, reason)


def _entry_problem(entry: Any, key: bytes) -> str:
    if not _entry_ok(entry):
        return "a witnessed pin is malformed: %r" % (entry,)
    if not _mac_holds(key, entry):
        return "a witnessed pin does not carry a valid MAC (forged, edited, or the wrong key)"
    return ""


def check_witnessed(receipts: Sequence[Any], witnessed: Sequence[Any],
                    key: bytes) -> tuple[bool, str]:
    """Like check_pins, but every pin must first carry a valid witness MAC.

    NEVER RAISES. Only a verifier that holds the key can run this.
    """
    for entry in witnessed:
        why = _entry_problem(entry, key)
        if why:
            return False, why
    return check_pins(receipts, [{"n": e["n"], "seal": e["seal"]} for e in witnessed])


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="witness", description=__doc__.split("\n")[0] if __doc__ else "")
    sub = ap.add_subparsers(dest="cmd", required=True)
    mk = sub.add_parser("make-key", help="create a key file (mode 0600); refuses to overwrite")
    mk.add_argument("path")
    sv = sub.add_parser("serve", help="run a witness")
    sv.add_argument("--key-file", required=True)
    sv.add_argument("--log", required=True)
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8787)
    args = ap.parse_args(argv)
    if args.cmd == "make-key":
        make_key(args.path)
        print("wrote a new key to %s (not shown). Give it to the verifier, never to the agent." % args.path)
        return 0
    server = make_server(args.host, args.port, load_key(args.key_file), args.log)
    print("witness listening on http://%s:%d, log %s" % (args.host, server.server_address[1], args.log), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
