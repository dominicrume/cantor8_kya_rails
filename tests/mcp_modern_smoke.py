#!/usr/bin/env python3
"""Our MCP servers must speak the stateless protocol, and still speak the old one.

    python3 tests/mcp_modern_smoke.py

MCP revision 2026-07-28 retired the initialize handshake and the session header. Every
request now carries its protocol version, capabilities and caller in `_meta`, a server
MUST implement `server/discover`, a request missing a required `_meta` field is -32602,
and an unsupported version is -32022 with the list it does support. A server built on
the handshake works for old clients and is wrong for new ones.

This drives each of our servers as a subprocess and checks all of that, plus the
promise of the stateless design: nothing from one request leaks into the next.

Stdlib only, per THE-RULES.md.
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION, CAPS, CLIENT, SERVER = ("io.modelcontextprotocol/protocolVersion",
                                 "io.modelcontextprotocol/clientCapabilities",
                                 "io.modelcontextprotocol/clientInfo",
                                 "io.modelcontextprotocol/serverInfo")
fails = []


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


class Server:
    def __init__(self, argv, env_extra=None):
        env = dict(os.environ)
        env.update(env_extra or {})
        self.cwd = tempfile.mkdtemp()
        self.p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, cwd=self.cwd, env=env)
        self.n = 0

    def raw(self, line):
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()
        return json.loads(self.p.stdout.readline())

    def call(self, method, params=None):
        self.n += 1
        msg = {"jsonrpc": "2.0", "id": self.n, "method": method}
        if params is not None:
            msg["params"] = params
        return self.raw(json.dumps(msg))

    def close(self):
        self.p.stdin.close()
        self.p.wait(timeout=20)


def meta(version="2026-07-28", client=None, caps=True):
    m = {VERSION: version}
    if caps:
        m[CAPS] = {}
    if client:
        m[CLIENT] = client
    return {"_meta": m}


def empty(resp):
    """A ping result is empty apart from the server naming itself in _meta."""
    r = resp.get("result")
    return isinstance(r, dict) and {k: v for k, v in r.items() if k != "_meta"} == {}


def common(label, mk):
    s = mk()
    d = s.call("server/discover", meta())
    r = d.get("result", {})
    check(r.get("resultType") == "complete" and "2026-07-28" in r.get("supportedVersions", [])
          and "tools" in r.get("capabilities", {}), "%s: server/discover answers with the modern shape" % label)
    check(SERVER in r.get("_meta", {}), "%s: discover names the server in _meta" % label)
    t = s.call("tools/list", meta())
    check(len(t.get("result", {}).get("tools", [])) >= 1 and SERVER in t["result"].get("_meta", {}),
          "%s: a modern request works with NO handshake, and the answer names the server" % label)
    bad = s.call("tools/list", meta(caps=False))
    check(bad.get("error", {}).get("code") == -32602, "%s: a missing required _meta field is -32602" % label)
    old = s.call("tools/list", meta(version="1900-01-01"))
    e = old.get("error", {})
    check(e.get("code") == -32022 and "2026-07-28" in e.get("data", {}).get("supported", [])
          and e["data"].get("requested") == "1900-01-01",
          "%s: an unsupported version is -32022 with the supported list" % label)
    check(empty(s.call("ping", meta())), "%s: ping" % label)
    ini = s.call("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                "clientInfo": {"name": "old", "version": "1"}})
    check("serverInfo" in ini.get("result", {}), "%s: a legacy client can still initialize" % label)
    check(len(s.call("tools/list").get("result", {}).get("tools", [])) >= 1,
          "%s: and a legacy request with no _meta still works" % label)
    check(s.raw("[1, 2]").get("error", {}).get("code") == -32600, "%s: a non-object request is -32600" % label)
    check(s.raw("not json").get("error", {}).get("code") == -32700, "%s: malformed JSON is -32700" % label)
    check(empty(s.call("ping", meta())), "%s: and it is still alive after both" % label)
    s.close()


def stamp(s, client, extra=None, **over):
    args = {"what": "answer", "amount": "1", "currency": "QUERY", "payee": "x",
            "rule": "r", "outcome": "ACCEPTED"}
    args.update(extra or {})
    return s.call("tools/call", dict(meta(client=client), name="kya_stamp", arguments=args))


def body(resp):
    return json.loads(resp["result"]["content"][0]["text"])


def agent_ref_checks(mk):
    s = mk()
    r = body(stamp(s, {"name": "ClaudeCode", "version": "2.1"}))
    check(r["receipt"].get("agent_ref") == "mcp-client:ClaudeCode/2.1",
          "package: with no agent_ref, the caller in THIS request's _meta is recorded, labelled mcp-client:")
    r2 = body(stamp(s, {"name": "Cursor", "version": "9"}))
    check(r2["receipt"].get("agent_ref") == "mcp-client:Cursor/9",
          "package: the next request's caller is recorded, not the previous one (stateless)")
    r3 = body(stamp(s, {"name": "Cursor", "version": "9"}, {"agent_ref": "did:web:agent.example#k1"}))
    check(r3["receipt"].get("agent_ref") == "did:web:agent.example#k1",
          "package: an explicit agent_ref wins over the client label")
    r4 = body(s.call("tools/call", {"name": "kya_stamp", "arguments": {
        "what": "a", "amount": "1", "currency": "QUERY", "payee": "x", "rule": "r", "outcome": "ACCEPTED"}}))
    check("agent_ref" not in r4["receipt"], "package: a legacy request with no caller records no agent_ref")
    long = stamp(s, None, {"agent_ref": "a" * 300})
    check(long["result"].get("isError") and "256" in long["result"]["content"][0]["text"],
          "package: an agent_ref over 256 characters is refused, not truncated")
    nonascii = stamp(s, None, {"agent_ref": "agent-é"})
    check(nonascii["result"].get("isError"), "package: a non-ASCII agent_ref is refused (SPEC 5)")
    notstr = stamp(s, None, {"agent_ref": 42})
    check(notstr["result"].get("isError"), "package: a non-string agent_ref is refused")
    path = os.path.join(s.cwd, "receipts.json")
    s.close()
    v = subprocess.run([sys.executable, "-m", "knowyouragenticai_receipts", "verify", path],
                       capture_output=True, text=True, cwd=s.cwd, env=ENV)
    check(v.returncode == 0, "package: a chain carrying agent_ref verifies with the published verifier")
    data = json.load(open(path))
    data[1]["agent_ref"] = "did:web:someone-else"
    json.dump(data, open(path, "w"))
    v = subprocess.run([sys.executable, "-m", "knowyouragenticai_receipts", "verify", path],
                       capture_output=True, text=True, cwd=s.cwd, env=ENV)
    check(v.returncode == 1, "package: changing an agent_ref afterwards breaks the chain")


ENV = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "pkg", "src"))


def main():
    print("MCP servers, modern and legacy")
    package = lambda: Server([sys.executable, "-m", "knowyouragenticai_receipts", "mcp"], {"PYTHONPATH": ENV["PYTHONPATH"]})
    common("package", package)
    agent_ref_checks(package)
    others = {"wallet": ([sys.executable, os.path.join(ROOT, "step-4-mcp", "kya_mcp.py"), "--ephemeral"], {}),
              "guard review": ([sys.executable, os.path.join(ROOT, "step-4-mcp", "kya_check_mcp.py")], {})}
    for label, (argv, env) in others.items():
        common(label, lambda argv=argv, env=env: Server(argv, env))
    print("\n%s" % ("ALL GREEN" if not fails else "%d FAILED: %s" % (len(fails), fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
