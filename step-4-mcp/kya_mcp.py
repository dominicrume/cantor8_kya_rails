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

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in ("step-2-agent", "step-8-store"):
    sys.path.insert(0, os.path.join(HERE, "..", _p))
from kya_chain import Chain, NonAsciiInReceipt
from store import Store, Tampered, Unusable

PROTOCOL = "2024-11-05"
SERVER = {"name": "kya-rails", "version": "1.0.0"}

# stdout carries the protocol. Anything we want to say goes to stderr.
def log(msg):
    print("[kya] " + msg, file=sys.stderr, flush=True)


class Wallet:
    """One mandate and one receipt chain, written through to a journal.

    "For the life of the process" is what this used to say, and it was the
    honest description of a real gap. The chain lived in memory: a crash, a
    kill, or a client that hung up took every receipt with it -- including,
    and this is the part that matters, the refusals. An audit trail that
    disappears when the thing being audited falls over is not an audit trail.

    It also reset the cap. `spent` lived in the same memory, so a process that
    died came back with the whole float available again: a cap reset obtained
    by crashing rather than by asking the owner.

    Both are fixed the same way the operator rail fixes them -- write through
    to the seal-chained journal, restore from it on the way up.
    """

    def __init__(self, devnet=False, store=None):
        if devnet:
            from devnet_ledger import DevNetLedger
            self.ledger = DevNetLedger()
        else:
            from agent import MockLedger
            self.ledger = MockLedger()
        self.chain = Chain()
        self.open = False
        self.store = store
        self._written = 0
        if store is not None:
            self.resume()

    # -- keeping it ---------------------------------------------------------
    def _state(self):
        return {"open": self.open, "ledger": self.ledger.label,
                "mandate": self.ledger.snapshot()}

    def persist(self):
        """Called after every tool call, from one place.

        One choke point rather than a line in each method: a persistence layer
        you have to remember to invoke is one you will forget to invoke on
        exactly the path that mattered. The operator rail says the same thing
        for the same reason.
        """
        if self.store is None:
            return
        for receipt in self.chain.receipts[self._written:]:
            self.store.receipt(receipt)
        self._written = len(self.chain.receipts)
        self.store.snapshot(self._state())

    def resume(self):
        """Bring back the chain and the mandate. Returns receipts recovered."""
        state, _messages, receipts = self.store.restore()
        # Chain.stamp derives both `n` and `prev` from this list, so restoring
        # it is enough for the next receipt to follow the last one written --
        # across a restart, in the same unbroken chain.
        self.chain.receipts = list(receipts)
        self._written = len(receipts)
        mandate = (state or {}).get("mandate")
        if mandate:
            self.ledger.resume(mandate)
            self.open = state.get("open", False)
        return len(receipts)

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
        wallet.persist()
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


# The JSON-RPC 2.0 codes, used as specified. A client that is told it sent
# malformed JSON can fix it; a client given silence cannot, and just waits.
PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INTERNAL_ERROR = (
    -32700, -32600, -32601, -32603)


def _error(mid, code, message):
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


def handle(msg, wallet):
    """Returns a response dict, or None for a notification.

    Anything at all can arrive on stdin, so nothing here assumes a shape it
    has not checked. `msg.get(...)` on a JSON list raised AttributeError and
    took the whole server down with it.
    """
    if not isinstance(msg, dict):
        return _error(None, INVALID_REQUEST, "a JSON-RPC request must be an "
                      "object, not %s" % type(msg).__name__)
    method, mid = msg.get("method"), msg.get("id")
    if not isinstance(mid, (str, int, float, type(None))):
        return _error(None, INVALID_REQUEST, "id must be a string, a number or null")
    if not isinstance(method, str):
        # `method in METHODS` on a list raises TypeError: unhashable type.
        return _error(mid, INVALID_REQUEST, "method must be a string, not %s"
                      % type(method).__name__)
    if method in METHODS:
        fn = METHODS[method]
        return fn(msg, wallet, mid) if fn else None
    if mid is None:
        return None
    return _error(mid, METHOD_NOT_FOUND, "method not found: %s" % method)


def answer(line, wallet):
    """One line in, one response (or None) out. This never raises.

    It is the model's only route to the wallet, and the receipt chain lives in
    this process's memory. A single malformed line used to end both: a JSON
    list where an object was expected killed handle(), the loop, and the
    server. The model got silence, its pending request was never answered, and
    every receipt stamped so far went with it.
    """
    try:
        msg = json.loads(line)
    except json.JSONDecodeError as e:
        return _error(None, PARSE_ERROR, "could not parse that line as JSON: %s" % e.msg)
    try:
        return handle(msg, wallet)
    except Exception as e:                   # noqa: BLE001 - the boundary
        # The detail goes to the log, where an operator reads it. The model
        # gets told it failed, not how, and the server stays up.
        log("UNHANDLED %s: %s" % (type(e).__name__, e))
        mid = msg.get("id") if isinstance(msg, dict) else None
        return _error(mid, INTERNAL_ERROR, "the wallet could not process that request")


def build_store(argv):
    """Persistent unless --ephemeral, the same way round as the operator rail:
    the safe mode is the default and the dangerous one takes a flag."""
    if "--ephemeral" in argv:
        return None
    # Its OWN journal, never the desk's. Two processes each hold a Journal
    # that caches the last row number in memory, so both would compute the
    # same next `n` and the second INSERT would collide with the primary key.
    # Loud rather than silent, but still a broken session.
    path = os.environ.get("KYA_MCP_STORE") or os.path.join(HERE, "..", "kya-mcp.db")
    return Store(path)


def announce(wallet, store):
    """The first thing an operator reads. It has to say whether the receipts
    from before are back, because that is the only question worth asking of a
    wallet that has just restarted."""
    if store is None:
        log("EPHEMERAL: no journal. Receipts die with this process.")
        return
    log("journal: %d receipt(s) recovered, chain %s"
        % (len(wallet.chain.receipts),
           "verifies" if wallet.chain.verify()[0] else "IS BROKEN"))


def main(argv):
    # Nothing here may print to stdout: that is the protocol channel, and a
    # stray line of English in it corrupts the session it is trying to warn
    # about. Every word below goes to stderr through log().
    try:
        store = build_store(argv)
    except Tampered as e:
        log("REFUSING TO START. " + str(e))
        log("  This journal is the wallet's audit trail. Investigate it before")
        log("  running anything: python3 tests/store_check.py <path>")
        return 3
    except Unusable as e:
        log("CANNOT START: nowhere to keep the record. " + str(e))
        log("  Or run with --ephemeral to work without one -- nothing will")
        log("  survive the process, which is a real choice, not a workaround.")
        return 4

    wallet = Wallet(devnet="--devnet" in argv, store=store)
    announce(wallet, store)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        resp = answer(line, wallet)
        if resp is None:
            continue                          # a notification; nothing to say
        try:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except BrokenPipeError:
            # The client hung up. That is how these sessions end, not a fault.
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
