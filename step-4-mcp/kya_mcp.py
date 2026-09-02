#!/usr/bin/env python3
"""KYA Rails MCP server: hand a language model a float it cannot overspend.

This is the operator problem. A business whose principal is in one country and
whose payouts happen in another needs someone on the ground who can transact --
and cannot be given unbounded authority over the float. Here that operator is a
language model, which makes the point sharply: models can be talked into things.

The model gets tools to open a mandate and to attempt payouts. It does NOT get
a tool to raise its own cap, and it cannot talk its way past one -- the limits
are assertions in a Daml choice body, and the ledger answers, not this file.
Every attempt is sealed into a receipt chain, refusals included, so what the
operator TRIED is as auditable as what it managed to do.

    claude mcp add kya -- python3 /path/to/step-4-mcp/kya_mcp.py
    claude mcp add kya -- python3 /path/to/step-4-mcp/kya_mcp.py --devnet

Then ask the model to settle a trade, and then ask it to overspend.

JSON-RPC 2.0 over stdio. Stdlib only, per THE-RULES.md: no pip install, and no
MCP SDK. The protocol is small enough to implement honestly.
"""
import json, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "step-2-agent"))
from kya_chain import Chain, NonAsciiInReceipt

PROTOCOL = "2024-11-05"
SERVER = {"name": "kya-rails", "version": "1.0.0"}

# stdout carries the protocol. Anything we want to say goes to stderr.
def log(msg):
    print("[kya] " + msg, file=sys.stderr, flush=True)


class Wallet:
    """One mandate, one receipt chain, for the life of the process."""

    def __init__(self, devnet=False):
        if devnet:
            from devnet_ledger import DevNetLedger
            self.ledger = DevNetLedger()
        else:
            from agent import MockLedger
            self.ledger = MockLedger()
        self.chain = Chain()
        self.open = False

    def open_mandate(self, cap, allowed, life_seconds,
                     period_limit=None, period_seconds=None):
        self.ledger.open_mandate(cap=cap, life_seconds=life_seconds,
                                 period_limit=period_limit,
                                 period_seconds=period_seconds)
        self.open = True
        return {"cap": cap, "allowed": allowed, "ledger": self.ledger.label}

    def charge(self, amount, payee, what):
        if not self.open:
            return {"error": "no mandate is open. Call open_mandate first."}
        outcome, rule = self.ledger.charge(amount, payee)
        r = self.chain.stamp(what, amount, self.ledger.name(payee), rule, outcome,
                             "mandate signed by Principal + Operator",
                             self.ledger.label, self.ledger.currency,
                             self.ledger.instrument)
        return {"outcome": outcome, "rule": rule, "receipt": r["n"],
                "seal": r["seal"], "ledger": self.ledger.label}

    def revoke(self):
        self.ledger.revoke()
        return {"revoked": True}

    def statement(self):
        ok, bad = self.chain.verify()
        return {"receipts": self.chain.receipts, "chain_verifies": ok,
                "first_broken": bad,
                "accepted": sum(1 for r in self.chain.receipts if r["outcome"] == "ACCEPTED"),
                "refused": sum(1 for r in self.chain.receipts if r["outcome"] == "REFUSED")}


TOOLS = [
    {"name": "open_mandate",
     "description": "Open a spending mandate on the ledger. The cap, the "
                    "allow-list and the expiry become rules the ledger "
                    "enforces; they cannot be changed from here afterwards.",
     "inputSchema": {"type": "object", "properties": {
         "cap": {"type": "number", "description": "total the agent may ever spend"},
         "allowed": {"type": "array", "items": {"type": "string"},
                     "description": "roles that may be paid: customer, partner"},
         "life_seconds": {"type": "integer",
                          "description": "seconds until expiry; negative for an "
                                         "already-expired mandate, to demonstrate the fence"},
         "period_limit": {"type": "number",
                          "description": "optional: most that may be spent inside any "
                                         "one window, on top of the total cap"},
         "period_seconds": {"type": "integer",
                            "description": "optional: length of that window in seconds"}},
         "required": ["cap"]}},

    {"name": "charge",
     "description": "Attempt a payout under the open mandate. This is an "
                    "ATTEMPT, not an instruction: the ledger decides, and a "
                    "refusal is recorded as a sealed receipt exactly like an "
                    "acceptance. There is no way to make a refused payout succeed, "
                    "including by explaining why it should be allowed.",
     "inputSchema": {"type": "object", "properties": {
         "amount": {"type": "number"},
         "payee": {"type": "string",
                   "description": "customer, partner, or unverified"},
         "what": {"type": "string", "description": "why this payment is being made"}},
         "required": ["amount", "payee", "what"]}},

    {"name": "revoke_mandate",
     "description": "The principal revokes the mandate, from wherever they "
                    "are. Immediate, and the operator cannot block or delay it.",
     "inputSchema": {"type": "object", "properties": {}}},

    {"name": "get_statement",
     "description": "The full receipt chain: every attempt, accepted and "
                    "refused, with the rule that decided it and the seal over "
                    "the previous receipt. Verifies the chain end to end.",
     "inputSchema": {"type": "object", "properties": {}}},
]


def call_tool(wallet, name, args):
    if name == "open_mandate":
        pl = args.get("period_limit")
        return wallet.open_mandate(
            float(args.get("cap", 5.0)),
            args.get("allowed", ["customer", "partner"]),
            int(args.get("life_seconds", 86400)),
            None if pl is None else float(pl),
            args.get("period_seconds"))
    if name == "charge":
        return wallet.charge(float(args["amount"]), args["payee"],
                             args.get("what", "unspecified"))
    if name == "revoke_mandate":
        return wallet.revoke()
    if name == "get_statement":
        return wallet.statement()
    raise ValueError("unknown tool: %s" % name)


def _initialize(msg, wallet, mid):
    want = (msg.get("params") or {}).get("protocolVersion", PROTOCOL)
    return {"jsonrpc": "2.0", "id": mid, "result": {
        "protocolVersion": want if want == PROTOCOL else PROTOCOL,
        "capabilities": {"tools": {}},
        "serverInfo": SERVER}}


def _tools_list(msg, wallet, mid):
    return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}


def _tools_call(msg, wallet, mid):
    p = msg.get("params") or {}
    try:
        out = call_tool(wallet, p.get("name"), p.get("arguments") or {})
        text, is_error = json.dumps(out, indent=2), False
    except NonAsciiInReceipt as e:
        # The seal guard. Surfaced as a tool error so the model can fix its own
        # text rather than the chain being poisoned.
        text, is_error = "refused before sealing: %s" % e, True
    except Exception as e:
        text, is_error = "%s: %s" % (type(e).__name__, e), True
    return {"jsonrpc": "2.0", "id": mid,
            "result": {"content": [{"type": "text", "text": text}],
                       "isError": is_error}}


# method -> handler. Notifications map to None: nothing to answer.
METHODS = {
    "initialize": _initialize,
    "tools/list": _tools_list,
    "tools/call": _tools_call,
    "notifications/initialized": None,
    "notifications/cancelled": None,
}


def handle(msg, wallet):
    """Returns a response dict, or None for a notification."""
    method, mid = msg.get("method"), msg.get("id")
    if method in METHODS:
        fn = METHODS[method]
        return fn(msg, wallet, mid) if fn else None
    if mid is None:
        return None
    return {"jsonrpc": "2.0", "id": mid,
            "error": {"code": -32601, "message": "method not found: %s" % method}}


def main(argv):
    wallet = Wallet(devnet="--devnet" in argv)
    log("ready, ledger = " + wallet.ledger.label)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle(msg, wallet)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main(sys.argv[1:])
