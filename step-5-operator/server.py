#!/usr/bin/env python3
"""The operator's rail. A tiny local server so the phone screen is real.

Stdlib only, per THE-RULES.md. It exposes exactly four things, and it is
deliberately thin: every decision belongs to the ledger, and this process is
allowed to carry an answer, not to make one.

    python3 step-5-operator/server.py                offline, MockLedger
    python3 step-5-operator/server.py --devnet       real Canton DevNet
    python3 step-5-operator/server.py --devnet --move-coin

Then open http://localhost:8420 on the same machine, or on a phone using the
machine's LAN address. It binds localhost by default: this thing carries
payout authority and should not appear on a network by accident.
"""
import json, os, sys, time, http.server, socketserver, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "step-2-agent"))
from kya_chain import Chain, NonAsciiInReceipt

PORT = int(os.environ.get("KYA_PORT", "8420"))


class QuoteDesk:
    """Mirrors KyaQuote and PayoutBook. MOCKED, and it says so.

    The Daml is the rule; this is the same rule in Python so the screen works
    offline. Every refusal string below is the assertion text from the
    contract, so what the operator reads here is what Canton would say.
    """

    def __init__(self):
        self.approved = ["GTB 0123456789 / CHIDI OKAFOR",
                         "UBA 2233445566 / BLESSING ADEYEMI"]
        self.quotes = {}
        self.seq = 0

    def approve(self, account):
        if account and account not in self.approved:
            self.approved.append(account)
        return self.approved

    def issue(self, customer, rate, amount, payout_account, minutes=120):
        # PayoutBook.IssueQuote
        if payout_account not in self.approved:
            return {"error": "payout account has not been approved by the principal"}
        self.seq += 1
        ref = "KYA-%04d" % (7000 + self.seq)
        self.quotes[ref] = {"reference": ref, "customer": customer, "rate": rate,
                            "expectedAmount": amount, "payoutAccount": payout_account,
                            "expiresAt": time.time() + minutes * 60,
                            "settled": False, "abandoned": False}
        return self.quotes[ref]

    def fulfil(self, ref, amount, claimed_account):
        # Quote.Fulfil, assertion by assertion, in the same order.
        q = self.quotes.get(ref)
        if not q:
            return {"outcome": "REFUSED",
                    "rule": "deposit does not carry this quote's reference"}
        if q["settled"]:
            return {"outcome": "REFUSED",
                    "rule": "this quote has already been paid once"}
        if q["abandoned"]:
            return {"outcome": "REFUSED", "rule": "quote was abandoned"}
        if time.time() >= q["expiresAt"]:
            return {"outcome": "REFUSED", "rule": "quote expired"}
        if abs(float(amount) - q["expectedAmount"]) > 1e-9:
            return {"outcome": "REFUSED", "rule": "amount does not match the quote"}
        if claimed_account != q["payoutAccount"]:
            return {"outcome": "REFUSED",
                    "rule": "payout account does not match the account named in the quote"}
        q["settled"] = True
        return {"outcome": "PAID", "rule": "paid to the account named when the quote was issued",
                "quote": q}


class Rail:
    """One mandate, one chain, for the life of the process."""

    def __init__(self, argv):
        if "--devnet" in argv:
            from devnet_ledger import DevNetLedger
            self.ledger = DevNetLedger(move_coin="--move-coin" in argv)
        else:
            from agent import MockLedger
            self.ledger = MockLedger()
        self.chain = Chain()
        self.desk = QuoteDesk()
        self.cap = 5.0
        self.period_limit = None
        self.opened = False

    def open(self, cap, period_limit=None, period_seconds=None):
        self.ledger.open_mandate(cap=cap, period_limit=period_limit,
                                 period_seconds=period_seconds)
        self.cap, self.period_limit, self.opened = cap, period_limit, True
        return self.state()

    def state(self):
        spent = sum(float(r["amount"]) for r in self.chain.receipts
                    if r["outcome"] == "ACCEPTED")
        return {"open": self.opened, "cap": self.cap, "spent": spent,
                "remaining": max(self.cap - spent, 0.0),
                "period_limit": self.period_limit,
                "ledger": self.ledger.label,
                "recipients": [{"key": k, "name": self.ledger.name(k)}
                               for k in ("customer", "partner")],
                "receipts": self.chain.receipts,
                "approved": self.desk.approved,
                "quotes": sorted(self.desk.quotes.values(),
                                 key=lambda q: q["reference"], reverse=True)}

    def request(self, amount, payee, what):
        if not self.opened:
            return {"error": "no mandate is open"}
        outcome, rule = self.ledger.charge(amount, payee)
        try:
            r = self.chain.stamp(what, amount, self.ledger.name(payee), rule,
                                 outcome, "mandate signed by Principal + Operator",
                                 self.ledger.label, self.ledger.currency,
                                 self.ledger.instrument)
        except NonAsciiInReceipt as e:
            return {"error": "that note contains a character the receipt cannot "
                             "carry. Please rewrite it in plain text.",
                    "detail": str(e)}
        return {"outcome": outcome, "rule": rule, "receipt": r}

    def revoke(self):
        self.ledger.revoke()
        return self.state()


RAIL = None


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def log_message(self, fmt, *args):
        pass  # the page is the log

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            self.path = "/operator.html"
        if self.path == "/api/state":
            return self._json(RAIL.state())
        return super().do_GET()

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return self._json({"error": "bad request"}, 400)
        if self.path == "/api/open":
            pl = body.get("period_limit")
            return self._json(RAIL.open(
                float(body.get("cap", 5.0)),
                None if pl in (None, "") else float(pl),
                body.get("period_seconds") or None))
        if self.path == "/api/request":
            return self._json(RAIL.request(float(body.get("amount", 0)),
                                           body.get("payee", ""),
                                           body.get("what", "")))
        if self.path == "/api/revoke":
            return self._json(RAIL.revoke())
        if self.path == "/api/quote":
            return self._json(RAIL.desk.issue(
                body.get("customer", ""), float(body.get("rate", 0)),
                float(body.get("amount", 0)), body.get("payout_account", "")))
        if self.path == "/api/fulfil":
            res = RAIL.desk.fulfil(body.get("reference", ""),
                                   float(body.get("amount", 0)),
                                   body.get("claimed_account", ""))
            # A payout attempt is a receipt whether or not it was allowed.
            try:
                r = RAIL.chain.stamp(
                    body.get("what") or ("payout against " + body.get("reference", "")),
                    float(body.get("amount", 0)), body.get("claimed_account", "")[:60],
                    res["rule"], "ACCEPTED" if res["outcome"] == "PAID" else "REFUSED",
                    "quote issued by Principal + Operator", RAIL.ledger.label,
                    RAIL.ledger.currency, RAIL.ledger.instrument)
                res["receipt"] = r
            except NonAsciiInReceipt as e:
                res["error"] = str(e)
            return self._json(res)
        if self.path == "/api/approve":
            return self._json({"approved": RAIL.desk.approve(body.get("account", ""))})
        return self._json({"error": "unknown endpoint"}, 404)


def main(argv):
    global RAIL
    RAIL = Rail(argv)
    host = "0.0.0.0" if "--lan" in argv else "127.0.0.1"
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((host, PORT), Handler) as httpd:
        print("operator rail on http://%s:%d" % (
            "localhost" if host == "127.0.0.1" else host, PORT))
        print("ledger:", RAIL.ledger.label)
        if host == "0.0.0.0":
            print("WARNING: bound to the LAN. This screen carries payout "
                  "authority; do not leave it running on an open network.")
        httpd.serve_forever()


if __name__ == "__main__":
    main(sys.argv[1:])
