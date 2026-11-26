#!/usr/bin/env python3
"""Adversarial and performance tests for the receipts MCP server, over stdio.

Each test attacks `python3 -m knowyouragenticai_receipts mcp` the way a hostile
or merely broken agent could, and records PASS or FAIL. PASS means the server
held (stayed alive, stayed inside the workspace, stayed bounded). FAIL means the
attack worked. This suite is expected to exit nonzero until the servers are
hardened: a red line is a finding, not a harness fault.

Stdlib only. No network beyond 127.0.0.1 listeners this file starts itself and
ONE connection attempt to 169.254.169.254 (C4, a GET that cannot reach a pin
list, so nothing is ever written). Everything destructive happens in temp dirs.
The witness in C is MOCKED: a local stub this file starts, not a real witness.
Fake "key" content is the string MOCKED-FAKE-KEY-*, never real material.

Run:   python3 tests/mcp_adversarial_smoke.py
       python3 tests/mcp_adversarial_smoke.py --tree /path/to/tree [--json out.json]
The tree is read, never written (PYTHONDONTWRITEBYTECODE is set everywhere).
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import random
import re
import shutil
import signal
import socket
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ENV_MARKER = "ENVMARKER-7f3a9c1e"
KEY_MARKER = "MOCKED-FAKE-KEY-5b1d0e77c2a94f"
LEAK_MARKER = "MOCKED-LEAK-MARKER-31337"
NOREPLY = "NOREPLY"
AUTO = object()

RESULTS: list[dict] = []
METRICS: dict = {}
LOCK = threading.Lock()
kr = None  # the package under test, imported in main() from --tree


# ---------------------------------------------------------------- reporting
def scrub(s) -> str:
    """Truncate to 300 chars and hide anything that looks like a key or seal."""
    s = str(s)
    s = re.sub(r"[0-9a-fA-F]{32,}", "<HEX>", s)
    s = s.replace(KEY_MARKER, "<FAKE-KEY>")
    s = s.replace("\n", " ")
    return s if len(s) <= 300 else s[:297] + "..."


def rec(id_, cat, title, ok, trigger, observed, sev="", status=None):
    status = status or ("PASS" if ok else "FAIL")
    row = dict(id=id_, cat=cat, title=title, status=status, sev=sev if status == "FAIL" else "",
               trigger=scrub(trigger), observed=scrub(observed))
    with LOCK:
        RESULTS.append(row)
        print("  %-4s %-5s %s%s" % (status, id_, title, ("  [%s]" % sev) if row["sev"] else ""), flush=True)


# ------------------------------------------------------------------ context
class Ctx:
    def __init__(self, tree):
        self.tree = tree
        self.src = os.path.join(tree, "pkg", "src")
        self.root = tempfile.mkdtemp(prefix="kya-adv-")
        self.home = os.path.join(self.root, "home")
        os.makedirs(self.home)
        self._n = 0
        self.has_witness = False

    def new_dir(self, name="d"):
        with LOCK:
            self._n += 1
            n = self._n
        d = os.path.join(self.root, "%s-%d" % (name, n))
        os.makedirs(d)
        return d

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


# ------------------------------------------------------------------- server
class Server:
    """One server process, spoken to over stdio the way an MCP client would."""

    def __init__(self, ctx, cwd, extra_env=None):
        env = {k: v for k, v in os.environ.items() if not k.startswith("KYA")}
        env.update(extra_env or {})
        env.update(PYTHONPATH=ctx.src, PYTHONDONTWRITEBYTECODE="1", HOME=ctx.home,
                   KYA_ENV_MARKER=ENV_MARKER)
        self.t0 = time.perf_counter()
        self.p = subprocess.Popen(
            [sys.executable, "-m", "knowyouragenticai_receipts", "mcp"], cwd=cwd, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.q: queue.Queue = queue.Queue()
        self.err = bytearray()
        self.mid = 100
        threading.Thread(target=self._rd, daemon=True).start()
        threading.Thread(target=self._rde, daemon=True).start()

    def _rd(self):
        try:
            for line in iter(self.p.stdout.readline, b""):
                self.q.put(line)
        except Exception:
            pass
        self.q.put(None)

    def _rde(self):
        try:
            while True:
                b = self.p.stderr.read1(65536)
                if not b:
                    return
                if len(self.err) < 200000:
                    self.err += b
        except Exception:
            pass

    def send(self, raw: bytes, threaded=False):
        def w():
            try:
                self.p.stdin.write(raw)
                self.p.stdin.flush()
            except Exception:
                pass
        if threaded:
            threading.Thread(target=w, daemon=True).start()
        else:
            w()

    def close_stdin(self):
        try:
            self.p.stdin.close()
        except Exception:
            pass

    def recv(self, timeout=10):
        try:
            return self.q.get(timeout=timeout)
        except queue.Empty:
            return NOREPLY

    def req(self, method, params=None, timeout=10, id_=AUTO):
        self.mid += 1
        id_ = self.mid if id_ is AUTO else id_
        msg = {"jsonrpc": "2.0", "id": id_, "method": method}
        if params is not None:
            msg["params"] = params
        self.send(json.dumps(msg).encode() + b"\n")
        line = self.recv(timeout)
        if line is NOREPLY or line is None:
            return line
        try:
            return json.loads(line)
        except ValueError:
            return line

    def tool(self, name, args, timeout=20):
        """(response, text, isError). text is None when there is no tool result."""
        r = self.req("tools/call", {"name": name, "arguments": args}, timeout)
        try:
            res = r["result"]
            return r, res["content"][0]["text"], bool(res.get("isError"))
        except Exception:
            return r, None, True

    def alive(self, timeout=5):
        if self.p.poll() is not None:
            return False
        r = self.req("ping", timeout=timeout)
        return isinstance(r, dict) and r.get("result") == {}

    def initialize(self):
        return self.req("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                       "clientInfo": {"name": "adv", "version": "0"}})

    def stderr_last(self):
        lines = [l for l in self.err.decode("utf8", "replace").splitlines() if l.strip()]
        return lines[-1] if lines else ""

    def rss_mb(self):
        out = subprocess.run(["ps", "-o", "rss=", "-p", str(self.p.pid)],
                             capture_output=True, text=True).stdout.strip()
        return int(out) / 1024 if out.isdigit() else 0.0

    def kill(self):
        try:
            self.p.kill()
            self.p.wait(timeout=5)
        except Exception:
            pass

    def stop(self):
        self.close_stdin()
        try:
            self.p.wait(timeout=3)
        except Exception:
            self.kill()


def stamp_args(**kw):
    a = dict(what="adv", amount="1.00", currency="USD", payee="acme", rule="r1", outcome="ACCEPTED")
    a.update(kw)
    return a


def mk_chain(path, n):
    c = kr.Chain()
    for i in range(n):
        c.stamp(what="w%d" % i, amount="1", currency="USD", payee="p", rule="r", outcome="ACCEPTED")
    c.save(path)
    return c


def text_of(r):
    try:
        return r["result"]["content"][0]["text"]
    except Exception:
        return str(r)


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100.0 * (len(xs) - 1))))]


TESTS = []


def test(group="par"):
    def deco(fn):
        TESTS.append((group, fn))
        return fn
    return deco


# ============================================================ A. framing
def a_case(ctx, id_, title, raw, trigger, sev, *, timeout=10, threaded=False, eof=False, want=None, env=None):
    """Send raw bytes, then ask: is the server still there?  want(reply)->str|None is an extra check."""
    s = Server(ctx, ctx.new_dir(id_), env)
    try:
        s.send(raw, threaded=threaded)
        if eof:
            s.close_stdin()
        first = s.recv(timeout)
        if eof:
            try:
                s.p.wait(timeout=5)
            except Exception:
                pass
        alive = s.p.poll() is None and (s.alive() if not eof else False)
        rc = s.p.poll()
        extra = want(first) if want else None
        shown = first if first in (NOREPLY, None) else first[:200]
        ok = (alive or (eof and rc == 0)) and extra is None
        if eof and rc not in (None, 0):
            ok = False
        rec(id_, "A", title, ok, trigger,
            "alive=%s rc=%s first_reply=%r stderr_last=%r%s" % (alive, rc, shown, s.stderr_last(),
                                                               (" CHECK:" + extra) if extra else ""), sev)
    finally:
        s.kill()


PING = b'{"jsonrpc":"2.0","id":1,"method":"ping"}'


@test()
def a1(ctx):
    a_case(ctx, "A1", "truncated JSON then newline: parse error, keeps serving",
           b'{"jsonrpc":"2.0","id":1,"method":"pi\n', 'raw line {"jsonrpc":"2.0","id":1,"method":"pi', "medium",
           want=lambda f: None if isinstance(f, bytes) and b"-32700" in f else "no -32700 reply")


@test()
def a2(ctx):
    n = 50 * 1024 * 1024
    raw = b'{"jsonrpc":"2.0","id":1,"method":"ping","pad":"' + b"A" * n + b'"}\n'
    s = Server(ctx, ctx.new_dir("A2"))
    try:
        t0 = time.perf_counter()
        s.send(raw, threaded=True)
        first = s.recv(40)
        dt = time.perf_counter() - t0
        rss = s.rss_mb()
        alive = s.alive()
        rec("A2", "A", "50 MB single line: answers in bounded time and stays alive",
            first not in (NOREPLY, None) and alive and dt < 30,
            'one line: {"jsonrpc":"2.0","id":1,"method":"ping","pad":"<50 MiB of A>"}',
            "reply_after=%.1fs rss=%.0f MB alive=%s (no size cap: server parsed all 50 MiB)" % (dt, rss, alive), "low")
    finally:
        s.kill()


@test()
def a3(ctx):
    a_case(ctx, "A3a", "raw NUL bytes before a request",
           b"\x00\x00\x00" + PING + b"\n", r"bytes 00 00 00 + ping line", "low")
    s = Server(ctx, ctx.new_dir("A3b"))
    try:
        w = ctx.new_dir("A3bf")
        f = os.path.join(w, "r.json")
        r, text, err = s.tool("kya_stamp", stamp_args(what="a\u0000b", save_path=f))
        try:
            chain_ok = len(kr.Chain.load(f)) == 1
        except Exception as e:
            chain_ok = "load failed: %s" % type(e).__name__
        rec("A3b", "A", "escaped NUL (\\u0000) inside a stamped field yields a verifiable chain",
            chain_ok is True and s.alive(), 'kya_stamp what="a\\u0000b"',
            "isError=%s chain_ok=%s" % (err, chain_ok), "medium")
    finally:
        s.kill()


@test()
def a4(ctx):
    # Python only escapes bad stdin bytes under the C locale or UTF-8 mode, so a client that
    # launches the server with a UTF-8 locale or PYTHONIOENCODING=utf-8 gets a hard decode error.
    a_case(ctx, "A4", "invalid UTF-8 on stdin does not kill the server (launched with PYTHONIOENCODING=utf-8)",
           b'\xff\xfe{"jsonrpc":"2.0","id":1,"method":"ping"}\n', "bytes ff fe + ping line; env PYTHONIOENCODING=utf-8",
           "high", timeout=5, env={"PYTHONIOENCODING": "utf-8", "LC_ALL": "en_US.UTF-8"})


@test()
def a5(ctx):
    n = 10000
    raw = b'{"jsonrpc":"2.0","id":1,"method":"ping","params":' + b'{"a":' * n + b"1" + b"}" * n + b"}\n"
    a_case(ctx, "A5", "10000-level nested JSON does not kill the server", raw,
           'ping with params = {"a":{"a":... 10000 deep ...}}', "high", timeout=5)


@test()
def a6(ctx):
    s = Server(ctx, ctx.new_dir("A6"))
    try:
        w = ctx.new_dir("A6f")
        f = os.path.join(w, "r.json")
        raw = ('{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"kya_stamp","arguments":'
               '{"what":"x","amount":"1","currency":"USD","payee":"p","rule":"r","outcome":"REFUSED",'
               '"outcome":"ACCEPTED","save_path":%s}}}\n' % json.dumps(f)).encode()
        s.send(raw)
        first = s.recv(10)
        try:
            recorded = kr.Chain.load(f).receipts[0]["outcome"]
        except Exception as e:
            recorded = "none (%s)" % type(e).__name__
        rec("A6", "A", "duplicate JSON keys are rejected, not resolved last-wins",
            recorded not in ("ACCEPTED", "REFUSED"),
            'stamp args with "outcome":"REFUSED" then "outcome":"ACCEPTED" in one object',
            "server recorded outcome=%s (a first-wins policy proxy would have seen REFUSED)" % recorded, "low")
    finally:
        s.kill()


@test()
def a7(ctx):
    a_case(ctx, "A7a", "5000-digit integer id does not kill the server",
           b'{"jsonrpc":"2.0","id":' + b"9" * 5000 + b',"method":"ping"}\n', 'id = 5000 digits "9"', "high", timeout=5)
    s = Server(ctx, ctx.new_dir("A7b"))
    try:
        big = "x" * (1 << 20)
        s.send(json.dumps({"jsonrpc": "2.0", "id": big, "method": "ping"}).encode() + b"\n", threaded=True)
        r = s.recv(15)
        ok = isinstance(r, bytes) and len(r) > (1 << 20) - 100
        rec("A7b", "A", "1 MiB string id is echoed and server survives", ok and s.alive(),
            'id = "x" * 1048576', "reply_bytes=%s (echoed in full: no cap)" % (len(r) if isinstance(r, bytes) else r), "low")
    finally:
        s.kill()


@test()
def a8(ctx):
    s = Server(ctx, ctx.new_dir("A8"))
    try:
        bad = []
        for idv in (None, 1.5, {"a": 1}, [1], True, "s", -0.0, 2 ** 63):
            r = s.req("ping", id_=idv, timeout=5)
            if not (isinstance(r, dict) and r.get("id") == idv):
                bad.append(repr(idv))
        rec("A8a", "A", "ids of type null/float/object/array/bool/string are echoed unchanged", not bad,
            "ping with id in [null,1.5,{a:1},[1],true,'s',-0.0,2**63]", "mismatch or no reply for: %s" % bad, "low")
        for lit in (b"1e999", b"NaN"):
            s.send(b'{"jsonrpc":"2.0","id":' + lit + b',"method":"ping"}\n')
            line = s.recv(5)
            strict = True
            why = ""
            if isinstance(line, bytes):
                try:
                    json.loads(line, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
                except ValueError as e:
                    strict, why = False, str(e)
            else:
                strict, why = False, "no reply"
            rec("A8b" + ("i" if lit == b"1e999" else "n"), "A", "reply to id %s is strict JSON" % lit.decode(),
                strict, 'id literal %s' % lit.decode(), "reply=%r %s" % (line[:80] if isinstance(line, bytes) else line, why), "low")
    finally:
        s.kill()


@test()
def a9(ctx):
    for name, raw in (("batch of 2", b'[{"jsonrpc":"2.0","id":1,"method":"ping"},{"jsonrpc":"2.0","id":2,"method":"ping"}]\n'),
                      ("empty batch", b"[]\n"), ("bare number", b"42\n"), ("bare string", b'"x"\n')):
        a_case(ctx, "A9-" + name.split()[0], "%s: answered with a structured reply" % name, raw, raw.decode().strip(), "low",
               want=lambda f: None if isinstance(f, bytes) and (b'"error"' in f or f.startswith(b"[")) else "no error/array reply: %r" % (f,))


@test()
def a10(ctx):
    s = Server(ctx, ctx.new_dir("A10"))
    try:
        s.send(b'{"jsonrpc":"2.0","id":11,"method":"ping"}\n{"jsonrpc":"2.0","id":12,"method":"tools/list"}\n')
        a, b = s.recv(5), s.recv(5)
        ids = []
        for x in (a, b):
            try:
                ids.append(json.loads(x)["id"])
            except Exception:
                ids.append(None)
        rec("A10", "A", "two requests in one write get two replies, in order", ids == [11, 12],
            "ping id 11 + tools/list id 12 in one write()", "reply ids=%s" % ids, "medium")
    finally:
        s.kill()


@test()
def a11(ctx):
    s = Server(ctx, ctx.new_dir("A11"))
    try:
        s.send(PING)
        s.close_stdin()
        r = s.recv(5)
        try:
            s.p.wait(timeout=5)
        except Exception:
            pass
        rec("A11", "A", "request with no trailing newline, then EOF: answered, clean exit",
            isinstance(r, bytes) and b'"result"' in r and s.p.poll() == 0, "ping bytes without newline, then close stdin",
            "reply=%r rc=%s" % (r, s.p.poll()), "low")
    finally:
        s.kill()


@test()
def a12(ctx):
    a_case(ctx, "A12", "EOF in the middle of a request: clean exit, no traceback",
           b'{"jsonrpc":"2.0","id":1,"meth', 'bytes {"jsonrpc":"2.0","id":1,"meth then close stdin', "low", eof=True)


@test()
def a13(ctx):
    for label, params in (("string", "x"), ("array", [1]), ("number", 5), ("true", True)):
        raw = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params}).encode() + b"\n"
        a_case(ctx, "A13-" + label, "tools/call with params=%s: error reply, server survives" % label, raw,
               raw.decode().strip(), "high", timeout=5)
    for label, args in (("array", [1, 2]), ("string", "x")):
        raw = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                          "params": {"name": "kya_stamp", "arguments": args}}).encode() + b"\n"
        a_case(ctx, "A13-args-" + label, "tools/call arguments=%s: error reply, server survives" % label, raw,
               raw.decode().strip(), "medium", timeout=5)


@test()
def a15(ctx):
    variants = {
        "what-object": stamp_args(what={"a": 1}), "amount-float": stamp_args(amount=12.5),
        "outcome-int": stamp_args(outcome=5), "currency-array": stamp_args(currency=["USD"]),
        "payee-null": stamp_args(payee=None), "agent_ref-int": stamp_args(agent_ref=5),
        "approved_by-object": stamp_args(approved_by={"x": 1}), "what-nonascii": stamp_args(what="café"),
        "overwrite-string": stamp_args(ledger=["a"]),
    }
    for name, args in variants.items():
        d = ctx.new_dir("A15")
        f = os.path.join(d, "r.json")
        args = dict(args, save_path=f)
        s = Server(ctx, d)
        try:
            r, text, err = s.tool("kya_stamp", args, timeout=10)
            alive = s.alive()
            chain = "no file"
            if os.path.exists(f):
                try:
                    chain = "verifies (%d)" % len(kr.Chain.load(f))
                except Exception as e:
                    chain = "UNVERIFIABLE: %s" % type(e).__name__
            rec("A15-" + name, "A", "stamp type confusion %s: alive and any file written verifies" % name,
                alive and not chain.startswith("UNVERIFIABLE"), json.dumps({k: v for k, v in args.items() if k != "save_path"}),
                "isError=%s alive=%s chain=%s text=%s" % (err, alive, chain, (text or str(r))[:120]), "high")
        finally:
            s.kill()


@test()
def a16(ctx):
    """An int where a path belongs is treated by Python as a file descriptor."""
    cases = (("verify-file_path=1", "kya_verify", {"file_path": 1}),
             ("stamp-save_path=1", "kya_stamp", stamp_args(save_path=1)),
             ("stamp-pin_file=1", "kya_stamp", stamp_args(pin_file=1, save_path="r.json")),
             ("disclose-file_path=1", "kya_disclose", {"file_path": 1}))
    for label, tool, args in cases:
        s = Server(ctx, ctx.new_dir("A16"))
        try:
            r, text, err = s.tool(tool, args, timeout=5)
            alive = s.alive(timeout=3)
            rec("A16-" + label, "A", "int used as a path (fd confusion) does not damage the server: %s" % label,
                alive, json.dumps({"tool": tool, "arguments": args}),
                "reply=%s alive=%s stderr_last=%r" % (scrub(text if text else r), alive, s.stderr_last()), "high")
        finally:
            s.kill()


# =============================================================== B. paths
def world(ctx, name):
    root = ctx.new_dir(name)
    work, outside = os.path.join(root, "work"), os.path.join(root, "outside")
    os.makedirs(work)
    os.makedirs(outside)
    return work, outside


def put(path, text):
    with open(path, "w") as f:
        f.write(text)


def get(path):
    with open(path) as f:
        return f.read()


@test()
def b1(ctx):
    work, outside = world(ctx, "B1")
    s = Server(ctx, work)
    try:
        a = stamp_args(save_path="../outside/x.json")
        r, text, err = s.tool("kya_stamp", a)
        rec("B1", "B", "stamp save_path ../ traversal cannot write outside the working directory",
            not os.path.exists(os.path.join(outside, "x.json")), json.dumps(a),
            "isError=%s outside/x.json exists=%s" % (err, os.path.exists(os.path.join(outside, "x.json"))), "high")
        tgt = os.path.join(outside, "abs.json")
        a = stamp_args(save_path=tgt)
        r, text, err = s.tool("kya_stamp", a)
        rec("B2", "B", "stamp save_path absolute path outside the working directory is refused",
            not os.path.exists(tgt), json.dumps(a), "isError=%s file created outside=%s" % (err, os.path.exists(tgt)), "high")
    finally:
        s.kill()


@test()
def b3(ctx):
    work, outside = world(ctx, "B3")
    victim = os.path.join(outside, "victim.txt")
    put(victim, "")
    s = Server(ctx, work)
    try:
        a = stamp_args(pin_file=victim, save_path="r.json")
        r, text, err = s.tool("kya_stamp", a)
        after = get(victim)
        rec("B3a", "B", "stamp pin_file cannot append to an existing (empty) file outside the workspace",
            after == "", json.dumps(a), "isError=%s victim bytes 0 -> %d (appended a JSON line; a non-JSON victim is refused by the pin parser)" % (err, len(after)), "high")
        a = stamp_args(pin_file="../outside/newpins.log", save_path="r2.json")
        s.tool("kya_stamp", a)
        rec("B3b", "B", "stamp pin_file ../ traversal cannot create a file outside the workspace",
            not os.path.exists(os.path.join(outside, "newpins.log")), json.dumps(a),
            "created=%s" % os.path.exists(os.path.join(outside, "newpins.log")), "high")
    finally:
        s.kill()


@test()
def b4(ctx):
    work, outside = world(ctx, "B4")
    victim = os.path.join(outside, "precious.txt")
    put(victim, "PRECIOUS-DATA")
    s = Server(ctx, work)
    try:
        a = {"save_path": victim}
        r, text, err = s.tool("kya_disclose", a)
        rec("B4a", "B", "disclose save_path onto an existing outside file without overwrite is refused",
            get(victim) == "PRECIOUS-DATA", json.dumps(a), "isError=%s victim intact=%s" % (err, get(victim) == "PRECIOUS-DATA"), "high")
        a = {"save_path": victim, "overwrite": True}
        r, text, err = s.tool("kya_disclose", a)
        rec("B4b", "B", "disclose save_path + overwrite=true cannot clobber a file outside the workspace",
            get(victim) == "PRECIOUS-DATA", json.dumps(a), "isError=%s victim intact=%s (now %d bytes)" % (err, get(victim) == "PRECIOUS-DATA", len(get(victim))), "high")
        ghost = os.path.join(outside, "does-not-exist")
        _, t1, _ = s.tool("kya_verify", {"file_path": victim})
        _, t2, _ = s.tool("kya_verify", {"file_path": ghost})
        rec("B4c", "B", "verify gives no existence oracle for paths outside the workspace",
            ("File not found" in (t1 or "")) == ("File not found" in (t2 or "")), 'kya_verify file_path=<existing outside>/<missing outside>',
            "existing->%s | missing->%s" % (scrub(t1)[:60], scrub(t2)[:60]), "low")
    finally:
        s.kill()


@test()
def b5(ctx):
    work, outside = world(ctx, "B5")
    mk_chain(os.path.join(outside, "chain.json"), 3)
    put(os.path.join(outside, "records.json"),
        json.dumps([{"outcome": "REFUSED", "what": LEAK_MARKER, "rule": "x", "seal": "s", "prev": "p"}]))
    s = Server(ctx, work)
    try:
        a = {"file_path": os.path.join(outside, "chain.json")}
        r, text, err = s.tool("kya_verify", a)
        read = '"receipt_count": 3' in (text or "")
        rec("B5a", "B", "verify cannot read a chain file outside the workspace", not read, json.dumps(a),
            "isError=%s read=%s" % (err, read), "medium")
        a = {"file_path": os.path.join(outside, "records.json")}
        r, text, err = s.tool("kya_disclose", a)
        leaked = LEAK_MARKER in (text or "")
        rec("B5b", "B", "disclose cannot return the contents of an arbitrary outside JSON file", not leaked, json.dumps(a),
            "isError=%s marker from outside file present in result=%s" % (err, leaked), "high")
    finally:
        s.kill()


@test()
def b6(ctx):
    work, outside = world(ctx, "B6")
    victim = os.path.join(outside, "victim.json")
    put(victim, "[]")
    os.symlink(victim, os.path.join(work, "link.json"))
    s = Server(ctx, work)
    try:
        s.tool("kya_stamp", stamp_args(save_path="link.json"))
        rec("B6a", "B", "stamp through a symlink-to-file leaves the link target alone", get(victim) == "[]",
            'save_path="link.json" (link -> outside/victim.json holding [])',
            "victim=%s link_is_symlink_after=%s" % ("intact" if get(victim) == "[]" else "OVERWRITTEN",
                                                   os.path.islink(os.path.join(work, "link.json"))), "high")
        put(victim, "PRECIOUS")
        os.symlink(victim, os.path.join(work, "dlink.json"))
        s.tool("kya_disclose", {"save_path": "dlink.json", "overwrite": True})
        rec("B6b", "B", "disclose overwrite through a symlink does not modify the target", get(victim) == "PRECIOUS",
            'disclose save_path="dlink.json" overwrite=true', "victim=%s" % ("intact" if get(victim) == "PRECIOUS" else "OVERWRITTEN"), "high")
        newt = os.path.join(outside, "created-via-link.log")
        os.symlink(newt, os.path.join(work, "plink.log"))
        s.tool("kya_stamp", stamp_args(pin_file="plink.log", save_path="r3.json"))
        rec("B6c", "B", "stamp pin_file through a symlink does not create or append to the target outside",
            not os.path.exists(newt), 'pin_file="plink.log" (link -> nonexistent file in outside dir)',
            "target created outside via link=%s" % os.path.exists(newt), "high")
    finally:
        s.kill()


@test()
def b7(ctx):
    work, outside = world(ctx, "B7")
    os.symlink(outside, os.path.join(work, "linkdir"))
    s = Server(ctx, work)
    try:
        s.tool("kya_stamp", stamp_args(save_path="linkdir/x.json"))
        rec("B7", "B", "stamp through a symlink-to-directory cannot write outside the workspace",
            not os.path.exists(os.path.join(outside, "x.json")), 'save_path="linkdir/x.json" (linkdir -> outside dir)',
            "outside/x.json exists=%s" % os.path.exists(os.path.join(outside, "x.json")), "high")
    finally:
        s.kill()


def stuck_case(ctx, id_, title, tool, args_fn, name="fifo", sev="medium"):
    work, outside = world(ctx, id_)
    fifo = os.path.join(outside, name)
    os.mkfifo(fifo)
    s = Server(ctx, work)
    try:
        args = args_fn(fifo)
        t0 = time.perf_counter()
        r, text, err = s.tool(tool, args, timeout=3)
        dt = time.perf_counter() - t0
        replied = r is not NOREPLY and r is not None
        rec(id_, "B", title, replied, json.dumps({"tool": tool, "arguments": args}),
            "reply within 3s=%s (waited %.1fs); server blocked on open() of a FIFO nobody writes to" % (replied, dt), sev)
    finally:
        s.kill()


@test()
def b8(ctx):
    stuck_case(ctx, "B8a", "verify file_path=FIFO does not hang the server", "kya_verify", lambda p: {"file_path": p})
    stuck_case(ctx, "B8b", "stamp save_path=FIFO does not hang the server", "kya_stamp", lambda p: stamp_args(save_path=p))
    stuck_case(ctx, "B8c", "stamp pin_file=FIFO does not hang the server", "kya_stamp", lambda p: stamp_args(pin_file=p, save_path="r.json"))
    stuck_case(ctx, "B8d", "disclose file_path=FIFO does not hang the server", "kya_disclose", lambda p: {"file_path": p})


def zero_case(ctx, id_, title, tool, args):
    s = Server(ctx, ctx.new_dir(id_))
    try:
        s.send(json.dumps({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                           "params": {"name": tool, "arguments": args}}).encode() + b"\n")
        t0, peak, replied = time.perf_counter(), 0.0, False
        while time.perf_counter() - t0 < 4:
            try:
                x = s.q.get(timeout=0.1)
                replied = True
                break
            except queue.Empty:
                pass
            peak = max(peak, s.rss_mb())
            if peak > 600:
                break
        rec(id_, "B", title, replied and peak < 300, json.dumps({"tool": tool, "arguments": args}),
            "replied=%s peak_rss=%.0f MB after %.1fs (killed at 600 MB; /dev/zero never ends)" % (replied, peak, time.perf_counter() - t0),
            "high")
    finally:
        s.kill()


@test()
def b9(ctx):
    zero_case(ctx, "B9a", "verify file_path=/dev/zero is bounded (memory and time)", "kya_verify", {"file_path": "/dev/zero"})
    zero_case(ctx, "B9b", "stamp pin_file=/dev/zero is bounded (memory and time)", "kya_stamp",
              stamp_args(pin_file="/dev/zero", save_path="r.json"))


@test()
def b10(ctx):
    work, outside = world(ctx, "B10")
    s = Server(ctx, work)
    try:
        bad = []
        for tool, key in (("kya_stamp", "save_path"), ("kya_stamp", "pin_file"), ("kya_verify", "file_path"),
                          ("kya_disclose", "save_path"), ("kya_disclose", "file_path")):
            args = stamp_args() if tool == "kya_stamp" else {}
            args[key] = "ok.json\u0000../../outside/evil.json"
            if key == "pin_file":
                args["save_path"] = "r.json"
            r, text, err = s.tool(tool, args, timeout=5)
            if r in (NOREPLY, None) or not s.alive():
                bad.append("%s.%s: dead" % (tool, key))
        made = sorted(os.listdir(outside)) + [f for f in os.listdir(work) if f.startswith("ok")]
        rec("B10", "B", "paths containing a NUL byte are rejected and create nothing", not bad and not made,
            'every path argument = "ok.json\\u0000../../outside/evil.json"', "problems=%s files_created=%s" % (bad, made), "medium")
    finally:
        s.kill()


@test()
def b11(ctx):
    work, outside = world(ctx, "B11")
    s = Server(ctx, work)
    try:
        long = "a" * 4096
        r, text, err = s.tool("kya_stamp", stamp_args(save_path=long))
        r2, t2, e2 = s.tool("kya_verify", {"file_path": "/".join(["d" * 255] * 20)})
        alive = s.alive()
        rec("B11", "B", "4096-char and 5100-char paths give an error reply, not a crash", err and e2 and alive,
            'save_path = "a"*4096 ; file_path = ("d"*255 + "/")*20', "stamp isError=%s verify isError=%s alive=%s reply_len=%d" % (err, e2, alive, len(text or "")), "low")
        d = os.path.join(work, "adir")
        os.mkdir(d)
        r3, t3, e3 = s.tool("kya_stamp", stamp_args(save_path=d))
        rec("B12", "B", "save_path = a directory is refused and the directory survives", e3 and os.path.isdir(d),
            'save_path="adir" (a directory)', "isError=%s dir intact=%s" % (e3, os.path.isdir(d)), "low")
    finally:
        s.kill()


@test()
def b13(ctx):
    work, outside = world(ctx, "B13")
    victim = os.path.join(outside, "victim.txt")
    put(victim, "PRECIOUS")
    s = Server(ctx, work)
    try:
        os.symlink(victim, os.path.join(work, "t.json.tmp.%d" % s.p.pid))
        s.tool("kya_stamp", stamp_args(save_path="t.json"))
        rec("B13", "B", "predictable temp name (<path>.tmp.<pid>) cannot be pre-planted as a symlink to hijack the write",
            get(victim) == "PRECIOUS", 'symlink t.json.tmp.<server pid> -> outside file, then stamp save_path="t.json"',
            "victim=%s" % ("intact" if get(victim) == "PRECIOUS" else "OVERWRITTEN with chain JSON"), "low")
    finally:
        s.kill()


# ================================================================ C. URLs
class Listener:
    """A local stub standing in for a witness. MOCKED: it is not a witness."""

    def __init__(self, fn):
        self.hits, self.conns, self.bytes_sent, self.stop = [], 0, 0, False
        outer = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *a):
                pass

            def _go(self):
                n = int(self.headers.get("Content-Length") or 0)
                if n:
                    self.rfile.read(n)
                outer.hits.append((self.command, self.path))
                try:
                    fn(self, outer)
                except Exception:
                    pass
            do_GET = do_POST = _go

        class S(ThreadingHTTPServer):
            daemon_threads = True

            def get_request(self):
                c = super().get_request()
                outer.conns += 1
                return c

        self.srv = S(("127.0.0.1", 0), H)
        self.port = self.srv.server_address[1]
        self.url = "http://127.0.0.1:%d" % self.port
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.stop = True
        self.srv.shutdown()
        self.srv.server_close()


def reply_json(h, code, obj):
    b = json.dumps(obj).encode()
    h.send_response(code)
    h.send_header("Content-Type", "application/json")
    h.send_header("Content-Length", str(len(b)))
    h.end_headers()
    h.wfile.write(b)


def witness_ok(h, L):
    if h.command == "GET":
        reply_json(h, 200, {"pins": []})
    else:
        reply_json(h, 400, {"error": "INTERNAL-SERVICE-MARKER"})


def need_witness(ctx, id_, title):
    if ctx.has_witness:
        return False
    rec(id_, "C", title, None, "-", "NOT APPLICABLE: this tree's kya_stamp has no witness_url argument", status="SKIP")
    return True


@test()
def c0(ctx):
    if ctx.has_witness:
        return
    L = Listener(witness_ok)
    work, _ = world(ctx, "C0")
    s = Server(ctx, work)
    try:
        r, text, err = s.tool("kya_stamp", stamp_args(witness_url=L.url, save_path="r.json"))
        s.tool("kya_verify", {"file_path": "r.json", "witness_url": L.url})
        rec("C0", "C", "witness_url is ignored in this tree: zero connections to an agent-chosen listener",
            L.conns == 0, 'kya_stamp/kya_verify witness_url="http://127.0.0.1:<port>"',
            "connections received=%d (argument silently ignored, which also means no witness protection)" % L.conns, "low")
    finally:
        s.kill()
        L.close()


@test()
def c1(ctx):
    if need_witness(ctx, "C1", "witness_url to an agent-chosen loopback listener is refused (SSRF)"):
        return
    L = Listener(witness_ok)
    work, _ = world(ctx, "C1")
    s = Server(ctx, work)
    try:
        a = stamp_args(witness_url=L.url, save_path="r.json")
        r, text, err = s.tool("kya_stamp", a)
        reflected = "INTERNAL-SERVICE-MARKER" in (text or "")
        v, vt, ve = s.tool("kya_verify", {"file_path": "r.json", "witness_url": L.url})
        methods = sorted(set(m for m, _ in L.hits))
        rec("C1", "C", "witness_url to an agent-chosen loopback listener is refused (SSRF)", L.conns == 0,
            'kya_stamp witness_url="http://127.0.0.1:<port>" (listener started by this test)',
            "listener saw connections=%d requests=%s methods=%s (stamp 2 + verify 1 expected if SSRF)" % (L.conns, L.hits, methods), "high")
        rec("C1b", "C", "an internal service's response body is not reflected into the tool result", not reflected,
            'listener answers POST /pins with {"error":"INTERNAL-SERVICE-MARKER"}',
            "marker reflected to the agent=%s text=%s" % (reflected, scrub(text)), "medium")
        L.hits.clear()
        a = stamp_args(witness_url=L.url + "/admin/delete?x=", save_path="r2.json")
        s.tool("kya_stamp", a)
        paths = sorted(set(p for _, p in L.hits))
        rec("C1c", "C", "agent cannot choose the request path (query-string trick defeats the /pins suffix)",
            paths in ([], ["/pins"]), 'witness_url="http://127.0.0.1:<port>/admin/delete?x="',
            "paths the listener actually received=%s" % paths, "high")
    finally:
        s.kill()
        L.close()


@test()
def c3(ctx):
    if need_witness(ctx, "C3", "non-http(s) schemes are refused with no side effect"):
        return
    L = Listener(witness_ok)
    work, outside = world(ctx, "C3")
    put(os.path.join(outside, "x"), "x")
    s = Server(ctx, work)
    try:
        bad = []
        for u in ("file://" + outside + "/x", "FILE://" + outside + "/x", "ftp://127.0.0.1:%d/" % L.port,
                  "gopher://127.0.0.1:%d/" % L.port, " " + L.url, "javascript:1"):
            r, text, err = s.tool("kya_stamp", stamp_args(witness_url=u, save_path="r.json"), timeout=8)
            if not err or "must start with" not in (text or ""):
                bad.append(u[:30])
        rec("C3", "C", "file://, FILE://, ftp://, gopher://, leading-space and javascript: URLs are refused",
            not bad and L.conns == 0 and not os.path.exists(os.path.join(work, "r.json")),
            "witness_url in [file://..., FILE://..., ftp://..., gopher://..., ' http://...', javascript:1]",
            "not-refused=%s listener_connections=%d chain_written=%s" % (bad, L.conns, os.path.exists(os.path.join(work, "r.json"))), "high")
    finally:
        s.kill()
        L.close()


@test()
def c4(ctx):
    if need_witness(ctx, "C4", "witness_url=169.254.169.254 is refused by policy, not tried"):
        return
    work, _ = world(ctx, "C4")
    s = Server(ctx, work)
    try:
        u = "http://169.254.169.254/latest/meta-data/"
        t0 = time.perf_counter()
        r, text, err = s.tool("kya_stamp", stamp_args(witness_url=u, save_path="r.json"), timeout=20)
        dt = time.perf_counter() - t0
        attempted = any(w in (text or "") for w in ("timed out", "unreachable", "No route", "refused", "could not be reached"))
        rec("C4", "C", "witness_url=169.254.169.254 is refused by policy, not tried", not attempted, 'witness_url="%s"' % u,
            "after %.1fs: %s. Whether the endpoint answers on a cloud host: NOT VERIFIED (this host is not one)." % (dt, scrub(text)), "high")
    finally:
        s.kill()


@test()
def c5(ctx):
    if need_witness(ctx, "C5", "a redirect from the witness URL is not followed to another host"):
        return
    inner = Listener(witness_ok)

    def redir(h, L):
        h.send_response(302)
        h.send_header("Location", inner.url + "/pins")
        h.send_header("Content-Length", "0")
        h.end_headers()
    outer = Listener(redir)
    work, _ = world(ctx, "C5")
    s = Server(ctx, work)
    try:
        s.tool("kya_stamp", stamp_args(witness_url=outer.url, save_path="r.json"))
        rec("C5", "C", "a redirect from the witness URL is not followed to another host", inner.conns == 0,
            'witness_url=<listener A>; A answers 302 Location: <listener B>/pins',
            "listener B (the 'internal' service) connections=%d requests=%s" % (inner.conns, inner.hits), "high")
    finally:
        s.kill()
        inner.close()
        outer.close()


@test()
def c6(ctx):
    if need_witness(ctx, "C6", "a witness that never answers: timeout honoured"):
        return

    def hang(h, L):
        t = time.time()
        while not L.stop and time.time() - t < 60:
            time.sleep(0.2)
    L = Listener(hang)
    work, _ = world(ctx, "C6")
    s = Server(ctx, work)
    try:
        t0 = time.perf_counter()
        s.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
            "name": "kya_stamp", "arguments": stamp_args(witness_url=L.url, save_path="r.json")}}).encode() + b"\n")
        s.send(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping"}).encode() + b"\n")
        first = s.recv(15)
        dt = time.perf_counter() - t0
        second = s.recv(15)
        dt2 = time.perf_counter() - t0
        rec("C6", "C", "a witness that accepts the connection and never answers: stamp returns within 8 s (TIMEOUT is 5 s)",
            first is not NOREPLY and dt < 8, 'witness_url=<listener that sleeps>', "stamp replied after %.1fs; no chain written=%s" % (dt, not os.path.exists(os.path.join(work, "r.json"))), "medium")
        rec("C6b", "C", "a stalled witness does not block an unrelated ping sent right behind it", dt2 - dt < 1 and dt < 1,
            "stamp (stalled witness) then ping id 2, same connection", "ping answered %.1fs after the request was sent (head-of-line blocking: server is single-threaded)" % dt2, "low")
    finally:
        s.kill()
        L.close()


@test()
def c7(ctx):
    if need_witness(ctx, "C7", "a witness that trickles bytes forever cannot pin the server"):
        return

    def drip(h, L):
        h.send_response(200)
        h.send_header("Content-Type", "application/json")
        h.end_headers()
        h.wfile.write(b'{"pins":[')
        h.wfile.flush()
        while not L.stop:
            time.sleep(0.5)
            h.wfile.write(b" ")
            h.wfile.flush()
            L.bytes_sent += 1
    L = Listener(drip)
    work, _ = world(ctx, "C7")
    s = Server(ctx, work)
    try:
        t0 = time.perf_counter()
        r, text, err = s.tool("kya_stamp", stamp_args(witness_url=L.url, save_path="r.json"), timeout=13)
        dt = time.perf_counter() - t0
        replied = r is not NOREPLY
        rec("C7", "C", "a witness that trickles 1 byte per 0.5 s forever: call ends within 13 s (socket timeout is per read, not total)",
            replied, 'witness_url=<listener: headers, then one byte every 0.5 s, never finishing>',
            "replied=%s after %.1fs; bytes trickled=%d. The 5 s TIMEOUT never fires because each read succeeds." % (replied, dt, L.bytes_sent), "high")
    finally:
        s.kill()
        L.close()


@test()
def c8(ctx):
    if need_witness(ctx, "C8", "an endless fast stream from the witness is cut off"):
        return
    chunk = b" " * 65536

    def flood(h, L):
        h.send_response(200)
        h.send_header("Content-Type", "application/json")
        h.end_headers()
        h.wfile.write(b'{"pins":[')
        t = time.time()
        while not L.stop and time.time() - t < 15:
            h.wfile.write(chunk)
            L.bytes_sent += len(chunk)
    L = Listener(flood)
    work, _ = world(ctx, "C8")
    s = Server(ctx, work)
    try:
        t0 = time.perf_counter()
        r, text, err = s.tool("kya_stamp", stamp_args(witness_url=L.url, save_path="r.json"), timeout=10)
        dt = time.perf_counter() - t0
        rss = s.rss_mb()
        rec("C8", "C", "an endless fast stream from the witness is cut off quickly and cheaply",
            r is not NOREPLY and dt < 5 and rss < 200, 'witness_url=<listener streaming spaces forever>',
            "replied after %.1fs, listener sent %.1f MB, server rss %.0f MB, reply=%s" % (dt, L.bytes_sent / 1e6, rss, scrub(text)), "medium")
    finally:
        s.kill()
        L.close()


# ============================================================ D. resources
@test()
def d1(ctx):
    d = ctx.new_dir("D1")
    f = os.path.join(d, "big.json")
    t0 = time.perf_counter()
    mk_chain(f, 100000)
    build = time.perf_counter() - t0
    s = Server(ctx, d)
    try:
        t0 = time.perf_counter()
        r, text, err = s.tool("kya_verify", {"file_path": f}, timeout=60)
        tv = time.perf_counter() - t0
        okv = '"verified": true' in (text or "")
        t0 = time.perf_counter()
        r, text2, err2 = s.tool("kya_stamp", stamp_args(save_path=f), timeout=60)
        ts = time.perf_counter() - t0
        size = os.path.getsize(f) / 1e6
        METRICS["D1"] = dict(chain_build_s=round(build, 1), verify_s=round(tv, 2), stamp_s=round(ts, 2), file_mb=round(size, 1))
        rec("D1", "D", "100000-receipt chain: verify and stamp each finish in under 5 s", okv and not err2 and tv < 5 and ts < 5,
            "kya_verify then kya_stamp on a 100000-receipt file",
            "verify %.2fs (ok=%s), stamp %.2fs (isError=%s), file %.1f MB; every stamp rereads, reverifies and rewrites the whole file" % (tv, okv, ts, err2, size), "medium")
    finally:
        s.kill()


@test()
def d2(ctx):
    d = ctx.new_dir("D2")
    f = os.path.join(d, "r.json")
    s = Server(ctx, d)
    try:
        t0 = time.perf_counter()
        r, text, err = s.tool("kya_stamp", stamp_args(what="W" * (10 * 1024 * 1024), save_path=f), timeout=60)
        dt = time.perf_counter() - t0
        accepted = not err
        r2, t2, e2 = s.tool("kya_stamp", stamp_args(save_path=f), timeout=60)
        verifies = False
        if os.path.exists(f):
            try:
                verifies = len(kr.Chain.load(f)) >= 1
            except Exception:
                pass
        size = os.path.getsize(f) / 1e6 if os.path.exists(f) else 0
        rec("D2a", "D", "10 MB 'what' field: server survives and any chain written verifies", s.alive() and (verifies or not accepted),
            'kya_stamp what="W"*10485760', "accepted=%s in %.1fs, file %.1f MB, verifies=%s, 2nd stamp isError=%s" % (accepted, dt, size, verifies, e2), "medium")
        rec("D2b", "D", "a field-size limit exists: 'what' of 10 MB is rejected", not accepted, 'kya_stamp what="W"*10485760',
            "accepted=%s. No cap means an agent can grow the evidence file by 10 MB per call and make every later stamp slower." % accepted, "low")
    finally:
        s.kill()


@test()
def d3(ctx):
    d = ctx.new_dir("D3")
    f = os.path.join(d, "shared.json")
    mk_chain(f, 2000)
    n_srv, per = 20, 10
    srvs = [Server(ctx, d) for _ in range(n_srv)]
    try:
        for s in srvs:
            s.initialize()
        bar = threading.Barrier(n_srv)
        errs = []

        def work(i):
            bar.wait()
            for k in range(per):
                r, text, err = srvs[i].tool("kya_stamp", stamp_args(what="p%d-%d" % (i, k), save_path=f), timeout=60)
                if err:
                    errs.append(scrub(text or r)[:80])
        ts = [threading.Thread(target=work, args=(i,)) for i in range(n_srv)]
        t0 = time.perf_counter()
        for t in ts:
            t.start()
        for t in ts:
            t.join(90)
        dt = time.perf_counter() - t0
        want = 2000 + n_srv * per
        try:
            c = kr.Chain.load(f)
            got, state = len(c), "chain verifies"
        except Exception as e:
            got, state = -1, "UNVERIFIABLE %s" % type(e).__name__
        lost = want - got if got >= 0 else "n/a"
        METRICS["D3"] = dict(expected=want, got=got, lost=lost, secs=round(dt, 1))
        rec("D3", "D", "20 server processes stamping one file: no lost updates, chain verifies", got == want,
            "20 server processes x 10 kya_stamp on one 2000-receipt file, started together",
            "%s; expected %d receipts, file has %d, LOST %s; error replies=%d %s" % (state, want, got, lost, len(errs), errs[:1]), "high")
    finally:
        for s in srvs:
            s.kill()


@test()
def d4(ctx):
    d = ctx.new_dir("D4")
    f = os.path.join(d, "r.json")
    base = mk_chain(f, 20000)
    N = len(base)
    states = []
    for trial in range(12):
        s = Server(ctx, d)
        try:
            s.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
                "name": "kya_stamp", "arguments": stamp_args(what="k%d" % trial, save_path=f)}}).encode() + b"\n")
            time.sleep(random.uniform(0.15, 0.6))
            s.p.send_signal(signal.SIGKILL)
            s.p.wait()
        finally:
            s.kill()
        try:
            n = len(kr.Chain.load(f))
            states.append("ok%d" % (n - N))
        except Exception as e:
            states.append("BAD:%s" % type(e).__name__)
            break
    litter = len([x for x in os.listdir(d) if ".tmp." in x])
    bad = [x for x in states if x.startswith("BAD")]
    rec("D4", "D", "SIGKILL during a stamp write: the chain file still loads and verifies", not bad,
        "kya_stamp onto a 20000-receipt file, SIGKILL 0.15-0.6 s later, 12 trials",
        "outcomes (growth beyond start)=%s stale .tmp files left behind=%d (INFO, not scored)" % (states, litter), "high")


@test()
def d5(ctx):
    d = ctx.new_dir("D5")
    f = os.path.join(d, "r.json")
    mk_chain(f, 5)
    doc = json.loads(get(f))
    doc[2]["amount"] = "999999"
    put(f, json.dumps(doc))
    before = get(f)
    s = Server(ctx, d)
    try:
        r, text, err = s.tool("kya_stamp", stamp_args(save_path=f))
        rec("D5", "D", "stamping onto a tampered chain is refused and the file is left untouched", err and get(f) == before,
            "kya_stamp save_path=<chain with receipt 3 amount edited>", "isError=%s file unchanged=%s text=%s" % (err, get(f) == before, scrub(text)[:120]), "high")
    finally:
        s.kill()


# ============================================================== E. leaks
@test()
def e1(ctx):
    work, outside = world(ctx, "E1")
    put(os.path.join(work, "garbage.json"), "not json at all")
    put(os.path.join(work, "pins.bad"), "also not json\n")
    os.mkdir(os.path.join(work, "adir"))
    s = Server(ctx, work)
    try:
        calls = [("kya_verify", {"file_path": "missing.json"}), ("kya_verify", {"file_path": "garbage.json"}),
                 ("kya_verify", {"receipts_json": "{{"}), ("kya_verify", {"file_path": "adir"}),
                 ("kya_stamp", stamp_args(save_path="garbage.json")), ("kya_stamp", stamp_args(save_path="nosuchdir/x.json")),
                 ("kya_stamp", stamp_args(pin_file="pins.bad", save_path="ok.json")), ("kya_stamp", {}),
                 ("kya_disclose", {"save_path": "nosuchdir/d.json"}), ("kya_disclose", {"file_path": "garbage.json"}),
                 ("kya_status", {}), ("nope_tool", {})]
        blob = ""
        for t, a in calls:
            r, text, err = s.tool(t, a, timeout=10)
            blob += " " + (text if text is not None else json.dumps(r) if not isinstance(r, bytes) else r.decode("utf8", "replace"))
        blob += " " + s.err.decode("utf8", "replace")
        hits = []
        for label, needle in (("env var value", ENV_MARKER), ("workspace absolute path", work), ("temp root", ctx.root),
                              ("HOME", ctx.home), ("python executable", sys.executable), ("source tree", ctx.tree),
                              ("python traceback", "Traceback (most recent")):
            if needle in blob:
                hits.append(label)
        pid = re.search(r"\.tmp\.(\d+)", blob)
        if pid:
            hits.append("server pid (from temp-file name in error)")
        rec("E1", "E", "error text and stderr never carry host absolute paths, env values, tracebacks or the server pid", not hits,
            "12 error-provoking calls (missing/garbage/dir files, bad pin file, missing dir, empty args, unknown tool)",
            "leaked: %s" % (hits or "nothing"), "low")
    finally:
        s.kill()


@test()
def e2(ctx):
    work, outside = world(ctx, "E2")
    keyf = os.path.join(outside, "fake.key")
    hexf = os.path.join(outside, "fake.hex")
    put(keyf, KEY_MARKER + "\n")
    put(hexf, "12" + KEY_MARKER.encode().hex() + "\n")
    s = Server(ctx, work)
    try:
        # positive control: a path that IS echoed must be caught by the same scan
        _, ctl, _ = s.tool("kya_verify", {"file_path": KEY_MARKER})
        if KEY_MARKER not in (ctl or ""):
            raise AssertionError("E2 positive control failed: the scan cannot see an echoed value")
        blob = ""
        for p in (keyf, hexf):
            for t, a in (("kya_verify", {"file_path": p}), ("kya_verify", {"receipts_json": get(p)}),
                         ("kya_verify", {"file_path": "x", "pin_file": p}), ("kya_verify", {"pin_file": p, "witness_key_file": p}),
                         ("kya_stamp", stamp_args(save_path=p)), ("kya_stamp", stamp_args(pin_file=p, save_path="ok.json")),
                         ("kya_disclose", {"file_path": p}), ("kya_verify", {"file_path": "r.json", "witness_url": "http://127.0.0.1:9", "witness_key_file": p})):
                r, text, err = s.tool(t, a, timeout=10)
                blob += " " + (text if text is not None else str(r))
        blob += s.err.decode("utf8", "replace")
        leaked = KEY_MARKER in blob or KEY_MARKER.encode().hex() in blob or "12" + KEY_MARKER.encode().hex()[:10] in blob
        rec("E2", "E", "a key file pointed at via any path argument never has its contents echoed", not leaked,
            "a MOCKED fake key file as file_path, pin_file, save_path, witness_key_file, receipts_json",
            "contents (or hex of them) present in any result or stderr=%s (contents never printed here)" % leaked, "high")
    finally:
        s.kill()


# ============================================================== F. speed
def timed(s, tool, args, n):
    xs = []
    for _ in range(n):
        t0 = time.perf_counter()
        s.tool(tool, args, timeout=60)
        xs.append((time.perf_counter() - t0) * 1000)
    return xs


def stats(xs):
    return dict(n=len(xs), p50=round(pct(xs, 50), 1), p95=round(pct(xs, 95), 1), max=round(max(xs), 1))


@test("seq")
def f1(ctx):
    xs = []
    for _ in range(20):
        s = Server(ctx, ctx.new_dir("F1"))
        try:
            r = s.initialize()
            xs.append((time.perf_counter() - s.t0) * 1000)
        finally:
            s.kill()
    med = statistics.median(xs)
    METRICS["startup_ms"] = dict(median=round(med, 1), p95=round(pct(xs, 95), 1), min=round(min(xs), 1))
    rec("F1", "F", "startup to first initialize response: median of 20 under 100 ms", med < 100, "spawn -> initialize reply, 20 spawns",
        "median %.1f ms, p95 %.1f, min %.1f (includes interpreter boot, measured from Popen)" % (med, pct(xs, 95), min(xs)), "low")


@test("seq")
def f2(ctx):
    d = ctx.new_dir("F2")
    f = os.path.join(d, "r.json")
    s = Server(ctx, d)
    try:
        s.initialize()
        xs = timed(s, "kya_stamp", stamp_args(save_path=f), 200)
        METRICS["stamp_fresh_200"] = stats(xs)
        METRICS["stamp_fresh_first20_p50"] = round(pct(xs[:20], 50), 1)
        METRICS["stamp_fresh_last20_p50"] = round(pct(xs[-20:], 50), 1)
        tot = sum(xs) / 1000
        METRICS["stamp_throughput_per_s"] = round(200 / tot, 1)
        rec("F2", "F", "kya_stamp on a small chain (1..10 receipts): p95 under 100 ms", pct(xs[:10], 95) < 100,
            "10 sequential stamps onto a fresh file", "p50 %.1f ms p95 %.1f ms" % (pct(xs[:10], 50), pct(xs[:10], 95)), "low")
    finally:
        s.kill()
    for n in (10, 1000, 10000):
        d = ctx.new_dir("F2s")
        f = os.path.join(d, "r.json")
        mk_chain(f, n)
        s = Server(ctx, d)
        try:
            s.initialize()
            xs = timed(s, "kya_stamp", stamp_args(save_path=f), 15)
            METRICS["stamp_on_%d" % n] = stats(xs)
            vx = timed(s, "kya_verify", {"file_path": f}, 20)
            METRICS["verify_%d" % n] = stats(vx)
            if n == 10:
                rec("F3", "F", "kya_stamp and kya_verify on a 10-receipt chain: p95 under 100 ms",
                    pct(xs, 95) < 100 and pct(vx, 95) < 100, "15 stamps, 20 verifies on a 10-receipt file",
                    "stamp p50 %.1f p95 %.1f ms; verify p50 %.1f p95 %.1f ms" % (pct(xs, 50), pct(xs, 95), pct(vx, 50), pct(vx, 95)), "low")
        finally:
            s.kill()


@test("seq")
def f4(ctx):
    s = Server(ctx, ctx.new_dir("F4"))
    try:
        s.initialize()
        n = 1000
        t0 = time.perf_counter()
        for _ in range(n):
            s.req("ping", timeout=5)
        seq = n / (time.perf_counter() - t0)
        msg = b'{"jsonrpc":"2.0","id":7,"method":"ping"}\n'
        t0 = time.perf_counter()
        s.send(msg * n, threaded=True)
        got = 0
        while got < n:
            x = s.recv(10)
            if x in (NOREPLY, None):
                break
            got += 1
        pipe = got / (time.perf_counter() - t0)
        METRICS["ping_req_per_s_sequential"] = round(seq)
        METRICS["ping_req_per_s_pipelined"] = round(pipe)
        rec("F4", "F", "1000 pipelined pings all answered", got == n, "1000 ping lines in one write",
            "answered %d/1000; sequential %.0f req/s, pipelined %.0f req/s" % (got, seq, pipe), "low")
    finally:
        s.kill()


# =================================================================== main
def main():
    global kr
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", default=os.path.abspath(os.path.join(HERE, "..")))
    ap.add_argument("--json")
    ap.add_argument("--only", help="comma list of test function names, e.g. d4,d5,a1 (for mutation checks)")
    args = ap.parse_args()
    ctx = Ctx(os.path.abspath(args.tree))
    sys.path.insert(0, ctx.src)
    import knowyouragenticai_receipts as _kr
    kr = _kr
    t_start = time.perf_counter()
    try:
        s = Server(ctx, ctx.new_dir("probe"))
        s.initialize()
        r = s.req("tools/list")
        try:
            props = [t for t in r["result"]["tools"] if t["name"] == "kya_stamp"][0]["inputSchema"]["properties"]
            ctx.has_witness = "witness_url" in props
        except Exception:
            pass
        s.kill()
        print("tree=%s version=%s witness_url_supported=%s" % (ctx.tree, kr.__version__, ctx.has_witness))
        only = set(args.only.split(",")) if args.only else None
        par = [fn for g, fn in TESTS if g == "par" and (only is None or fn.__name__ in only)]
        seq = [fn for g, fn in TESTS if g == "seq" and (only is None or fn.__name__ in only)]

        def run(fn):
            try:
                fn(ctx)
            except Exception as e:  # a harness fault must not look like a pass
                rec(fn.__name__, "?", "HARNESS ERROR in %s" % fn.__name__, False, "-", "%s: %s" % (type(e).__name__, e), "harness")
        with ThreadPoolExecutor(max_workers=10) as ex:
            list(ex.map(run, par))
        for fn in seq:
            run(fn)
    finally:
        ctx.cleanup()
    rows = sorted(RESULTS, key=lambda r: r["id"])
    npass = sum(r["status"] == "PASS" for r in rows)
    nfail = sum(r["status"] == "FAIL" for r in rows)
    nskip = sum(r["status"] == "SKIP" for r in rows)
    print("\n=== FAILURES ===")
    for r in rows:
        if r["status"] == "FAIL":
            print("%s [%s/%s] %s\n   trigger : %s\n   observed: %s" % (r["id"], r["cat"], r["sev"], r["title"], r["trigger"], r["observed"]))
    print("\n=== SPEED / METRICS ===")
    for k, v in METRICS.items():
        print("%-28s %s" % (k, v))
    print("\nPASS %d  FAIL %d  SKIP %d  (%.1fs)" % (npass, nfail, nskip, time.perf_counter() - t_start))
    if args.json:
        with open(args.json, "w") as f:
            json.dump(dict(tree=ctx.tree, results=rows, metrics=METRICS), f, indent=1)
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
