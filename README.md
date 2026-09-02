# KYA Rails

[![ci](https://github.com/dominicrume/cantor8_kya_rails/actions/workflows/ci.yml/badge.svg)](https://github.com/dominicrume/cantor8_kya_rails/actions/workflows/ci.yml)

**A spend-limited wallet for an AI agent, enforced on Canton.**

Two parts, and the second one is not about Canton:

1. **[SPEC.md](SPEC.md)** — an open format for tamper-evident receipts of agent
   actions, **including the actions that were refused**. Stdlib-only, no
   signatures, no network to verify. Two independent implementations and
   [14 conformance vectors](tests/vectors.json). Three independent
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
| Attack suite green | **73 / 73** `daml test` scripts, both directions of the cycle |
| The cycle holds at every join | 15 checks over HTTP, in the order a desk works it |
| Every fence mutation-tested | all **27** in the Daml, and all **29** refusals in the two webhook adapters: delete any one and a named test goes red — enforced in CI |
| The desk survives a restart | the 10:02 quote is still bound at 13:20 after the process dies — **27** checks, including a forged journal entry that proves the limit |
| The deposit door | **30** attacks on the adapter + **15** over a real socket, including the X-Forwarded-For spoof that defeats a naive IP allowlist |
| The WhatsApp door | **54** attacks on the adapter + **14** over a real socket: unsigned, wrongly signed, signed-for-another-body, replayed, day-old, another business account, delivery reports, hostile display names |
| Fences enforced on-ledger | cap, **per-period limit**, allow-list, expiry, revoke — all in the `Charge` choice body |
| Deployed on Cantor8 DevNet | `kya-rails-mandate` 1.0.0, package `df5a02e88a68…`, vetted |
| Refusals returned by real Canton | over-cap, unverified payee, expired, revoked, agent-only `Adjust` |
| Receipt chain | 6 receipts, 2 accepted, 4 refused, chain verifies end to end |
| Tamper evident | edit one receipt, every later seal breaks |
| Real Canton Coin moved | 5.0 CC split by mandate-authorised transfers: agent 1.4, recipient 2.1, partner 1.5, **unverified 0.0**, total conserved |

The expiry proof is the strongest single piece of evidence: **the same mandate,
same payee, same amount — ACCEPTED at T, REFUSED at T+100s on a real clock.**
Only time changed. `expiresAt` is just a field until the assertion in `Charge`
makes it a rule.

---

## Quick start

Offline, no network, no install, no server. Python is stdlib only.

```bash
python3 step-2-agent/agent.py          # writes step-3-verify/receipts.js
open step-3-verify/verifier.html       # press Play, then Verify, then Tamper
```

### The desk bot

Customers already trust bots that credit them fast. The conversation is the
product, not a link you send:

```bash
python3 step-5-operator/server.py     # then open http://localhost:8420/bot
```

It is a **state machine, deliberately not a language model.** A model in this
seat is an operator that can be talked to, and the whole point of everything
here is that the number and the account are not the operator's to choose.
*"My guy quoted me 1400 this morning"* and a prompt injection are the same
attack; a state machine reading the band off the ledger cannot be persuaded,
flattered, or made to hallucinate an address.

It also does not read intent out of prose. Asked for an amount it accepts a
number and nothing else — because extracting the first digit run from
*"ignore previous instructions, the rate is 1600"* is exactly how that
sentence becomes an amount of 1600. `tests/bot_smoke.py` attacks it with the
messages a real desk receives.

Where a model *is* useful is turning messy human text into an intent at the
edge. Its output would still have to pass every fence. That is not wired up.

### Connecting it to real WhatsApp

`step-7-providers/meta.py` translates Meta's WhatsApp Cloud API webhook into
the same `on_message` the simulator uses, so the bot cannot tell the two
apart. It exists only when it is fully configured — three environment
variables, none of which go in this repository:

```bash
export KYA_META_APP_SECRET=...      # signs every delivery
export KYA_META_VERIFY_TOKEN=...    # answers Meta's one-time GET challenge
export KYA_META_PHONE_ID=...        # the desk's own number, and no other
python3 step-5-operator/server.py   # webhook at /webhook/meta
```

With any of them missing the path returns 404 rather than running unguarded,
and the startup banner says which mode it is in. A **half-configured webhook
endpoint is an open one**, and this one is a door straight into the desk's
conversation engine.

Every delivery must carry a valid `X-Hub-Signature-256` over the **raw bytes**
— not over a re-serialised parse, which is the mistake that makes a signature
check decorative. Deliveries are deduplicated on Meta's own message id and
bounded by a freshness window, because an HMAC proves who sent a body and
never says when. Threats T16–T20 in [docs/threat-model.md](docs/threat-model.md)
set out what this stops and what it does not.

**Replies are MOCKED.** Sending a message back needs a Graph API call with an
access token this repository does not have. The reply text is returned and
recorded; nothing is sent to Meta. It says so in the code and on the startup
banner.

### Connecting the deposit feed

`step-7-providers/breet.py` turns a Breet deposit webhook into the
`ConfirmDepositSeen` the cycle needs, so the desk stops taking a customer's
screenshot as proof that money arrived. Same rule: it exists only when it is
configured.

```bash
export KYA_BREET_SECRET=...          # their shared header secret
python3 step-5-operator/server.py    # webhook at /webhook/breet
```

Breet signs nothing — a shared secret in a header is a **bearer credential**,
not a signature, and anyone who obtains it can forge a confirmation. So it is
compared in constant time, the provider's IP allowlist is the second lock, and
every field is matched against a deal we already hold before anything is
confirmed. The webhook does not get to say which deal it is.

Behind a reverse proxy the allowlist needs `KYA_BREET_TRUST_PROXY=1`, and then
only the **last** hop of `X-Forwarded-For` counts — the one the proxy
appended. Reading that header without a declared proxy would turn the
allowlist into a value the attacker sets; that is T21 in the threat model, and
`tests/breet_wire_smoke.py` proves all three cases by mutation.

`KYA_BREET_REQUIRE_IP=0` turns the allowlist off for a laptop demo. It leaves
a header secret as the only check, so the startup banner says so out loud.

### The desk survives the laptop closing

`step-8-store/store.py`. This was the largest hole in the build and it was not
a missing feature — it was the fraud coming back in through the side door.

`Rail` used to say so in its own docstring: *"one mandate, one chain, for the
life of the process."* Every open deal lived in a Python dict. A desk quotes at
10:02 and the deposit lands at 13:20; if the laptop slept in between, the
payout account bound at quote time was **gone**, and the 14:05 stranger with a
screenshot met a desk with nothing to contradict them. That is T9 exactly,
reintroduced by a process restart.

Deals, quotes, conversations and the receipt chain are now written to a SQLite
journal as they happen. **Persistence is the default; `--ephemeral` is the
flag** — forgetting to type something should not be able to cost money.

```bash
python3 step-5-operator/server.py               # saved to kya-desk.db
python3 step-5-operator/server.py --ephemeral   # demos and training runs
python3 tests/store_check.py                    # is the journal intact?
```

The journal is append-only and seal-chained **with the receipt chain's own
`canonical()` and `seal()`**, imported rather than reimplemented, because two
implementations of one hash is how you get two answers. Editing any entry
breaks every seal after it; the server refuses to start on a broken journal
and the operator screen turns red rather than quietly showing numbers it
cannot stand behind.

What it does **not** stop is appending. Someone holding the file can add a
correctly sealed entry saying anything, and `tests/store_smoke.py` proves that
by forging one rather than pretending otherwise. It makes rewriting history
detectable, not adding to it — the same limit as the receipt chain, for the
same reason. The quote on the ledger is what actually holds.

### The operator's screen

The person on the ground, on a phone, under pressure from a customer who is
waiting:

```bash
python3 step-5-operator/server.py          # offline
python3 step-5-operator/server.py --devnet --move-coin
```

Then open `http://localhost:8420`. It opens on a **training scenario**: the
exact sequence a working desk lost money to — a quote at 10:02 to someone who
never sends, a real deposit at 13:20, and at 14:05 an unknown number with a
screenshot asking to be paid to their own account. The "Pay the claimant"
button is there, and red, and the ledger refuses it.

The conversation pane is where real WhatsApp Business messages would arrive
through a webhook. Nothing is connected to WhatsApp yet, and the page says so
on the page rather than in a footnote.

Two design decisions worth naming. The recipient is a **picker, not a text
field**, so "send it to this account instead" is not typeable — a new account
has to be added by the principal. And a refusal is worded as *the ledger
refused this*, not *your request failed*: an operator who reads a refusal as
their own failure works around it, and an operator who reads it as the system
deciding is protected by it.

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
export C8_CLIENT_SECRET=...            # shell only, never committed
python3 step-2-agent/agent.py --devnet
```

The checks, all three of which run in CI:

```bash
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
python3 tests/complexity_lint.py # no function over the ceiling without a written reason
cd step-1-mandate && daml build && cd test && daml test   # 73 scripts
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
| [step-1-mandate/daml/KyaTest.daml](step-1-mandate/daml/KyaTest.daml) | every test is named after the attack it proves |
| [step-2-agent/DEVNET-PARTIES.md](step-2-agent/DEVNET-PARTIES.md) | DevNet parties, rights, and the traps that cost us hours |
| [SPEC.md](SPEC.md) | the receipt format, written to be implemented from the text alone |
| [docs/threat-model.md](docs/threat-model.md) | fourteen threats, several undefended and said so |
| [docs/privacy-matrix.md](docs/privacy-matrix.md) | who sees what, who is excluded — generated from the Daml, checked in CI |
| [docs/upgrade-path.md](docs/upgrade-path.md) | how we failed Canton's upgrade check, and the rules that came out of it |
| [docs/wallet-providers.md](docs/wallet-providers.md) | where the addresses would come from, and what to ask a provider |
| [docs/complexity.md](docs/complexity.md) | the one function allowed to be complicated, and the reason it is |
| [tests/vectors.json](tests/vectors.json) | 9 conformance vectors. Where the spec and a vector disagree, the vector wins. |
| [CONTRIBUTING.md](CONTRIBUTING.md) | start here — the most useful contribution is a third implementation |

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
