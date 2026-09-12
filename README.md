# KYA Rails

[![ci](https://github.com/dominicrume/cantor8_kya_rails/actions/workflows/ci.yml/badge.svg)](https://github.com/dominicrume/cantor8_kya_rails/actions/workflows/ci.yml)

**Know Your AgenticAI is the evidence layer that sits under an agent
platform.**

A platform decides what an agent may do. This records what it **tried and was
refused**, sealed so the other side can check it without trusting whoever ran
the agent.

Every log records what your agent did. The question an auditor, a counterparty
or a regulator actually asks is the other one: *what did it try, and what
stopped it?* An ordinary log cannot answer that, because the operator who
writes the log is the party the question is about.

Know Your AgenticAI writes a receipt for every attempt, refusals included, and
seals each one onto the last. Anyone can check the chain by dropping the file
on a web page. No wallet, no install, no account, no node. The head is
anchored on Canton, so a chain rewritten from scratch has nowhere to hide.

And the refusal itself is written to the ledger, which is the part that was
missing. The normal way to enforce a spending rule is to abort the
transaction, and an aborted transaction leaves nothing behind: after a refused
payment the ledger looks exactly as it would if the agent had never been
asked. So the accepted payments were checkable against the world and the
refusals were us writing about ourselves, which is backwards.
[`TryCharge`](step-1-mandate/daml/KyaMandate.daml) runs the same rules and,
when one says no, commits a `ChargeRefused` contract and moves no money. The
contract id and the record time come from the ledger. A refusal that happened
cannot then be invented, deleted, backdated or reordered, and removing one is
itself a recorded event.

**It is not a wallet, a registry or a rail, and it does not try to be.** Those
exist and are built by people with banking licences. This is the layer
underneath them: the artefact you hand someone when they ask you to prove a
negative.

The spending rules are not policy in an application. They are `assertMsg`
fences in a Daml choice body: the agent cannot argue with them, the operator
cannot quietly widen them, and a crash does not reset them.

KYC asks whether a person is who they say. **KYA asks what an autonomous
actor was permitted to do, and proves what it was stopped from doing.**

### D1, answered — the three attacks the judges will run

The brief says: *"We will try to make your agent exceed its cap, and pay someone
it should not. Both must fail **on the ledger**, not in your API. Be ready to show
us the line of Daml that stops it. Then we will revoke and try again."*

Here are the lines.

| The attack | The line of Daml that refuses it | The test that proves it |
| --- | --- | --- |
| Exceed the cap | [`KyaMandate.daml:129`](step-1-mandate/daml/KyaMandate.daml#L129) — `assertMsg "charge would exceed the cap" (spent + amount <= cap)` | `testOverCapRefusedByTheCapAssertion` |
| Pay someone not allowed | [`KyaMandate.daml:130`](step-1-mandate/daml/KyaMandate.daml#L130) — `assertMsg "payee is not on the allow-list" (payee ``elem`` allowed)` | `testPayoutRedirectionRefused` |
| Charge after revoke | [`KyaMandate.daml:195`](step-1-mandate/daml/KyaMandate.daml#L195) — `choice Revoke` is **consuming**: it archives the mandate, so there is no contract left to charge. Stronger than an assertion | `testAfterRevokeRefused` |

Two more fences on the same choice, beyond what D1 asks for:
[expiry](step-1-mandate/daml/KyaMandate.daml#L127),
[positive amount](step-1-mandate/daml/KyaMandate.daml#L128), and a
[per-period limit](step-1-mandate/daml/KyaMandate.daml#L143) that refuses while the
total cap still has room.

**Every fence is proven load-bearing, not just present.** `tests/mutation.py`
deletes each of the 30 `assertMsg` fences in turn, rebuilds, and requires a
*named* test to go red. All 30 do — so no fence is decoration, and none is
enforced only by a test that would pass without it:

```
$ python3 tests/mutation.py
baseline: 100 scripts green
  ok    charge would exceed the cap          -> testOverCapRefusedByTheCapAssertion goes red
  ok    payee is not on the allow-list       -> testPayoutRedirectionRefused goes red
  ...  32 of 32
every fence is covered: deleting any one of them turns a test red.
```

One command runs the ledger side end to end:

```bash
python3 tests/daml_tests.py                # 100 of 100 attack scripts
```

Nothing above is enforced in Python. The Python mirror in `step-2-agent/agent.py`
is labelled `MOCKED` and exists so the demo survives a dead network; the fences
that matter are the ones on this page.

---

Two parts, and the second one is not about Canton:

1. **[SPEC.md](SPEC.md)** — an open format for tamper-evident receipts of agent
   actions, **including the actions that were refused**. Stdlib-only, no
   signatures, no network to verify. Three independent implementations and
   [20 conformance vectors](tests/vectors.json). Three independent
   implementations agree.
2. **A reference application** — the spend-limited wallet D1 asks for, with the
   limits enforced in a Daml choice body.

Cantor8 *Build on Canton* hackathon, challenge D1.
Built with the KYA Method: Promise it. Attack it. Inspect it. Prove it.

---

## The problem

A business whose principal is in one country and whose payouts happen in
another has one structural problem: **someone has to execute on the ground, and
that someone cannot be given unbounded authority over the float.**

Hire an operator and you are trusting a person with your money in a place you
are not. Automate the operator and you are trusting a process with your money
in a place you are not. Either way the authority is the same shape: a key, or a
login, or a signing right. And every one of those has exactly one answer: yes.

The failure is not usually theft. It is this message, which every operator
eventually receives:

> "Change of account — send it to this one instead."

It arrives from a compromised customer, or a socially engineered operator, or
occasionally the operator itself. The operator does not have to be dishonest
for the money to leave; they only have to be convinced. In agent terms this is
prompt injection, and it is the same attack with a different name.

Every mitigation people reach for first — a limit in the prompt, a check in the
backend, a policy document, an instruction in the operating manual — is **the
operator policing itself**. Edit the file, or talk the operator past its own
check, and the float is gone.

## The approach

The operator gets a mandate instead of a key. It is a Daml contract on Canton:
a **cap**, a **counterparty allow-list**, an **expiry**, and a **revoke the
principal can exercise from anywhere**. All four are asserted inside the
`Charge` choice body, so Canton validates them *before the transaction can
exist*. There is nothing to roll back and nothing to detect afterwards, because
the payout never happens.

Now "change of account, send it here instead" is not a judgement call the
operator has to get right under pressure. It is a request the ledger refuses.

Both parties sign it (`signatory owner, spender`), so the operator consents to
its own limits and then cannot remove them. We tested exactly that: the operator
tried to raise its own cap and the ledger refused it for missing principal
authorisation.

**Every attempt is sealed into a receipt chain — including the ones the ledger
refused.** Most systems log what succeeded. This one proves what was *tried and
stopped* — which is what you need when you are reading a statement from another
country and deciding whether to trust the person who produced it.

---

## The numbers

| Claim | Evidence |
| --- | --- |
| Attack suite green | **100 / 100** `daml test` scripts, both directions of the cycle. `--show-coverage` reports 30 of 44 template choices exercised; the other 14 are Daml's auto-generated `Archive`, so every choice we wrote is covered. The count is checked by `tests/balance_lint.py`, because it read **92** for weeks after the suite had grown |
| Published | **`pip install knowyouragenticai-receipts`** — [live on PyPI](https://pypi.org/project/knowyouragenticai-receipts/) since 6 September 2026. **1.1.0**, MIT, **zero dependencies**, with the conformance vectors inside it, so `python -m knowyouragenticai_receipts selftest` reports 20/20 with no network |
| Anyone can implement it | ~40 lines, graded through a pipe in any language — `tests/conformance_any.py -- ./yours`. Two of the 16 vectors exist because we asked which wrong implementations still passed, and two did |
| The journal cannot be edited | **5** checks on the journal: a receipt written before a process was killed is still there afterwards, and an entry edited or deleted from the middle of the file is refused on the next open |
| The tests are themselves tested | `tests/mutation_suite.py` breaks **69** real things — the page's tamper detection, the webhook's signature check, the QR's contents, the audit trail, the route error boundary, the model's session with the wallet, the receipts a killed process must not lose, the refusals a disclosure must not be able to drop, the ledger record that stops a refusal being only our word, the rule the demo's mirror must not quietly rename — and requires the suite that claims to cover each one to go red. Two audits found 15 assertions that could not fail; this is what stops the sixteenth |
| Every fence mutation-tested | all **32** in the Daml: delete any one and a *named* test goes red. `tests/mutation_py.py` does the same for the refusals at the edges, and now covers **1 of 1** — the journal's, because the webhook adapters it also covered moved to the kya-desk repository with the desk. The count is small and stated rather than rounded: it was 30 of 30 when there were thirty edges, and a repository that quotes yesterday's number is the thing this column exists to prevent |
| One bad line cannot end the model's session | `tests/mcp_smoke.py` feeds 15 malformed JSON-RPC lines **between** the good ones. Each gets its proper code (-32700 / -32600 / -32601), and the request after them all is still answered |
| The chain is bound to its origin | the head is published on Canton — a **fully forged** chain verifies green in all three implementations, and the ledger answers `NOT ANCHORED` |
| Fences enforced on-ledger | cap, **per-period limit**, allow-list, expiry, positive amount — five `assertMsg` fences in the `Charge` choice body. Revoke is not one of them and should not be: it is a **consuming** choice, so it archives the mandate and there is no contract left to charge. That is a stronger guarantee than an assertion, and the distinction is worth stating rather than rounding off |
| Deployed on Cantor8 DevNet | Built: `kya-rails-mandate` **1.1.1** on SDK 3.4.11 (100/100 scripts). Vetted on DevNet: **1.1.0**, as an upgrade of 1.0.0 — 1.1.1 is built and tested but not yet uploaded, and this row will say so until it is. The mandate templates carry package `df5a02e88a68…` from 1.0.0; `KyaAnchor` arrived in 1.1.0 as `fd3f43a273be…`, and both are vetted |
| Refusals returned by real Canton | over-cap, unverified payee, expired, revoked, agent-only `Adjust` |
| Receipt chain | 6 receipts, 2 accepted, 4 refused, chain verifies end to end |
| Tamper evident | edit one receipt, every later seal breaks |
| Real Canton Coin moved | 5.0 CC split by mandate-authorised transfers, **total conserved and the unverified account left at 0.0** — the arithmetic is [below](#the-float-adds-up), from [docs/devnet-balances.json](docs/devnet-balances.json), checked by `tests/balance_lint.py` |

The expiry proof is the strongest single piece of evidence: **the same mandate,
same payee, same amount — ACCEPTED at T, REFUSED at T+100s on a real clock.**
Only time changed. `expiresAt` is just a field until the assertion in `Charge`
makes it a rule.

### The float adds up

Real Amulet on Cantor8 DevNet, measured 31 August 2026 either side of a
`--devnet --move-coin` run:

| Party | Opening | Closing | Moved |
| --- | ---: | ---: | ---: |
| `kya-agent-1` | 5.0000 | 1.4000 | −3.6000 |
| `kya-customer-1` | 0.0000 | 2.1000 | +2.1000 |
| `kya-partner-1` | 0.0000 | 1.5000 | +1.5000 |
| **`kya-unverified-1`** | **0.0000** | **0.0000** | **0.0000** |
| **Total** | **5.0000** | **5.0000** | **0.0000** |

Two things are worth reading off it. The totals match, so no coin was created
or lost. And the account the agent was told to redirect to holds zero on both
sides — the change-of-account attack moved nothing, which is the whole of D1
stated as arithmetic rather than as a promise.

The figures live in [docs/devnet-balances.json](docs/devnet-balances.json).
`tests/balance_lint.py` re-adds every column, checks the table above against
that file cell by cell, and fails if the unverified account is non-zero on
either side. It also re-derives every count in the table above from the file
that produces it — that check exists because two of them had already drifted,
one by fourteen.

---

## Quick start

Offline, no network, no install, no server. Python is stdlib only.

```bash
python3 step-2-agent/agent.py          # writes step-3-verify/receipts.js
open step-3-verify/verifier.html       # press Play, then Verify, then Tamper
```

### Proving a chain came from you

The receipt chain proves nothing was *edited*. It never proved where the file
came from — hand someone a wholly fabricated `receipts.js` and the verifier
goes green, because every seal in it really does follow from the one before.
SPEC.md said so from the day it was written, and named the fix: bind it to a
ledger transaction.

**A `--devnet` run anchors itself**, at the end, every time — not when someone
remembers. The gap between receipts existing and being bound to anybody is
exactly the window in which they could be swapped, and a step you have to
remember is a step that gets skipped on the day it matters.

```
ANCHOR: head 1e0d5f42d165acf3... (6 receipts) published on Canton, signed by kya-owner-1
```

An offline run says the opposite just as plainly, because a MOCKED chain has
no origin to claim:

```
ANCHOR: NOT PUBLISHED -- MOCKED rail: nothing was published, so this chain is not anchored
        The receipts verify, but nothing ties them to this desk.
```

```bash
python3 tests/devnet_anchor.py --check   # does the ledger agree with this file?
python3 step-2-agent/agent.py --devnet --no-anchor   # publish nothing, and say so
```

### Check a file right now, with nothing installed

**https://dominicrume.github.io/cantor8_kya_rails/**

Drop a receipts file on it. That is the whole thing. No install, no account, no
terminal, and it works on a phone.

The page is generated by `build-standalone.py --pages` and CI fails if it drifts
from the file people are handed — a hosted copy showing a different chain under
the same name would be worse than having no hosted copy.

### Checking a file, with nothing installed

The person who most needs to verify a payment record — an auditor, a
counterparty, the customer who was paid — is the least likely to have a
terminal open. Asking them to install Python is asking for three things that
have nothing to do with their question.

So `step-3-verify/verifier.html` takes the file instead. **Drag `receipts.json`
onto the page.** It is read in the reader's own browser: nothing is uploaded,
nothing is stored, and it works with no network at all. On a phone, tap.

It reads a bare JSON array, a `const RECEIPTS = [...]` file, or a chain wrapped
in an export (`{"receipts": [...]}`, `{"data": [...]}`) — and it distinguishes
three answers that are genuinely different:

| | |
| --- | --- |
| **holds** | every seal recomputed here; nothing was edited |
| **BROKEN at entry N** | that entry or something before it was changed after the fact |
| **not a receipt chain** | valid JSON, but a different kind of file — **not** an accusation |

That third row is the one worth having. Calling an ordinary export "tampered"
is a false accusation of the most serious kind this format makes, and it is
what the CLI used to do.

**And the verifier page answers the origin question too, without a terminal.** It shows the
chain head it is holding, and takes a paste of whatever the ledger returned —
the whole output of `--check`, or just the seal. It then says `MATCHES`,
`DIFFERENT`, or that the count disagrees, which is how a truncated chain is
caught: cutting the last three receipts off leaves a chain that still verifies,
with a head that is still a real seal.

The split is deliberate. The page does the **comparison**; the reader supplies
what the **ledger** said. If the page fetched that itself, or if it were baked
into the file at build time, whoever forged the receipts would have forged that
too. A reader obtaining it independently is the entire point — and until they
do, the page says *"Not checked"*, never *"unanchored"*.

The principal publishes the final seal **and the receipt count** as a
`ChainAnchor` contract. The count is not decoration: a chain truncated after
receipt 3 still verifies, and its head is a real seal — dropping the last three
receipts is how you hide a refusal. The count is what catches it.

Demonstrated rather than asserted: a forged two-receipt chain claiming two 9.9
CC payouts to the operator's own wallet verifies with **0 broken seals**, and
`--check` answers `NOT ANCHORED`.

What this does not prove is that the receipts are *true*. A principal can
anchor a chain of lies. What they cannot do is anchor one and later swap it,
or deny publishing it.

### Give the wallet to a language model

The point of the mandate is that it holds even when the agent is persuaded.
The MCP server lets you try that yourself:

```bash
claude mcp add kya -- python3 step-4-mcp/kya_mcp.py
```

Then ask the model to settle a trade, and then ask it to overspend. It will
try, and the ledger will refuse it, and the refusal will be in the statement
with the rule that caused it. There is no tool that widens the cap, and no
form of words that gets past it.

```
open_mandate    cap 5.0
charge  2.0 -> customer     ACCEPTED
charge  1.5 -> partner      ACCEPTED
charge  3.0 -> customer     REFUSED   charge would exceed the cap
charge  1.0 -> unverified   REFUSED   payee is not on the allow-list
```

Add `--devnet` to run the same thing against real Canton.

### Demoing it

Three ways, in order of preference. None of them require a working venue network.

1. **From the repo** — `open step-3-verify/verifier.html`. Your machine, your
   file, no network at all.
2. **One file you can hand over** — `step-3-verify/kya-rails-standalone.html`
   has the receipts inlined, so it is a single document that opens by
   double-click on any machine. Email it, AirDrop it, put it on a USB stick.
   Rebuild it after any run with `python3 step-3-verify/build-standalone.py`.
3. **A local URL, if a browser is fussy about `file://`** —
   `cd step-3-verify && python3 -m http.server 8000`, then open
   `http://localhost:8000/verifier.html`. Still entirely on your machine.

The demo must never be blocked by wifi. That is a design constraint, not an
accident: see [ARCHITECTURE.md](ARCHITECTURE.md).

Against real Canton DevNet:

```bash
read -rs "C8_CLIENT_SECRET?paste your DevNet secret: "; export C8_CLIENT_SECRET
python3 tests/devnet_check.py          # is the rail usable? answers in seconds
python3 step-2-agent/agent.py --devnet
```

That first line is deliberate. `export C8_CLIENT_SECRET=<value>` invites you to
paste angle brackets, and `<` is a redirect in zsh — you get
`parse error near '\n'` and no secret. `read -rs` prompts instead: nothing is
echoed to the screen and nothing lands in your shell history, which is where a
secret typed on a command line lives forever.

If you are reviewing this rather than building on it, there is one command:

```bash
read -rs "C8_CLIENT_SECRET?paste your DevNet secret: "; export C8_CLIENT_SECRET
python3 tests/prove.py
```

It uses **your** credentials on **your** validator, asks Canton to break its own
rules four ways, checks the receipt chain that produced against the ledger, then
forges a chain in front of you — one that verifies perfectly green — and shows
the ledger naming it as not ours. It writes a mandate and an anchor; it moves no
coin unless you add `--move-coin`. Everything else is a read.

Run the preflight first. Everything else about DevNet is already defaulted in
`devnet_ledger.py` — the secret is the only thing you supply — and when it is
wrong the failure used to surface three layers down as *"cannot find the
instrument admin; no holdings visible"*, which sends you to check your wallet
when the problem is your token. The preflight separates the three cases that
look identical from the outside: no secret, the `...` placeholder pasted from
the docs, and a real secret that has expired.

The checks, all of which run in CI:

```bash
python3 tests/conformance_any.py -- ./your-implementation   # grade ANY language
python3 tests/conformance.py     # seal format, Python
node    tests/conformance.js     # seal format, JavaScript
cd impl/go && go run .           # seal format, Go
python3 tests/fence_lint.py      # every spending rule is present in its contract
python3 tests/mutation.py        # delete each Daml fence, prove a test goes red
python3 tests/mutation_py.py     # same, for every refusal in the webhook adapters
python3 tests/meta_smoke.py      # attack the WhatsApp webhook adapter
python3 tests/meta_wire_smoke.py # and again over a real socket, through the server
python3 tests/breet_wire_smoke.py # the deposit webhook, and its IP allowlist
python3 tests/store_smoke.py     # the quote outlives the process; history is tamper-evident
python3 tests/anchor_smoke.py    # the agent anchors the chain it wrote, or says it did not
python3 tests/standalone_smoke.py # the handed-out file is self-contained and current
python3 tests/complexity_lint.py # no function over the ceiling without a written reason
python3 tests/daml_tests.py                               # 100 scripts, rebuilt from source
```

---

## Architecture

```
  [verifier.html]        [agent.py]                 [Canton DevNet]
  chat replay      <--   attempts charges      -->  KyaMandate.daml
  + receipt panel        never decides              cap / allow-list /
  + VERIFY + TAMPER          |                      expiry / revoke
                             v                      enforced IN THE
                        kya_chain.py                CHOICE BODY
                        seal = sha256(
                          canonical(receipt)
                          + previous seal)
                             |
                             v
                        receipts.js
```

Three stages, one job each. The output of one is the input of the next; the
filesystem is the pipeline.

| Stage | Job |
| --- | --- |
| [`step-1-mandate/`](step-1-mandate/) | the Daml contract and the attack suite. The ledger enforces. |
| [`step-2-agent/`](step-2-agent/) | the agent and the sealed receipt chain. It only *tries*. |
| [`step-3-verify/`](step-3-verify/) | the offline verifier a judge touches. It reads receipts; it never calls the ledger. |

`MockLedger` and `DevNetLedger` expose the **same `charge()` interface**, so
`agent.py` cannot tell them apart. Swapping the entire ledger backend touched one
file — `kya_chain.py` and `verifier.html` were never opened.

### The canonicalisation contract

Specified in full in [SPEC.md](SPEC.md), with
[conformance vectors](tests/vectors.json) that any implementation can check
itself against. The seal must be byte-identical in Python and JavaScript:

```
seal = sha256( canonical(receipt_without_seal) + previous_seal )
canonical = JSON, sorted keys, separators "," and ":", ASCII only
```

ASCII is not decoration. Python escapes non-ASCII to `\uXXXX`; `JSON.stringify`
emits the raw character. Same receipt, different bytes, different hash — the
chain would verify in Python and go red in the browser. `assert_ascii()` refuses
to seal what the verifier cannot reproduce. Currency **codes** live in the
receipt; **symbols** are rendered at display time only.

---

## What is mocked, stated plainly

Honesty is scored, and overclaiming loses.

- **The demo rail is labelled on every receipt**, inside the seal, as either
  `DevNet (real Canton, package …)` or `MOCKED (mirrors KyaMandate.daml)`. A
  judge can tell which produced the artefact in front of them without asking.
- **Every address in this repository is a placeholder.** They are well-formed
  examples with no keys behind them. No wallet provider is connected, so
  nothing here can receive or send real value on any chain except Canton
  DevNet. See [docs/wallet-providers.md](docs/wallet-providers.md) for what
  connecting one actually requires.
- **The coin moves, on DevNet only.** `--devnet --move-coin` authorises the
  payout on the mandate and then transfers real Amulet; receipts say
  `Amulet (transferred on DevNet)` and name the settlement. Without that flag
  the mandate records the authorisation and nothing moves, which the receipt
  also says. DevNet Amulet is test currency and worth nothing anywhere else.
- **Authorisation and settlement are two steps, and can disagree.** The charge
  commits first. If the transfer then fails it cannot be rolled back, so the
  receipt reads `AUTHORISED but NOT SETTLED` rather than implying money moved.
- **`MockLedger` mirrors the Daml assertions in Python** so the demo survives a
  dead venue network. It is labelled MOCKED in code, in the receipt, and on the
  page.
- A network failure is **never** recorded as a ledger refusal. If the ledger
  cannot be reached, the run stops, records nothing, and says so.

See [SHORTCUTS.md](SHORTCUTS.md) for every debt taken, with a repayment plan.

---

## Repo map

| File | What it is |
| --- | --- |
| [THE-RULES.md](THE-RULES.md) | the promises this build keeps, and the NOT list |
| [ARCHITECTURE.md](ARCHITECTURE.md) | why the system is shaped this way |
| [CONTEXT.md](CONTEXT.md) | routing: which stage owns which question |
| [SHORTCUTS.md](SHORTCUTS.md) | debts taken, consciously, with repayment plans |
| [scoreboard/THIRTEEN-CHECKS.md](scoreboard/THIRTEEN-CHECKS.md) | honest self-score |
| [step-1-mandate/daml/KyaMandate.daml](step-1-mandate/daml/KyaMandate.daml) | the mandate. Cap, period, allow-list, expiry, revoke. |
| [step-1-mandate/daml/KyaQuote.daml](step-1-mandate/daml/KyaQuote.daml) | the quote. Binds a payout account to the person who asked, **before the deposit exists**. |
| [step-1-mandate/daml/KyaCycle.daml](step-1-mandate/daml/KyaCycle.daml) | crypto in, naira out: the deposit instruction and the off-taker leg. |
| [step-1-mandate/daml/KyaInbound.daml](step-1-mandate/daml/KyaInbound.daml) | naira in, crypto out: the fake-alert fence and the outbound network. |
| [step-1-mandate/test/daml/KyaTest.daml](step-1-mandate/test/daml/KyaTest.daml) | every test is named after the attack it proves |
| [step-2-agent/DEVNET-PARTIES.md](step-2-agent/DEVNET-PARTIES.md) | DevNet parties, rights, and the traps that cost us hours |
| [SPEC.md](SPEC.md) | the receipt format, written to be implemented from the text alone |
| [docs/threat-model.md](docs/threat-model.md) | twenty-two threats, several undefended and said so |
| [docs/privacy-matrix.md](docs/privacy-matrix.md) | who sees what, who is excluded — generated from the Daml, checked in CI |
| [docs/upgrade-path.md](docs/upgrade-path.md) | how we failed Canton's upgrade check, and the rules that came out of it |
| [docs/wallet-providers.md](docs/wallet-providers.md) | where the addresses would come from, and what to ask a provider |
| [docs/dev-fund-onepager.md](docs/dev-fund-onepager.md) | the Canton Development Fund ask in one page, including what it does not claim |
| [docs/complexity.md](docs/complexity.md) | the one function allowed to be complicated, and the reason it is |
| [tests/vectors.json](tests/vectors.json) | 20 conformance vectors. Where the spec and a vector disagree, the vector wins. |
| [CONTRIBUTING.md](CONTRIBUTING.md) | start here — the most useful contribution is a third implementation |

---

## Prove an agent *didn't* do the thing it wasn't allowed to do

Logs show what an agent did. Almost nothing shows what it **tried** and was
stopped from doing, in a form you can hand to somebody who doesn't trust you.

```python
from knowyouragenticai_receipts import Policy, guard, Refused

policy = Policy(cap="100.00", currency="USD", allow=["acme"], period_seconds=86400)
chain  = policy.open()          # entry 1 IS the policy

@guard(policy, chain, what="refund a customer")
def refund(amount, payee):
    return stripe.refunds.create(amount=amount, destination=payee)

refund("40.00", "acme")         # runs, recorded ACCEPTED
refund("90.00", "acme")         # raises Refused, never reaches Stripe
refund("1.00", "stranger")      # raises Refused, never reaches Stripe
```

No ledger, no chain, no Canton. Stdlib only.

**The point is the first entry.** A receipt reading `REFUSED — over the cap`
proves the agent was stopped; it does not prove what the cap *was*. An operator
who set it to a million produces a record indistinguishable from one who set it
to five, so "the agent didn't overspend" stayed unprovable — the one thing this
format exists to prove.

The policy is now receipt #1, carrying the rules as readable text. Every later
entry hashes it through `prev`:

| what someone tries afterwards | result |
|---|---|
| raise the cap | chain breaks at entry 1 |
| widen the allow-list | chain breaks at entry 1 |
| swap the currency | chain breaks at entry 1 |
| soften a refusal | chain breaks at that entry |
| delete the policy | chain stops verifying |

The verifier needed no changes — it already refuses a chain whose first entry
moved.

**Who refused is on the record.** A Python guard is the operator's own process
saying no, and it is labelled `self-attested`. A Daml fence is an independent
party saying no. The two are never written the same way, because the reader's
whole job is deciding how much to believe it. That is why the spending rules in
this repository stay in `KyaMandate.daml` and are not reimplemented here —
`guard` is for agents that have no ledger at all, and it says so on every line
it writes.

---

## Run it on your own Daml, in CI

Everything above needs somebody to run it. This does not:

```yaml
- uses: digital-asset/setup-daml@main          # or however you install the SDK
- uses: dominicrume/cantor8_kya_rails@main
  with:
    src: simple-token
    test: simple-token-test
```

On every pull request it makes each `assertMsg` and `ensure` vacuous in turn,
rebuilds the DAR, re-runs your suite, and writes a table of the fences no test
noticed into the job summary. The sealed record uploads as the
`daml-fence-assurance` artifact, and its head seal is printed in the summary so
the file a reviewer downloads can be matched to the run that made it.

It refuses rather than misleads: with no `daml` on PATH it fails with a named
error before anything is mutated, because a package reported as having no
findings and a package nobody checked look identical from the outside.

`fail-on-uncovered` is **off** by default. The first run against a real
repository is information, and a check that goes red on day one is a check
somebody disables on day two. Outputs — `fences`, `covered`, `uncovered`,
`head`, `record` — are there for when you want to gate on it.

---

## The same method, pointed at somebody else's code

The tests here answer one question: *would anything notice if a rule were
removed?* Nothing about that question is specific to this repository, so the
harness was generalised and run against three of OpenZeppelin's Canton
repositories — 69 authorisation fences across `canton-contracts`,
`canton-token-template` and `canton-stablecoin`.

**52 of the 69 can be made vacuous with every test still passing.** These are
not vulnerabilities: every fence is present and working. The finding is that the
suites would not notice if one were removed — which matters at the next change,
not today. Reported as
[canton-contracts#43](https://github.com/OpenZeppelin/canton-contracts/issues/43),
with the method, the controls and the three defects the harness had first
written up in [docs/findings-openzeppelin.md](docs/findings-openzeppelin.md).

The findings are also emitted as a sealed chain — one entry per fence, carrying
the file, the line, the verdict, the rule and the toolchain version:

```bash
python3 tools/assurance.py --src PKG --test PKG --for "Their Name"
```

[The record for `access-control-v1`](docs/findings/canton-contracts-access-control-v1.json)
drops onto [the verifier page](https://dominicrume.github.io/cantor8_kya_rails/)
like any other chain. Soften one verdict from `UNCOVERED` to `COVERED` before
you do, and the page names the entry it broke at — including when the person who
softened it is the one who wrote the report. An audit firm hands over a PDF you
believe because of who signed it. This is the same finding, checkable by the
client without trusting the auditor at all.

---

## Method

The folder structure is the agent architecture: one stage, one job, plain text as
the interface, every output an edit surface. `THE-RULES.md` is read before any
change; each stage carries its own `CONTEXT.md` and a `THE-JOB.md` with an
explicit **NOT** list.

That is why the spending rules are still in Daml and not in Python, and why
swapping the ledger backend was a one-file change.

---

## Licence

[MIT](LICENSE). Copyright (c) 2026 Rume Dominic (O'Rume Dominic Uririe).

The licence covers the code in this repository. It grants no rights in the
"KYA" and "KYA Rails" names or in the KYA Framework as a body of work.

## Credits

Built by **Rume Dominic** (O'Rume Dominic Uririe), Aston University — creator of
the KYA Framework.

`KyaMandate.daml` extends the Cantor8 hackathon starter `Mandate.daml`; the
organisers' toolkit is a dependency, never modified.
