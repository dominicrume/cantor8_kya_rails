"""DevNetLedger: the real Canton rail, same interface as MockLedger.

agent.py does not know which one it is talking to. It attempts; the ledger
decides. That is the whole point of the NOT list in THE-JOB.md -- no spending
rule lives in this file, every refusal string below is quoted back from what
Canton actually returned.

Requires C8_CLIENT_SECRET in the environment. Never in a file: THE-RULES.md.
"""
import datetime, os, re, sys, time

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
PKG = "6d13f9948206e73684461925d830261bff5a5d265191b5c764258c98f40dc241"
TPL, PROP = f"{PKG}:KyaMandate:KyaMandate", f"{PKG}:KyaMandate:KyaMandateProposal"
PARTY = {r: f"kya-{r}-1{NS}" for r in
         ("owner", "agent", "customer", "partner", "unverified")}

# The assertion messages in KyaMandate.daml. We match them so the receipt can
# cite the rule by name; the ledger, not this file, decides which one fires.
RULES = re.compile(r"(mandate expired|charge would exceed the cap|"
                   r"payee is not on the allow-list|amount must be positive)")

def _configure():
    if not os.environ.get("C8_CLIENT_SECRET"):
        raise SystemExit("C8_CLIENT_SECRET is not set. Shell only, never a file.")
    c8lab.BASE = os.environ["C8_BASE"]
    c8lab.IDP = os.environ["C8_IDP"]
    c8lab.CID = os.environ["C8_CLIENT_ID"]
    c8lab.CSEC = os.environ["C8_CLIENT_SECRET"]


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
            if RULES.search(m) or "CONTRACT_NOT_ACTIVE" in m or "NOT_FOUND" in m \
               or "uthoriz" in m:
                return False, m            # the ledger answered; not a retry
            c8lab._tok.clear()
            time.sleep(min(2 + 3 * i, 15))
    return False, last


def _rule(m):
    hit = RULES.search(m)
    if hit:
        return hit.group(1)
    if "CONTRACT_NOT_ACTIVE" in m or "NOT_FOUND" in m:
        return "Revoke: mandate no longer active on the ledger"
    if "uthoriz" in m:
        return "missing authorization from owner"
    return m[:110]


def _created(r):
    for ev in r.get("transaction", {}).get("events", []):
        c = ev.get("CreatedTreeEvent", {}).get("value") or ev.get("CreatedEvent")
        if c:
            return c.get("contractId")


class DevNetLedger:
    """Same charge() contract as MockLedger. NOT MOCKED: this is real Canton."""

    label = "DevNet (real Canton, package %s)" % PKG[:12]
    # Canton Coin. The mandate records the spend; it does not move the
    # coin yet -- see SHORTCUTS.md. Saying so is cheaper than being caught.
    currency, instrument = "CC", "Amulet (recorded, not transferred)"

    def __init__(self):
        _configure()
        self.cid = None

    def open_mandate(self, cap=5.0, life_seconds=86400):
        """Owner proposes, agent accepts. Both signatures, as the template demands.

        A negative life_seconds creates a mandate whose expiry has already
        passed. Nothing in Accept checks expiry -- only the assertion in Charge
        does -- so this is the same refusal as waiting out the clock, without
        making a judge watch a timer. The timed version was run and refused too.
        """
        exp = (datetime.datetime.now(datetime.timezone.utc)
               + datetime.timedelta(seconds=life_seconds)
               ).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
        ok, r = _retry(lambda: c8lab.submit([{"CreateCommand": {
            "templateId": PROP, "createArguments": {
                "owner": PARTY["owner"], "spender": PARTY["agent"],
                "cap": "%.1f" % float(cap),
                "expiresAt": exp,
                "allowed": [PARTY["customer"], PARTY["partner"]]}}}],
            act_as=PARTY["owner"], sub=USER, want_transaction=True))
        if not ok:
            raise RuntimeError("could not propose the mandate: " + str(r)[:160])
        ok, r = _retry(lambda: c8lab.submit([{"ExerciseCommand": {
            "templateId": PROP, "contractId": _created(r),
            "choice": "Accept", "choiceArgument": {}}}],
            act_as=PARTY["agent"], sub=USER, want_transaction=True))
        if not ok:
            raise RuntimeError("agent could not accept: " + str(r)[:160])
        self.cid = _created(r)
        return self.cid, exp

    def charge(self, amount, payee):
        """No state here: the mandate lives on the ledger, which is the point."""
        ok, r = _retry(lambda: c8lab.submit([{"ExerciseCommand": {
            "templateId": TPL, "contractId": self.cid, "choice": "Charge",
            "choiceArgument": {"amount": "%.1f" % amount,
                               "payee": PARTY.get(payee, payee),
                               "memo": "KYA Rails demo"}}}],
            act_as=PARTY["agent"], sub=USER, want_transaction=True))
        if not ok:
            return "REFUSED", _rule(str(r))
        self.cid = _created(r) or self.cid
        return "ACCEPTED", "cap and allow-list satisfied, committed on DevNet"

    def revoke(self):
        _retry(lambda: c8lab.submit([{"ExerciseCommand": {
            "templateId": TPL, "contractId": self.cid,
            "choice": "Revoke", "choiceArgument": {}}}], act_as=PARTY["owner"], sub=USER))
