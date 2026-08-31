# Threat model

What this system defends against, what it does not, and what an attacker gets
if each part fails. Written to be argued with.

**The asset:** a float held in one country, spent by an operator in another,
under a mandate issued by a principal who cannot be present.

**The trust boundary:** the operator is *not* trusted. Neither is the machine
it runs on, nor the messages it receives. The ledger is trusted. The
principal's key is trusted.

---

## T1 — The operator is persuaded to pay the wrong account

*"Change of account, send it here instead."* The commonest way money leaves a
business like this, and it does not require a dishonest operator — only a
convinced one. Against an AI operator this is prompt injection; the mechanism
differs, the outcome is identical.

**Defence:** `payee elem allowed`, asserted in the `Charge` choice body.
Canton refuses before the transaction exists.
**Residual risk:** an attacker who can get an account *added to the
allow-list* defeats this entirely. The allow-list is changed by the principal,
so this reduces to T4. **Adding a counterparty is the security-critical
operation in this system, not paying one.**

## T2 — The operator drains the float

**Defence:** total cap, plus an optional per-period limit, both asserted in
the choice body. Enforced twice for the cap — the assertion and the `ensure`
invariant.
**Residual risk:** an operator can still spend the full cap on legitimate
counterparties. The cap bounds the loss; it does not prevent it. Set the cap
to what you can afford to lose in the window, not to what is convenient.

## T3 — The operator keeps spending after being told to stop

**Defence:** `Revoke` is consuming, `controller owner`, and creates nothing.
There is no flag to race and no successor contract to charge against.
**Residual risk:** revocation is only as fast as the principal noticing. The
receipt chain is what makes noticing possible; the expiry is what bounds the
damage when nobody is looking.

## T4 — The principal's credentials are stolen

**Not defended.** An attacker with the principal's signing authority can widen
the cap, add counterparties, and issue new mandates. Every fence in this
system derives from that key.
**Mitigation is out of scope here** and belongs in key management: hardware
keys, and a second signatory on `Adjust` if the deployment can bear it. This
is the top risk in the system and the one least addressed by this code.

## T5 — The operator forges a statement

**Defence:** every receipt is sealed over the previous seal. Editing one
breaks it and every one after it. The principal recomputes offline — no
network, no key material, no trust in the producer.
**Residual risk, and it is real:** the chain is **not signed**. An operator
who discards the real chain and produces a fresh, internally consistent one
passes verification. We tested this and it passes.

The chain proves *nobody edited this history*. It does not prove *this is the
history*. Binding it to origin — a signature over the final seal, or anchoring
the seal on-ledger — is unimplemented, and is the largest gap in the format.
`ChargeRecord` partially covers it for accepted charges, since those exist
on-ledger independently. **Refusals have no such anchor.**

## T6 — The operator hides a refusal

An operator that quietly drops refused attempts produces a shorter chain that
still verifies.
**Defence: none in the format.** The chain is tamper-evident, not
completeness-proving. Nothing forces a producer to record an attempt it would
rather forget.
**Mitigation:** `n` increases by exactly one, so removing a receipt from the
middle is detectable. Removing the tail is not. Publishing the final seal
somewhere the operator does not control turns tail-truncation into a
detectable event; we do not do this yet.

## T7 — Two implementations disagree about a seal

A chain verifying on the server and failing in the browser destroys the
guarantee, and the failure is silent until someone checks.
**Defence:** one specification, ten conformance vectors, three independent
implementations, all in CI. `assert_ascii` refuses to seal what a verifier
could not reproduce.
**Residual risk:** the vectors cover what we thought to test. The Go
implementation found an unspecified escaping rule that two implementations had
silently agreed on. A fourth may find another.

## T8 — The ledger itself is wrong or unavailable

**Defence against unavailability:** a failure to reach the ledger is never
recorded as a refusal. If we could not ask, nothing is written and the run
stops.
**Not defended:** if Canton commits something it should not have, this system
records it faithfully. It inherits the ledger's correctness.

## T9 — A stranger claims someone else's deposit

The loss that actually happens on a desk, and the one the mandate alone does
not prevent.

A quote is given at 10:00 to someone who never sends. At 13:00 somebody else
deposits. At 14:00 a third party — who has been watching the deposit address,
because on a public chain anyone can — messages the operator with a screenshot
claiming the deposit is theirs, and supplies their own payout account. The
operator pays. Later the real depositor arrives and is paid too. **The desk
pays twice and neither payment was unauthorised.**

Nothing in that sequence requires a careless operator. A screenshot is not
evidence of sending, and by the time anyone can tell, both payouts have gone.

**Defence:** `KyaQuote` binds the payout account to the quote **at the moment
the quote is issued, before any deposit exists**. A claimant arriving after
the money cannot change it, and cannot produce a reference they never
received. `Fulfil` is consuming, so a quote settles once or not at all — the
double payout is not a rule an operator has to remember at 2am, it is an
archived contract that cannot be exercised twice.

**Why this needs almost no KYC.** The question stops being *who is this
person*, which is expensive and drives real customers away, and becomes *is
this the same person who asked* — which the quote already answers.

**Canton's part in it:** on a public chain the deposit is monitorable by
anyone, which is what makes the claim cheap to fabricate. A Canton
counterpart is visible only to the parties to it;
`testWatcherCannotSeeTheQuote` holds that.

**Residual risk:** the operator can still fulfil against the wrong quote by
hand if two are open with similar amounts, and an operator who is themselves
the fraudster can issue a quote naming their own account. The second is T4
wearing different clothes — it needs the principal's controls over who may
issue quotes, which is not built.

## T10 — The customer is given the wrong deposit address

The desk quotes for USDT, BTC, XRP and others, each arriving over a different
network. Hand over an ERC-20 address for a TRC-20 transfer, or omit a memo on
a chain that requires one, and the deposit does not bounce. **The coin is gone
and no fence later in the cycle can recover it.**

This is not a fraud. It is an operator moving fast on a phone while somebody
waits, which is the condition under which the whole cycle runs.

**Defence:** `DepositBook` holds approved addresses per (asset, network), each
flagged for whether that network requires a memo. The operator cannot issue an
instruction for a network the desk has no address on, and cannot issue one
without a memo where a memo is required. `DepositInstruction` is observed by
the customer, so *"you sent me the wrong address"* becomes a question with an
answer on the ledger.

**Residual risk:** an approved address that is itself wrong is faithfully
handed out. The principal approves addresses, so this is T4 again.

**Confirming the deposit.** An operator confirming that money landed is an
operator reading a block explorer on a phone under pressure — a judgement
call, and the class of failure this system exists to remove. A deposit feed
the principal names may write the confirmation instead, with a transaction
reference required. Its authority is deliberately narrow: it says money
arrived on chain, and it cannot pay anyone. The operator cannot appoint it.

This is the exact twin of the bank feed in T12, and the symmetry is the
point: **both directions of the cycle have a moment where a human is asked
to believe a screen, and both are now feeds rather than judgement.**

## T11 — The off-taker takes the crypto and does not send the naira

When the desk has no naira it sends the crypto **first**, to a wallet the
off-taker supplies, and waits. It is the same "wallet they provided" attack as
T9, except the money is the desk's own and the amounts are much larger.

**Defence:** `OffTakerBook` approves wallets per (off-taker, asset, network) —
an approval is for a wallet on a chain, not for a name, so a new address sent
over WhatsApp this morning is refused. `ConfirmNairaReceived` refuses an amount
short of what was agreed, so a shortfall is a refusal rather than something
argued about at 2am with a customer waiting.

**Residual risk, and it is the big one: none of this makes the off-taker pay.**
It bounds where the crypto may go and records what was owed. An off-taker who
receives at an approved wallet and simply keeps it is a commercial and legal
problem, not a technical one. The ledger gives you a timestamped record of
exactly what was sent, where, and what was agreed — which is what a recovery
action needs — and nothing more.

## T12 — The fake bank alert (naira in, crypto out)

The reverse leg, and the more dangerous direction for a reason that has
nothing to do with cryptography: **a naira transfer can be reversed and a
crypto send cannot.** The desk is exposed from the moment it releases.

The customer sends a doctored transfer receipt. The operator, on a phone,
looks at it and releases the crypto. The money never arrives. Looking harder
does not help — a good forgery and a real screenshot are the same pixels.

**Defence:** `ConfirmNairaCredited` is `controller principal`. The operator
sees a screenshot; the principal sees the account, and only the person who
can see the account may say money is in it. A bank reference is required, so
the confirmation points at something checkable later rather than at somebody's
recollection. `ReleaseCrypto` refuses without that confirmation.

**Residual risk, and it is serious: a confirmed credit can still be reversed.**
Fraudulently sourced funds get recalled days later, and by then the crypto is
gone. Nothing here defends that. A hold period before release is the usual
mitigation and is **not implemented**; it is a commercial decision about how
long the desk is willing to make customers wait.

**The bank feed.** `controller principal` is honest and does not scale past
one person, so a feed party the principal names may write the confirmation
instead. Its authority is deliberately narrow: confirm a credit that matches,
and nothing else. It cannot release crypto, approve an account, or move the
rate band, and the operator cannot appoint it. The same fences apply to it —
a reference is required and a short credit is refused — so automating the
confirmation does not quietly remove the check it was there to carry.

**What the feed changes about hiring.** Confirmation was the reason an
employee could not be trusted with the admin work: they would be confirming
money into an account they can see. With a feed writing it, the human never
holds that authority, and the job becomes safe to delegate.

## T13 — The desk sends on the wrong network

On the outbound leg the desk is the **sender**, so a wrong-network send is the
desk's own loss rather than the customer's.

**Defence:** the receiving wallet and its network are fixed when the rate is
agreed, and `ReleaseCrypto` refuses a different network or a different wallet.
The desk also cannot quote an asset it has no way to send.

**Residual risk:** an address that is valid on two chains, quoted against the
wrong one, is faithfully sent to the wrong one.

## T14 — A forged receipts file attacks the person verifying it

The verifier's whole purpose is that a stranger hands you a chain and you
check it. That means `receipts.js` is untrusted input by design, and a chain
carrying markup in a field — `"payee": "<img src=x onerror=...>"` — runs in
the browser of the person doing the checking. The tool for catching liars
becomes the delivery mechanism.

Found by running the project's own code auditor over the repository, which
flagged 23 `innerHTML` uses; two of them interpolated unescaped values.

**Defence:** every field out of a receipt is escaped before it reaches the
DOM, and `tests/xss_lint.py` fails CI on any unescaped interpolation in any
of the three pages. Verified with a deliberately forged `receipts.js`: the
markup renders as text.

**Residual risk:** the same discipline is needed on any page added later. The
lint covers the three that exist; a fourth would need adding to its list.

---

## What is not in scope

Custody, key management, transport security between the operator's device and
the ledger, sanctions and AML screening of counterparties, and the legal
question of who may move money where. The last is a licensing matter and no
amount of Daml addresses it.

## Ranked, honestly

| | Risk | Status |
| --- | --- | --- |
| 1 | Principal's key stolen (T4) | not defended; out of scope, and the biggest hole |
| 2 | Chain not bound to origin (T5) | known, documented in SPEC.md section 8, unimplemented |
| 3 | Refusals can be omitted (T6) | partially detectable; tail truncation is not |
| 4 | Adding a counterparty (T1 residual) | the real privileged operation; deserves its own control |
| 5 | Operator issues a quote to themselves (T9 residual) | not defended; needs controls on quote issuance |
| 6 | Operator persuaded (T1) | **defended** |
| 7 | Float drained (T2) | **defended, bounded** |
| 8 | Spending after revoke (T3) | **defended** |
| 6 | Off-taker keeps the crypto (T11 residual) | **not defended** — bounded and recorded, not prevented |
| 9 | Stranger claims a deposit (T9) | **defended** — the account is fixed before the money exists |
| 9 | Wrong network or missing memo (T10) | **defended** — the instruction cannot be issued |
| 9 | Crypto to an unapproved off-taker wallet (T11) | **defended** |
| 3 | Confirmed naira later reversed (T12 residual) | **not defended** — no hold period; a commercial decision |
| 9 | Fake bank alert (T12) | **defended** — only the principal may confirm a credit |
| 9 | Desk sends on the wrong network (T13) | **defended** |
| 10 | Implementations diverge (T7) | **defended, three implementations in CI** |
