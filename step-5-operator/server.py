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
import hmac, json, os, secrets, sys, time, http.server, socketserver, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "step-2-agent"))
sys.path.insert(0, os.path.join(HERE, "..", "step-6-whatsapp"))
sys.path.insert(0, os.path.join(HERE, "..", "step-7-providers"))
sys.path.insert(0, os.path.join(HERE, "..", "step-8-store"))
from kya_chain import Chain, NonAsciiInReceipt
from bot import Conversation, GREETING
from meta import MetaAdapter, MAX_BODY
from breet import BreetAdapter
from store import Store, Tampered

# Meta's webhook, if and only if it is fully configured. A half-configured
# webhook endpoint is an open one, so all three values must be present or the
# path does not exist at all. None of them belong in this file: they live in
# the shell, like every other secret in this repository.
META = None
META_PATH = "/webhook/meta"


# Breet's deposit webhook. Same rule as Meta's: it exists only when it is
# configured, because an endpoint that confirms deposits causes payouts.
BREET = None
BREET_PATH = "/webhook/breet"
BREET_TRUST_PROXY = False


def build_store(argv):
    """Persistent unless --ephemeral.

    The safe mode is the default and the dangerous one takes a flag. Nobody
    loses a payout binding because they forgot to type --store.
    """
    if "--ephemeral" in argv:
        return None
    path = os.environ.get("KYA_STORE") or os.path.join(HERE, "..", "kya-desk.db")
    return Store(path)


def build_breet(rail):
    """Breet authenticates with a shared header secret and an IP allowlist.

    KYA_BREET_REQUIRE_IP=0 turns the allowlist off. That is for running the
    demo on a laptop, where nothing arrives from a provider IP, and it leaves
    a bearer token in a header as the only check -- so it announces itself on
    the startup banner rather than being a quiet default.
    """
    global BREET_TRUST_PROXY
    secret = os.environ.get("KYA_BREET_SECRET")
    if not secret:
        return None
    BREET_TRUST_PROXY = os.environ.get("KYA_BREET_TRUST_PROXY") == "1"
    require_ip = os.environ.get("KYA_BREET_REQUIRE_IP", "1") != "0"
    return BreetAdapter(rail.cycle, secret, require_ip=require_ip)


def build_meta(rail):
    secret = os.environ.get("KYA_META_APP_SECRET")
    token = os.environ.get("KYA_META_VERIFY_TOKEN")
    phone_id = os.environ.get("KYA_META_PHONE_ID")
    if not (secret and token and phone_id):
        return None
    return MetaAdapter(rail, secret, token, phone_id)

PORT = int(os.environ.get("KYA_PORT", "8420"))

# Set only when bound off the loopback. None means localhost-only, no token.
LAN_TOKEN = None


class CycleDesk:
    """The whole OTC cycle, mirroring KyaCycle.daml. MOCKED, and it says so.

    A deal is one object moving through states, because that is how the desk
    actually thinks about it -- not as four contracts to be joined by hand at
    2am. Every refusal string is the assertion text from the Daml.
    """

    # (asset, network, address, memo_required) -- approved by the principal
    ADDRESSES = [
        ("USDT", "TRC20", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t", False),
        ("USDT", "ERC20", "0x8f3aE9dB1B7B2f5F3aE44D9B3F1c8bA2E4d5C6f7", False),
        ("BTC",  "BITCOIN", "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq", False),
        ("XRP",  "XRPL",  "rEb8TK3gBgk5auZkwc6sHnwrGVJH8DuaLh", True),
    ]
    OFFTAKERS = [("Supplier A", "USDT", "TRC20", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")]

    def __init__(self):
        self.deals = {}
        self.seq = 0

    def networks(self):
        return [{"asset": a, "network": n, "memo_required": m}
                for a, n, _, m in self.ADDRESSES]

    def offtakers(self):
        return [{"offtaker": o, "asset": a, "network": n, "address": w}
                for o, a, n, w in self.OFFTAKERS]

    def open_deal(self, customer, asset, network, amount, rate, payout_account,
                  memo=None, approved_accounts=()):
        # PayoutBook.IssueQuote
        if payout_account not in approved_accounts:
            return {"error": "payout account has not been approved by the principal"}
        # DepositBook.IssueDepositInstruction
        match = [(addr, needs) for a, n, addr, needs in self.ADDRESSES
                 if a == asset and n == network]
        if not match:
            return {"error": "no approved address for that asset on that network"}
        address, needs_memo = match[0]
        if needs_memo and not memo:
            return {"error": "this network requires a memo or tag and none was given"}
        self.seq += 1
        ref = "KYA-%04d" % (7000 + self.seq)
        d = {"reference": ref, "customer": customer, "asset": asset,
             "network": network, "amount": amount, "rate": rate,
             "naira": round(amount * rate, 2), "payoutAccount": payout_account,
             "depositAddress": address, "memo": memo,
             "state": "QUOTED", "offtaker": None, "nairaReceived": False,
             "opened": time.time(), "expiresAt": time.time() + 7200}
        self.deals[ref] = d
        return d

    def confirm_deposit(self, ref):
        d = self.deals.get(ref)
        if not d:
            return {"error": "no such deal"}
        if d["state"] != "QUOTED":
            return {"error": "deposit already confirmed for this deal"}
        d["state"] = "DEPOSITED"
        return d

    def send_to_offtaker(self, ref, offtaker, address):
        # OffTakerBook.SendToOffTaker
        d = self.deals.get(ref)
        if not d:
            return {"error": "no such deal"}
        if d["state"] != "DEPOSITED":
            return {"outcome": "REFUSED",
                    "rule": "the customer's deposit has not been confirmed yet"}
        if (offtaker, d["asset"], d["network"], address) not in self.OFFTAKERS:
            return {"outcome": "REFUSED",
                    "rule": "off-taker wallet is not approved for that asset and network"}
        d["state"] = "WITH_OFFTAKER"
        d["offtaker"] = {"name": offtaker, "address": address}
        return {"outcome": "SENT", "rule": "sent to an approved off-taker wallet", "deal": d}

    def confirm_naira(self, ref, received):
        # SupplyLeg.ConfirmNairaReceived
        d = self.deals.get(ref)
        if not d or d["state"] != "WITH_OFFTAKER":
            return {"outcome": "REFUSED", "rule": "no supply leg awaiting naira"}
        if float(received) < d["naira"]:
            return {"outcome": "REFUSED", "rule": "naira received is short of the amount agreed"}
        d["nairaReceived"] = True
        d["state"] = "FUNDED"
        return {"outcome": "RECEIVED", "rule": "naira received in full", "deal": d}

    def pay(self, ref, claimed_account, amount):
        # Quote.Fulfil
        d = self.deals.get(ref)
        if not d:
            return {"outcome": "REFUSED",
                    "rule": "deposit does not carry this quote's reference"}
        if d["state"] == "PAID":
            return {"outcome": "REFUSED", "rule": "this quote has already been paid once"}
        if d["state"] == "QUOTED":
            return {"outcome": "REFUSED",
                    "rule": "the customer's deposit has not been confirmed yet"}
        if d["state"] == "WITH_OFFTAKER":
            return {"outcome": "REFUSED",
                    "rule": "naira has not been received from the off-taker yet"}
        if time.time() >= d["expiresAt"]:
            return {"outcome": "REFUSED", "rule": "quote expired"}
        if abs(float(amount) - d["amount"]) > 1e-9:
            return {"outcome": "REFUSED", "rule": "amount does not match the quote"}
        if claimed_account != d["payoutAccount"]:
            return {"outcome": "REFUSED",
                    "rule": "payout account does not match the account named in the quote"}
        d["state"] = "PAID"
        return {"outcome": "PAID",
                "rule": "paid to the account named when the quote was issued", "deal": d}


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
    """One mandate, one chain. Persistent unless told otherwise.

    This class used to say "for the life of the process", and meant it: the
    payout account bound at 10:02 did not survive the laptop sleeping before
    the 13:20 deposit. Persistence is therefore the DEFAULT and --ephemeral is
    the flag, because forgetting a flag should not be able to cost money.
    """

    def __init__(self, argv, store=None):
        if "--devnet" in argv:
            from devnet_ledger import DevNetLedger
            self.ledger = DevNetLedger(move_coin="--move-coin" in argv)
        else:
            from agent import MockLedger
            self.ledger = MockLedger()
        self.chain = Chain()
        self.desk = QuoteDesk()
        self.cycle = CycleDesk()
        self.threads = {}          # wa_id -> Conversation
        self.transcript = []       # every message in and out, for the operator
        self.rate = 1250.0
        self.band = (1000.0, 1500.0)
        self.cap = 5.0
        self.period_limit = None
        self.opened = False
        self.store = store
        self._msgs = 0          # how much of the transcript is already on disk
        self._receipts = 0
        self.restored = self.reload()

    # -- persistence -------------------------------------------------------
    def desk_state(self):
        """Everything that must survive a restart, and nothing that must not.

        No secrets, no LAN token, no ledger handle: this file sits on a laptop
        and is copied around, so it holds the desk's working state and its
        audit trail only.
        """
        return {"deals": self.cycle.deals, "dealSeq": self.cycle.seq,
                "quotes": self.desk.quotes, "quoteSeq": self.desk.seq,
                "approved": self.desk.approved, "rate": self.rate,
                "band": list(self.band), "cap": self.cap,
                "periodLimit": self.period_limit, "opened": self.opened}

    def persist(self):
        """Called after anything that could have changed the desk.

        One choke point rather than a call in each handler: a persistence
        layer you have to remember to invoke is one you will forget to invoke
        on exactly the path that mattered.
        """
        if self.store is None:
            return
        for entry in self.transcript[self._msgs:]:
            self.store.message(entry)
        self._msgs = len(self.transcript)
        for receipt in self.chain.receipts[self._receipts:]:
            self.store.receipt(receipt)
        self._receipts = len(self.chain.receipts)
        self.store.snapshot(self.desk_state())

    def reload(self):
        """Bring back what was on disk. Returns the number of open deals."""
        if self.store is None:
            return 0
        state, messages, receipts = self.store.restore()
        self.transcript = list(messages)
        self.chain.receipts = list(receipts)
        self._msgs, self._receipts = len(messages), len(receipts)
        if state:
            self._apply(state)
        return len(self.cycle.deals)

    def _apply(self, state):
        self.cycle.deals = state.get("deals", {})
        self.cycle.seq = state.get("dealSeq", 0)
        self.desk.quotes = state.get("quotes", {})
        self.desk.seq = state.get("quoteSeq", 0)
        self.desk.approved = state.get("approved", self.desk.approved)
        self.rate = state.get("rate", self.rate)
        self.band = tuple(state.get("band", self.band))
        self.cap = state.get("cap", self.cap)
        self.period_limit = state.get("periodLimit")
        self.opened = state.get("opened", False)

    def thread(self, wa_id):
        if wa_id not in self.threads:
            self.threads[wa_id] = Conversation(
                wa_id, self.cycle, lambda: list(self.desk.approved))
        return self.threads[wa_id]

    def on_message(self, wa_id, text):
        """One inbound message. Returns what the bot says back.

        The bot never chooses the rate: it is handed the band the principal
        set, and reads from it. There is no path here that lets a message
        change a number.
        """
        self.transcript.append({"wa_id": wa_id, "dir": "in", "text": text})
        reply = self.thread(wa_id).handle(text, self.rate, self.band)
        self.transcript.append({"wa_id": wa_id, "dir": "out", "text": reply})
        return reply

    def open(self, cap, period_limit=None, period_seconds=None):
        self.ledger.open_mandate(cap=cap, period_limit=period_limit,
                                 period_seconds=period_seconds)
        self.cap, self.period_limit, self.opened = cap, period_limit, True
        return self.state()

    def storage_state(self):
        """What the operator needs to know before they trust this screen.

        Whether an open deal will still be here after the laptop sleeps is not
        a detail: it is the difference between a quote that binds a payout
        account and a sticky note. So it goes on the screen, not just in the
        terminal banner nobody is looking at.
        """
        if self.store is None:
            return {"mode": "EPHEMERAL", "intact": True, "restored": 0,
                    "warning": "Deals are NOT saved. Closing this server "
                               "loses every open deal and the receipt chain."}
        return {"mode": "SAVED", "intact": self.store.intact,
                "restored": self.restored,
                "entries": self.store.journal.n,
                "warning": "" if self.store.intact else
                           "The journal does not follow from itself. Do not "
                           "trust this record; check the ledger."}

    def state(self):
        spent = sum(float(r["amount"]) for r in self.chain.receipts
                    if r["outcome"] == "ACCEPTED")
        return {"open": self.opened, "cap": self.cap, "spent": spent,
                "remaining": max(self.cap - spent, 0.0),
                "period_limit": self.period_limit,
                "ledger": self.ledger.label,
                "storage": self.storage_state(),
                "recipients": [{"key": k, "name": self.ledger.name(k)}
                               for k in ("customer", "partner")],
                "receipts": self.chain.receipts,
                "approved": self.desk.approved,
                "quotes": sorted(self.desk.quotes.values(),
                                 key=lambda q: q["reference"], reverse=True),
                "networks": self.cycle.networks(),
                "offtakers": self.cycle.offtakers(),
                "deals": sorted(self.cycle.deals.values(),
                                key=lambda d: d["reference"], reverse=True),
                "rate": self.rate, "band": list(self.band),
                "transcript": self.transcript[-40:]}

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



# ---------------------------------------------------------------------------
# Routes. A dispatch table rather than an if/elif ladder: each endpoint is a
# named function that can be read, tested and found on its own, and adding one
# does not make the router harder to follow.
# ---------------------------------------------------------------------------

def r_open(body):
    pl = body.get("period_limit")
    return RAIL.open(float(body.get("cap", 5.0)),
                     None if pl in (None, "") else float(pl),
                     body.get("period_seconds") or None)


def r_request(body):
    return RAIL.request(float(body.get("amount", 0)), body.get("payee", ""),
                        body.get("what", ""))


def r_revoke(body):
    return RAIL.revoke()


def r_quote(body):
    return RAIL.desk.issue(body.get("customer", ""), float(body.get("rate", 0)),
                           float(body.get("amount", 0)), body.get("payout_account", ""))


def _stamp(res, body, authority="quote issued by Principal + Operator"):
    """A payout attempt is a receipt whether or not it was allowed."""
    try:
        res["receipt"] = RAIL.chain.stamp(
            body.get("what") or ("payout for " + body.get("reference", "")),
            float(body.get("amount", 0)), body.get("claimed_account", "")[:60],
            res["rule"], "ACCEPTED" if res["outcome"] in ("PAID",) else "REFUSED",
            authority, RAIL.ledger.label, RAIL.ledger.currency, RAIL.ledger.instrument)
    except NonAsciiInReceipt as e:
        res["error"] = str(e)
    return res


def r_fulfil(body):
    res = RAIL.desk.fulfil(body.get("reference", ""), float(body.get("amount", 0)),
                           body.get("claimed_account", ""))
    if res.get("outcome") == "PAID":
        res["outcome"] = "PAID"
    return _stamp(res, body)


def r_approve(body):
    return {"approved": RAIL.desk.approve(body.get("account", ""))}


def r_deal(body):
    return RAIL.cycle.open_deal(
        body.get("customer", ""), body.get("asset", ""), body.get("network", ""),
        float(body.get("amount", 0)), float(body.get("rate", 0)),
        body.get("payout_account", ""), body.get("memo") or None,
        RAIL.desk.approved)


def r_deposit_confirmed(body):
    return RAIL.cycle.confirm_deposit(body.get("reference", ""))


def r_offtaker(body):
    return RAIL.cycle.send_to_offtaker(body.get("reference", ""),
                                       body.get("offtaker", ""), body.get("address", ""))


def r_naira(body):
    return RAIL.cycle.confirm_naira(body.get("reference", ""),
                                    float(body.get("received", 0)))


def r_pay(body):
    return _stamp(RAIL.cycle.pay(body.get("reference", ""),
                                 body.get("claimed_account", ""),
                                 float(body.get("amount", 0))), body)


def r_wa(body):
    return {"reply": RAIL.on_message(body.get("from") or "sim", body.get("text", ""))}


def r_rate(body):
    r = float(body.get("rate", 0))
    lo, hi = RAIL.band
    if not (lo <= r <= hi):
        return {"error": "rate is outside the band %s-%s" % (lo, hi)}
    RAIL.rate = r
    return {"rate": r}


POST_ROUTES = {
    "/api/open": r_open, "/api/request": r_request, "/api/revoke": r_revoke,
    "/api/quote": r_quote, "/api/fulfil": r_fulfil, "/api/approve": r_approve,
    "/api/deal": r_deal, "/api/deposit-confirmed": r_deposit_confirmed,
    "/api/offtaker": r_offtaker, "/api/naira": r_naira, "/api/pay": r_pay,
    "/api/wa": r_wa, "/api/rate": r_rate,
}

# Static pages, and the short forms that survive being pasted into a chat.
GET_PAGES = {"/": "/operator.html", "/bot": "/bot.html", "/c": "/customer.html"}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def authorised(self):
        """No token required on loopback; required on everything else."""
        if LAN_TOKEN is None:
            return True
        got = (self.headers.get("X-KYA-Token")
               or urllib.parse.parse_qs(
                   urllib.parse.urlparse(self.path).query).get("t", [""])[0])
        return hmac.compare_digest(str(got), str(LAN_TOKEN))

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
        parsed = urllib.parse.urlparse(self.path)
        # Meta's verification GET carries no LAN token and cannot be given
        # one. It is answered only when it proves it knows the verify token.
        if parsed.path == META_PATH and META is not None:
            return self._meta_verify(parsed.query)
        if not self.authorised():
            return self._json({"error": "unauthorised"}, 401)
        path = parsed.path

        if path == "/api/state":
            return self._json(RAIL.state())
        if path == "/api/customer":
            return self._customer()
        if path.startswith("/c/"):
            return self._short_link(path[3:])
        self.path = GET_PAGES.get(path, self.path)
        return super().do_GET()

    def _customer(self):
        """The customer's view. Deliberately narrow: what they must do, what
        was agreed, where it is up to, and their receipt. Nothing about the
        desk's float, its other deals, its off-takers or its margin."""
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        ref = (q.get("ref") or [""])[0]
        d = RAIL.cycle.deals.get(ref)
        if not d:
            return self._json({"error": "no such deal"}, 404)
        receipt = next((r for r in reversed(RAIL.chain.receipts)
                        if ref in r["what"] and r["outcome"] == "ACCEPTED"), None)
        return self._json({
            "reference": d["reference"], "state": d["state"],
            "asset": d["asset"], "network": d["network"],
            "amount": d["amount"], "rate": d["rate"], "naira": d["naira"],
            "depositAddress": d["depositAddress"], "memo": d["memo"],
            "payoutAccount": d["payoutAccount"], "receipt": receipt})

    def _short_link(self, ref):
        """/c/KYA-7001 -- the shape that survives being pasted into WhatsApp."""
        body = ('<meta http-equiv="refresh" content="0;url=/customer.html?ref='
                + urllib.parse.quote(ref) + '">').encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _meta_verify(self, query):
        params = {k: v[0] for k, v in urllib.parse.parse_qs(query).items()}
        code, text = META.verify(params)
        payload = text.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _client_ip(self):
        """Who is really calling.

        `client_address` is the socket peer: the one thing a caller cannot
        forge. Behind a reverse proxy it is the proxy, and the real caller is
        the LAST entry of X-Forwarded-For -- the one that proxy appended.
        Everything to the left of it is whatever the caller sent and is worth
        nothing.

        Off unless KYA_BREET_TRUST_PROXY=1, because reading that header with
        no known proxy in front turns the provider's IP allowlist into a
        header anyone can set.
        """
        if BREET_TRUST_PROXY:
            forwarded = self.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.rsplit(",", 1)[-1].strip()
        return self.client_address[0]

    def _breet_post(self):
        """Breet signs nothing, so the body may be parsed before the check --
        but it is still authenticated before it is looked at. A body that does
        not parse becomes None, which the adapter refuses AFTER authenticating
        rather than before, so an unauthenticated caller learns nothing about
        what this endpoint expects."""
        n = int(self.headers.get("Content-Length", 0))
        if n > MAX_BODY:
            return self._json({"error": "body too large"}, 413)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            body = None
        code, out = BREET.handle(dict(self.headers), self._client_ip(), body)
        RAIL.persist()
        return self._json(out, code)

    def _meta_post(self):
        """The signature covers the bytes on the wire, so the bytes go
        through untouched: no parse, no re-encode, no LAN token."""
        n = int(self.headers.get("Content-Length", 0))
        if n > MAX_BODY:
            return self._json({"error": "body too large"}, 413)
        code, body = META.handle(dict(self.headers), self.rfile.read(n))
        RAIL.persist()
        return self._json(body, code)

    def _webhook(self):
        """The provider endpoint for this path, if one is configured.

        These are dispatched before the LAN token and before the JSON parse:
        a provider cannot be given our token, and each authenticates by its
        own scheme instead. An unconfigured provider has no endpoint at all,
        so this returns None and the request falls through to a 404.
        """
        if self.path == META_PATH and META is not None:
            return self._meta_post
        if self.path == BREET_PATH and BREET is not None:
            return self._breet_post
        return None

    def do_POST(self):
        hook = self._webhook()
        if hook is not None:
            return hook()
        if not self.authorised():
            return self._json({"error": "unauthorised"}, 401)
        n = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return self._json({"error": "bad request"}, 400)
        route = POST_ROUTES.get(self.path)
        if route is None:
            return self._json({"error": "unknown endpoint"}, 404)
        out = route(body)
        RAIL.persist()
        return self._json(out)


def print_store_status():
    if RAIL.store is None:
        print("Storage: EPHEMERAL (--ephemeral). Deals, conversations and the")
        print("         receipt chain are lost when this process stops.")
        return
    print("Storage: %s" % os.path.relpath(RAIL.store.journal.path))
    print("         restored %d open deal(s), %d message(s), %d receipt(s);"
          % (RAIL.restored, len(RAIL.transcript), len(RAIL.chain.receipts)))
    print("         journal verified: history has not been edited.")


def print_provider_status():
    """Say which doors are open, and what is only pretending to be one."""
    if META is None:
        print("WhatsApp: MOCKED only (/bot). The Meta webhook is OFF -- set")
        print("          KYA_META_APP_SECRET, KYA_META_VERIFY_TOKEN and")
        print("          KYA_META_PHONE_ID to turn it on.")
    else:
        print("WhatsApp: live webhook at %s (signature-checked)." % META_PATH)
        print("          Replies are MOCKED: nothing is sent back to Meta.")
    if BREET is None:
        print("Deposits: MOCKED only. The Breet webhook is OFF -- set")
        print("          KYA_BREET_SECRET to turn it on.")
        return
    print("Deposits: live webhook at %s." % BREET_PATH)
    if not BREET.require_ip:
        print("          IP ALLOWLIST OFF (KYA_BREET_REQUIRE_IP=0). A header")
        print("          secret is the only check. Local demo use only.")
    if BREET_TRUST_PROXY:
        print("          Trusting X-Forwarded-For. The IP check is now only")
        print("          as good as the proxy in front of this.")


def main(argv):
    global RAIL, LAN_TOKEN, META, BREET
    try:
        store = build_store(argv)
    except Tampered as e:
        print("REFUSING TO START.")
        print(" ", e)
        print("  The journal is the desk's audit trail. Investigate it before")
        print("  running anything: python3 tests/store_check.py <path>")
        sys.exit(3)
    RAIL = Rail(argv, store=store)
    META = build_meta(RAIL)
    BREET = build_breet(RAIL)

    # Localhost by default. --lan is how the operator opens this on a phone,
    # and it puts a payout interface on a network, so it is not a warning-level
    # decision: off the loopback, every request needs a token.
    #
    # A shared token over plain HTTP on a local network is modest protection.
    # It stops the other devices on the wifi, which is the realistic threat in
    # a shared office, and it is not a substitute for HTTPS on anything wider.
    host = "127.0.0.1"
    if "--lan" in argv:
        host = "0.0.0.0"                                   # nosec B104 - gated below
        LAN_TOKEN = os.environ.get("KYA_LAN_TOKEN") or secrets.token_urlsafe(18)

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((host, PORT), Handler) as httpd:
        if host == "127.0.0.1":
            print("operator rail on http://localhost:%d" % PORT)
        else:
            print("operator rail on http://<this machine>:%d" % PORT)
            print("")
            print("  Bound to the LAN. Every request needs this token:")
            print("      %s" % LAN_TOKEN)
            print("  Open:  http://<this machine>:%d/?t=%s" % (PORT, LAN_TOKEN))
            print("")
            print("  This screen carries payout authority. The token stops the")
            print("  other devices on your wifi, and nothing more -- it travels")
            print("  in plain HTTP. Do not expose this beyond a network you own.")
        print("ledger:", RAIL.ledger.label)
        print_provider_status()
        print_store_status()
        httpd.serve_forever()


if __name__ == "__main__":
    main(sys.argv[1:])
