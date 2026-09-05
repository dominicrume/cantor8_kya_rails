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

p = subprocess.run([sys.executable, SERVER], input="\n".join(lines) + "\n",
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

print()
if fails:
    print("MCP SMOKE FAILED - %d:" % len(fails))
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("MCP smoke passed: the model cannot overspend, cannot redirect, cannot outlive a revoke.")
