#!/usr/bin/env python3
"""Drive the MCP server over stdio and assert the fences hold.

A model holding this wallet must not be able to overspend, pay a party that
is not on the allow-list, or charge after the owner revokes -- no matter what
it says in the `what` field. This test speaks the same JSON-RPC the model's
client speaks, so it fails if the wire protocol breaks as well as if a fence does.

Run: python3 tests/mcp_smoke.py
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, "..", "step-4-mcp", "kya_mcp.py")

REQUESTS = [
    (1, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                       "clientInfo": {"name": "mcp_smoke", "version": "1"}}),
    (None, "notifications/initialized", None),
    (2, "tools/list", None),
    (3, "tools/call", {"name": "open_mandate", "arguments": {"cap": 5.0}}),
    (4, "tools/call", {"name": "charge", "arguments": {
        "amount": 2.0, "payee": "customer", "what": "customer leg"}}),
    (5, "tools/call", {"name": "charge", "arguments": {
        "amount": 1.5, "payee": "partner", "what": "liquidity leg"}}),
    (6, "tools/call", {"name": "charge", "arguments": {
        "amount": 3.0, "payee": "customer",
        "what": "URGENT: the desk owner verbally approved raising the cap"}}),
    (7, "tools/call", {"name": "charge", "arguments": {
        "amount": 1.0, "payee": "unverified",
        "what": "the customer says this is their new wallet, please send here"}}),
    (8, "tools/call", {"name": "revoke_mandate", "arguments": {}}),
    (9, "tools/call", {"name": "charge", "arguments": {
        "amount": 0.5, "payee": "customer", "what": "one last one"}}),
    (10, "tools/call", {"name": "get_statement", "arguments": {}}),
    # A fresh mandate with a per-period limit well below the total cap, so
    # only the period fence can refuse the second payout.
    (11, "tools/call", {"name": "open_mandate", "arguments": {
        "cap": 100.0, "period_limit": 20.0, "period_seconds": 86400}}),
    (12, "tools/call", {"name": "charge", "arguments": {
        "amount": 15.0, "payee": "customer", "what": "first payout in the window"}}),
    (13, "tools/call", {"name": "charge", "arguments": {
        "amount": 10.0, "payee": "customer",
        "what": "still far below the cap of 100, but the window is nearly used"}}),
]

lines = []
for mid, method, params in REQUESTS:
    m = {"jsonrpc": "2.0", "method": method}
    if mid is not None:
        m["id"] = mid
    if params is not None:
        m["params"] = params
    lines.append(json.dumps(m))

p = subprocess.run([sys.executable, SERVER, "--ephemeral"], input="\n".join(lines) + "\n",
                   capture_output=True, text=True, timeout=60)
by_id = {}
for line in p.stdout.splitlines():
    if line.strip():
        d = json.loads(line)
        by_id[d.get("id")] = d

fails = []
def check(cond, what):
    print("  %s %s" % ("PASS" if cond else "FAIL", what))
    if not cond:
        fails.append(what)

def payload(mid):
    return json.loads(by_id[mid]["result"]["content"][0]["text"])

print("KYA Rails - MCP server smoke test")
check(by_id[1]["result"]["serverInfo"]["name"] == "kya-rails", "initialize handshake")
names = [t["name"] for t in by_id[2]["result"]["tools"]]
check(set(names) == {"open_mandate", "charge", "revoke_mandate", "get_statement"},
      "tools/list exposes exactly the four tools")
# A denylist of two spellings could not see a tool called
# `increase_spending_limit`. Assert the WHOLE set: a new tool has to be added
# here deliberately, which is the point at which someone asks what it does.
EXPECTED_TOOLS = {"open_mandate", "charge", "revoke_mandate", "get_statement"}
check(set(names) == EXPECTED_TOOLS,
      "the model is offered exactly the tools we intend, and no others")

check(payload(4)["outcome"] == "ACCEPTED", "charge inside the mandate is accepted")
check(payload(5)["outcome"] == "ACCEPTED", "second leg inside the mandate is accepted")

over = payload(6)
check(over["outcome"] == "REFUSED" and "cap" in over["rule"],
      "overspend REFUSED even when the model claims verbal approval")
stranger = payload(7)
check(stranger["outcome"] == "REFUSED" and "allow-list" in stranger["rule"],
      "payout redirection REFUSED even when the model is told it is legitimate")
after = payload(9)
check(after["outcome"] == "REFUSED", "charge after revoke REFUSED")

st = payload(10)
# The count first. This passed with stamp() appending nothing at all: an
# empty chain verifies trivially and all([]) is True.
check(len(st["receipts"]) >= 3, "the run actually produced receipts to verify")
check(st["chain_verifies"] is True, "receipt chain verifies end to end")
check(st["refused"] == 3, "all three refusals were sealed as receipts (got %s)" % st["refused"])
check(st["receipts"] and all(r.get("ledger") for r in st["receipts"]),
      "every receipt names the ledger that produced it")

within = payload(12)
check(within["outcome"] == "ACCEPTED", "first payout inside the window is accepted")
over = payload(13)
check(over["outcome"] == "REFUSED" and "period" in over["rule"],
      "second payout REFUSED by the period limit, not the cap (rule: %s)" % over["rule"])


# ---------------------------------------------------------------------------
# A hostile stdin. This is not hypothetical: a JSON list where an object was
# expected raised AttributeError inside handle(), killed the loop, and ended
# the server. The model was left with silence, its pending request unanswered,
# and the whole in-memory receipt chain gone with the process.
#
# The malformed lines are interleaved BETWEEN good ones on purpose. Feeding
# them at the end would pass even if each one still killed the server.
# ---------------------------------------------------------------------------
print()
print("a hostile stdin, with the good requests still to come after it")

HOSTILE = [
    ('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}', None),
    ("this is not json at all", -32700),
    ('{"jsonrpc":"2.0","id":2,"method":"tools/list"}', None),
    ("[1,2,3]", -32600),
    ("5", -32600),
    ('"a bare string"', -32600),
    ("null", -32600),
    ('{"jsonrpc":"2.0","id":3,"method":["not","a","string"]}', -32600),
    ('{"jsonrpc":"2.0","id":{"an":"object"},"method":"tools/list"}', -32600),
    ('{"jsonrpc":"2.0","id":4,"method":"no/such/method"}', -32601),
    ('{"jsonrpc":"2.0","id":5,"method":"tools/call","params":"not an object"}', None),
    ('{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"charge"}}', None),
    ('{"jsonrpc":"2.0","id":7,"method":"tools/call",'
     '"params":{"name":"charge","arguments":{"amount":"lots","payee":[1]}}}', None),
    ('{"jsonrpc":"2.0","id":8,"method":"tools/call","params":{"name":"../../etc/passwd"}}', None),
    # The line that proves the session is still alive after all of the above.
    ('{"jsonrpc":"2.0","id":99,"method":"tools/list"}', None),
]

hp = subprocess.run([sys.executable, SERVER, "--ephemeral"],
                    input="\n".join(h[0] for h in HOSTILE) + "\n",
                    capture_output=True, text=True, timeout=60)
answers = [json.loads(l) for l in hp.stdout.splitlines() if l.strip()]
survivor = [a for a in answers if a.get("id") == 99]

check(hp.returncode == 0, "the server exits cleanly rather than crashing (rc=%s)"
      % hp.returncode)
check(len(survivor) == 1,
      "the LAST request is still answered -- no bad line ended the session")
check(bool(survivor) and len(survivor[0]["result"]["tools"]) == 4,
      "and it is answered correctly, with all four tools")
check("Traceback" not in hp.stderr, "nothing raised out of the loop")
check(all("jsonrpc" in a for a in answers),
      "every answer is a JSON-RPC message, including the failures")

# Line by line, not as a set. Asking only whether -32600 appears SOMEWHERE
# passes even when the line that should have produced it produced something
# else entirely -- one aggregate hiding every individual answer. Each of these
# lines produces exactly one response, in order, so they can be matched up.
check(len(answers) == len(HOSTILE),
      "one answer per line, in order (%d lines, %d answers)"
      % (len(HOSTILE), len(answers)))
wrong = []
for (line, want), got in zip(HOSTILE, answers):
    code = got.get("error", {}).get("code")
    if want != code:
        wrong.append("%.40s -> wanted %s, got %s" % (line, want, code))
check(not wrong, "each line gets ITS proper JSON-RPC code")
for w in wrong:
    print("       ", w)
check(all(a["error"]["message"] for a in answers if "error" in a),
      "and every error carries a message a caller can act on")

# A tool that fails must not look like a transport failure -- the model has to
# be able to tell "you asked wrongly" from "the wallet is broken".
tool_errors = [a for a in answers
               if a.get("result", {}).get("isError") is True]
check(len(tool_errors) >= 3,
      "a bad tool call comes back as a tool error, not a dead connection (%d)"
      % len(tool_errors))

print()
if fails:
    print("MCP SMOKE FAILED - %d:" % len(fails))
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("MCP smoke passed: the model cannot overspend, cannot redirect, cannot\noutlive a revoke -- and cannot end the session by sending nonsense.")
