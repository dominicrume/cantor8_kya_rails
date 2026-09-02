"""DevNetLedger: the real Canton rail, same interface as MockLedger.

agent.py does not know which one it is talking to. It attempts; the ledger
decides. That is the whole point of the NOT list in THE-JOB.md -- no spending
rule lives in this file, every refusal string below is quoted back from what
Canton actually returned.

Requires C8_CLIENT_SECRET in the environment. Never in a file: THE-RULES.md.
"""
import datetime, os, re, sys, time, uuid

# MUST run before `import c8lab`. The toolkit reads C8_USER at import time and
# freezes it into submit()'s `sub=USER` default argument, and submit() puts that
# straight into the request body as "userId". Set it afterwards and every
# command silently carries userId=ledger-api-user, a LocalNet name that does not
# exist on DevNet -- which comes back as an opaque 403 "security-sensitive
# error", not as anything mentioning the user.
ENV = {"C8_BASE": "https://api.validator.dev.digik.cantor8.tech/api/ledger",
       "C8_IDP": "https://auth.dev.digik.cantor8.tech",
       "C8_CLIENT_ID": "hackathon",
       "C8_REGISTRY": "https://sv-proxy.dev.digik.cantor8.tech",
       "C8_USER": "validator-backend@clients",
       "C8_ADMIN_USER": "validator-backend@clients",
       "SSL_CERT_FILE": "/etc/ssl/cert.pem"}
for _k, _v in ENV.items():
    os.environ.setdefault(_k, _v)

sys.path.insert(0, os.path.expanduser("~/hackathon-toolkit"))
import c8lab

USER = os.environ["C8_USER"]        # passed explicitly, never left to the default

NS  = "::12204e94c0e449c0efcd270dd1e68259c36471cebef132e5c7dfc2750fe8c9eed77f"
PKG = "df5a02e88a68521095a7e6bb08a4d2c57ee87d4af0910a7c656fb231a5a07b0b"
TPL, PROP = f"{PKG}:KyaMandate:KyaMandate", f"{PKG}:KyaMandate:KyaMandateProposal"
# KyaAnchor arrived in 1.1.0, so it carries that package id rather than the
# 1.0.0 the mandate templates were deployed under. Both are vetted; a command
# names the package it wants and Canton resolves it.
ANCHOR_PKG = "fd3f43a273be2187025c03699b8a107f58fe2d0a5b7a62295885b6ab58f12ab9"
# Commands take a package ID. ACS filters insist on a package NAME reference
# and reject an ID outright: "expected a package name". Same template, two
# spellings, and the error only tells you which one you got wrong.
TPL_BY_NAME = "#kya-rails-mandate:KyaMandate:KyaMandate"
PARTY = {r: f"kya-{r}-1{NS}" for r in
         ("owner", "agent", "customer", "partner", "unverified")}

# The assertion messages in KyaMandate.daml. We match them so the receipt can
# cite the rule by name; the ledger, not this file, decides which one fires.
RULES = re.compile(r"(mandate expired|charge would exceed the cap|"
                   r"charge would exceed the period limit|"
                   r"payee is not on the allow-list|amount must be positive|"
                   r"new cap below what is already spent)")

def _configure():
    secret = os.environ.get("C8_CLIENT_SECRET", "")
    if not secret:
        raise SystemExit("C8_CLIENT_SECRET is not set. Shell only, never a file.")
    if secret.strip(".") == "" or len(secret) < 12:
        # "..." is a placeholder from the docs, and pasting it produces an auth
        # failure that surfaces three layers away as "no holdings visible".
        raise SystemExit(
            "C8_CLIENT_SECRET looks like a placeholder (%r), not a real secret.\n"
            "Paste the actual value from the organisers." % secret[:12])
    c8lab.BASE = os.environ["C8_BASE"]
    c8lab.IDP = os.environ["C8_IDP"]
    c8lab.CID = os.environ["C8_CLIENT_ID"]
    c8lab.CSEC = os.environ["C8_CLIENT_SECRET"]


class LedgerUnreachable(RuntimeError):
    """We never reached the ledger. NOT a refusal, and never stamped as one."""


# Markers that mean Canton looked at the command and said no.
LEDGER_ANSWERED = (
    "CONTRACT_NOT_ACTIVE", "NOT_FOUND", "uthoriz", "INVALID_ARGUMENT",
    "DAML_AUTHORIZATION_ERROR", "DAML_FAILURE", "User failure",
    "NOT_VALID_UPGRADE_PACKAGE",
)


def _is_ledger_answer(m):
    """Did Canton decide, or did the network eat it?

    Only these mean the ledger looked at the command and said no. Anything
    else -- TLS timeouts, DNS, token failures, 5xx -- is us failing to ask,
    and recording that as REFUSED would put a lie inside a sealed receipt.
    """
    # DAML_FAILURE is an assertion in the choice body firing. That is the
    # ledger deciding, not the network failing, and treating it as retryable
    # meant a real refusal was retried eight times and then reported as "the
    # ledger never answered".
    return bool(RULES.search(m)) or any(marker in m for marker in LEDGER_ANSWERED)


def _retry(fn, tries=8):
    """DevNet drops TLS handshakes under load. A hang is the network, not us.

    c8lab caches its Keycloak token for the life of the process and never
    refreshes it; the token is good for 900s. Clearing it on the way round
    means a long demo cannot die of an expired token mid-run.
    """
    last = None
    for i in range(tries):
        try:
            return True, fn()
        except Exception as e:
            m = str(e).replace("\n", " ")
            last = m
            if _is_ledger_answer(m):
                return False, m            # the ledger answered; not a retry
            c8lab._tok.clear()
            time.sleep(min(2 + 3 * i, 15))
    raise LedgerUnreachable(
        "gave up after %d tries; the ledger never answered, so nothing is "
        "recorded. Last error: %s" % (tries, str(last)[:200]))


def _submit(commands, act_as, want_transaction=True):
    """Retry the SAME command id, so a retry is idempotent.

    c8lab.submit mints a fresh commandId per call. Over a link that drops
    responses, a command can commit on the ledger while the reply is lost;
    the retry is then a NEW command that finds the contract already consumed
    and comes back CONTRACT_NOT_FOUND. That looks like a bug in the mandate
    and is really a lost packet. One id, and Canton deduplicates for us.
    """
    cid = "kya-%s" % uuid.uuid4()
    return _retry(lambda: c8lab.submit(commands, act_as=act_as, sub=USER,
                                       command_id=cid,
                                       want_transaction=want_transaction))


def _rule(m):
    hit = RULES.search(m)
    if hit:
        return hit.group(1)
    if "CONTRACT_NOT_ACTIVE" in m or "NOT_FOUND" in m:
        return "Revoke: mandate no longer active on the ledger"
    if "uthoriz" in m:
        return "missing authorization from owner"
    return m[:110]


def _created(r, entity="KyaMandate"):
    """The cid of the created contract OF THAT TEMPLATE.

    Charge creates ChargeRecord first and the successor mandate second, so
    "first created event" is the record, not the mandate. Exercising a mandate
    choice on that cid returns WRONGLY_TYPED_CONTRACT_ID, which reads like an
    auth problem and is not one. Match the template by name.
    """
    for ev in r.get("transaction", {}).get("events", []):
        c = ev.get("CreatedTreeEvent", {}).get("value") or ev.get("CreatedEvent")
        if c and str(c.get("templateId", "")).endswith(":" + entity):
            return c.get("contractId")


def discover_admin():
    """The instrument issuer, taken from a holding we can already see.

    c8lab.dso_party() scans /v2/parties for a party starting with "DSO::". On
    the shared DevNet validator that list is paginated over thousands of
    entries and the DSO is not in the page returned, so the lookup fails with
    "could not find the DSO party" -- which reads like the network is not
    ready. Every Amulet holding names its admin, so ask a holding instead.
    """
    for party in (PARTY["agent"], PARTY["owner"]):
        ok, hs = _retry(lambda: c8lab.holdings(party, sub=USER), tries=4)
        if ok and hs:
            return hs[0]["admin"]
    return None


def _spendable(party):
    ok, hs = _retry(lambda: c8lab.holdings(party, sub=USER), tries=4)
    if not ok:
        return 0.0
    return sum(float(h["amount"] or 0) for h in hs if not h["locked"])


def _active_mandates(expires_at=None):
    """Live KyaMandate contracts for the agent.

    After an ambiguous failure -- command committed, response lost -- a cached
    contract id is stale, and the next exercise returns CONTRACT_NOT_FOUND.
    Believing that would stamp "mandate no longer active" on a receipt while
    the mandate is alive and well. Reconcile from state; never guess.

    `expires_at` narrows to OUR mandate. Earlier runs leave live mandates
    behind, and "any active mandate" is not "the one we just opened" -- pick
    the wrong one and every charge comes back "mandate expired" against a
    mandate we never created. expiresAt is minted per run and identifies it.
    """
    try:
        ok, res = _retry(_query_active_mandates, tries=4)
    except LedgerUnreachable:
        return None          # cannot see the ledger: decline to guess
    if not ok:
        return None
    return _pick_mandates(res, expires_at)


def _query_active_mandates():
    body = {"filter": {"filtersByParty": {PARTY["agent"]: {"cumulative": [
                {"identifierFilter": {"TemplateFilter": {"value": {
                    "templateId": TPL_BY_NAME,
                    "includeCreatedEventBlob": False}}}}]}}},
            "verbose": True, "activeAtOffset": c8lab.ledger_end(sub=USER)}
    return c8lab.call("/v2/state/active-contracts", body, sub=USER)


def _is_gone(err):
    """The ledger says this contract id is not there -- said two ways."""
    text = str(err)
    return "NOT_FOUND" in text or "CONTRACT_NOT_ACTIVE" in text


def _pick_mandates(items, expires_at):
    out = []
    for item in items:
        ev = item.get("contractEntry", {}).get("JsActiveContract", {}).get("createdEvent", {})
        if not ev.get("contractId"):
            continue
        args = ev.get("createArgument", {}) or {}
        if expires_at is not None and args.get("expiresAt") != expires_at:
            continue
        out.append(ev["contractId"])
    return out


class DevNetLedger:
    """Same charge() contract as MockLedger. NOT MOCKED: this is real Canton."""

    label = "DevNet (real Canton, package %s)" % PKG[:12]
    # Canton Coin. The mandate records the spend; it does not move the
    # coin yet -- see SHORTCUTS.md. Saying so is cheaper than being caught.
    currency = "CC"

    @property
    def instrument(self):
        return ("Amulet (transferred on DevNet)" if self.move_coin
                else "Amulet (recorded, not transferred)")

    def name(self, role):
        """On the real rail the receipt names the actual on-ledger party, so a
        reader can paste it into the ledger API and find the contract."""
        from agent import NAMES
        return "%s (%s)" % (NAMES[role], PARTY[role].split("::")[0])

    def __init__(self, move_coin=False):
        _configure()
        self.cid = None
        self.revoked = False
        self.exp = None
        # Off by default: a real transfer is two round trips plus an accept,
        # and the demo should not need them to prove the fences. On, the
        # mandate stops being a record of a payout and becomes the payout.
        self.move_coin = move_coin
        if move_coin:
            admin = discover_admin()
            if not admin:
                # Almost always auth, not an empty wallet: a bad token returns
                # no holdings, and "no holdings" is a misleading thing to say.
                raise RuntimeError(
                    "could not read any holding, so the instrument admin is "
                    "unknown. This is usually a bad C8_CLIENT_SECRET rather "
                    "than an empty wallet -- check the secret first, then that "
                    "kya-agent-1 still holds Amulet.")
            c8lab.ADMIN_PARTY = admin
            os.environ["C8_ADMIN_PARTY"] = admin
            self.admin = admin

    def open_mandate(self, cap=5.0, life_seconds=86400,
                     period_limit=None, period_seconds=None):
        """Owner proposes, agent accepts. Both signatures, as the template demands.

        A negative life_seconds creates a mandate whose expiry has already
        passed. Nothing in Accept checks expiry -- only the assertion in Charge
        does -- so this is the same refusal as waiting out the clock, without
        making a judge watch a timer. The timed version was run and refused too.
        """
        exp = (datetime.datetime.now(datetime.timezone.utc)
               + datetime.timedelta(seconds=life_seconds)
               ).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.exp = exp          # identifies OUR mandate if we have to reconcile
        ok, r = _submit([{"CreateCommand": {
            "templateId": PROP, "createArguments": {
                "owner": PARTY["owner"], "spender": PARTY["agent"],
                "cap": "%.1f" % float(cap),
                "expiresAt": exp,
                "allowed": [PARTY["customer"], PARTY["partner"]],
                "periodLimit": None if period_limit is None else "%.1f" % float(period_limit),
                "periodLength": None if period_seconds is None
                                else {"microseconds": str(int(period_seconds) * 1000000)}}}}],
            act_as=PARTY["owner"])
        if not ok:
            raise RuntimeError("could not propose the mandate: " + str(r)[:160])
        ok, r = _submit([{"ExerciseCommand": {
            "templateId": PROP, "contractId": _created(r, "KyaMandateProposal"),
            "choice": "Accept", "choiceArgument": {}}}],
            act_as=PARTY["agent"])
        if not ok:
            live = (_active_mandates(exp) or [None])[0]   # Accept may have committed
            if not live:
                raise RuntimeError("agent could not accept: " + str(r)[:160])
            self.cid = live
            self.revoked = False
            return self.cid, exp
        self.cid = _created(r, "KyaMandate")
        self.revoked = False
        return self.cid, exp

    def charge(self, amount, payee):
        """No state here: the mandate lives on the ledger, which is the point."""
        def attempt():
            return _submit([{"ExerciseCommand": {
                "templateId": TPL, "contractId": self.cid, "choice": "Charge",
                "choiceArgument": {"amount": "%.1f" % amount,
                                   "payee": PARTY.get(payee, payee),
                                   "memo": "KYA Rails demo"}}}],
                act_as=PARTY["agent"])

        ok, r = attempt()
        if not ok and self._should_reconcile(r):
            ok, r = attempt()
        if not ok:
            return "REFUSED", _rule(str(r))
        self.cid = _created(r, "KyaMandate") or self.cid
        if not self.move_coin:
            return "ACCEPTED", "cap and allow-list satisfied, committed on DevNet"

        # The mandate authorised it. Now actually move the Amulet.
        #
        # The charge is already committed, so a failure here cannot be rolled
        # back -- it is an authorised payout that did not settle. That is a
        # real operational state and the receipt says so rather than implying
        # money moved when it did not.
        moved, detail = self._settle(amount, PARTY.get(payee, payee))
        if moved:
            return "ACCEPTED", "authorised by the mandate and settled on DevNet: " + detail
        return "ACCEPTED", "AUTHORISED but NOT SETTLED: " + detail

    def _should_reconcile(self, err):  # noqa: D401
        """Was the mandate really gone, or is our cached id just stale?

        If WE revoked it, NOT_FOUND is the right answer and reconciling would
        go hunting for some other live mandate and charge that instead --
        stamping "expired" on what was really a revoke. Only an UNEXPLAINED
        disappearance is ambiguous. Returns True if the cid was refreshed and
        the charge is worth retrying.
        """
        if self.revoked or not _is_gone(err):
            return False
        live = (_active_mandates(self.exp) or [None])[0]
        if live and live != self.cid:
            self.cid = live
            return True
        return False

    def _settle(self, amount, receiver):
        """Move Amulet for a charge the mandate has already authorised."""
        ok, r = _retry(lambda: c8lab.transfer(PARTY["agent"], receiver,
                                              "%.1f" % amount, sub=USER), tries=4)
        if not ok:
            return False, str(r)[:110]
        kind = r.get("transferKind")
        if kind == "offer" and r.get("instructionCid"):
            # No TransferPreapproval, so it lands as an offer the receiver
            # accepts. We hold act-as on our own parties, so we can.
            ok2, r2 = _retry(lambda: c8lab.accept_transfer(
                r["instructionCid"], receiver, sub=USER), tries=4)
            if not ok2:
                return False, "offer created but not accepted: " + str(r2)[:90]
            return True, "%.1f Amulet transferred (offer accepted)" % amount
        if kind == "direct":
            return True, "%.1f Amulet transferred (direct)" % amount
        return False, "unexpected transferKind: %s" % kind

    def anchor(self, seal, count, label):
        """Publish this chain's head on Canton. Returns (published, detail).

        Called at the end of every --devnet run rather than when somebody
        remembers, because a chain that is not anchored carries no claim about
        where it came from -- and the gap between writing the receipts and
        anchoring them is exactly the window in which they could be swapped.

        Never raises. A run that produced real refusals is still worth having
        if the anchor fails; what is not acceptable is that failing quietly,
        so the caller is handed the reason and says so.
        """
        try:
            ok, r = _submit([{"CreateCommand": {
                "templateId": "%s:KyaAnchor:ChainAnchor" % ANCHOR_PKG,
                # Daml Int64 crosses the JSON Ledger API as a STRING. Sending
                # 6 returns HTTP 500 "Expected ujson.Str (data: 6)", which
                # names neither the field nor the type.
                "createArguments": {"principal": PARTY["owner"], "seal": seal,
                                    "receipts": str(count), "ledger": label}}}],
                act_as=PARTY["owner"])
        except LedgerUnreachable as e:
            return False, "the ledger never answered: %s" % str(e)[:110]
        if not ok:
            return False, str(r)[:150]
        return True, "signed by %s" % PARTY["owner"].split("::")[0]

    def revoke(self):
        _submit([{"ExerciseCommand": {
            "templateId": TPL, "contractId": self.cid,
            "choice": "Revoke", "choiceArgument": {}}}],
            act_as=PARTY["owner"], want_transaction=False)
        self.revoked = True
