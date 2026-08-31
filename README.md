# KYA Rails

[![ci](https://github.com/dominicrume/cantor8_kya_rails/actions/workflows/ci.yml/badge.svg)](https://github.com/dominicrume/cantor8_kya_rails/actions/workflows/ci.yml)

**A spend-limited wallet for an AI agent, enforced on Canton.**

Two parts, and the second one is not about Canton:

1. **[SPEC.md](SPEC.md)** — an open format for tamper-evident receipts of agent
   actions, **including the actions that were refused**. Stdlib-only, no
   signatures, no network to verify. Two independent implementations and
   [9 conformance vectors](tests/vectors.json).
2. **A reference application** — the spend-limited wallet D1 asks for, with the
   limits enforced in a Daml choice body.

Cantor8 *Build on Canton* hackathon, challenge D1.
Built with the KYA Method: Promise it. Attack it. Inspect it. Prove it.

---

## The problem

A trading desk gives an AI agent authority to settle trades. An attacker talks
the agent into paying a wallet the desk never authorised. That is **payout
redirection**, and it costs desks **$3,000–$5,000 per incident**.

Every mitigation people reach for first — a limit in the agent's prompt, a check
in the application code, a policy document — is the agent policing itself. Edit
the file, or talk the agent past its own check, and the money is gone.

## The approach

The mandate is a Daml contract on Canton: a **cap**, a **counterparty
allow-list**, an **expiry**, and a **revoke**. All four are asserted inside the
`Charge` choice body, so Canton validates them *before the transaction can
exist*. There is nothing to roll back and nothing to detect afterwards, because
the spend never happens.

Both parties sign it (`signatory owner, spender`), so the agent consents to its
own leash and then cannot take it off. We tested exactly that: the agent tried to
raise its own cap and the ledger answered *"missing authorization from owner"*.

**Every attempt is sealed into a receipt chain — including the ones the ledger
refused.** Most systems log what succeeded. This one proves what was *tried and
stopped*, which is the artefact an auditor actually asks for.

---

## The numbers

| Claim | Evidence |
| --- | --- |
| Attack suite green | **11 / 11** `daml test` scripts, mutation-tested |
| Fences enforced on-ledger | cap, allow-list, expiry, revoke — all in the `Charge` choice body |
| Deployed on Cantor8 DevNet | package `6d13f9948206e73684461925d830261bff5a5d265191b5c764258c98f40dc241` |
| Refusals returned by real Canton | over-cap, unverified payee, expired, revoked, agent-only `Adjust` |
| Receipt chain | 6 receipts, 2 accepted, 4 refused, chain verifies end to end |
| Tamper evident | edit one receipt, every later seal breaks |
| Real Canton Coin held | 5.0000 Amulet, unlocked, in `kya-agent-1` |

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
cd step-1-mandate && daml test   # the on-ledger fences, 10 scripts
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
- **The coin does not move.** `Charge` records the spend on-ledger; it does not
  transfer Canton Coin. The 5 CC in `kya-agent-1` is untouched. Every receipt
  says `Amulet (recorded, not transferred)`.
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
| [step-1-mandate/daml/KyaMandate.daml](step-1-mandate/daml/KyaMandate.daml) | the contract. The fences are here. |
| [step-1-mandate/daml/KyaTest.daml](step-1-mandate/daml/KyaTest.daml) | every test is named after the attack it proves |
| [step-2-agent/DEVNET-PARTIES.md](step-2-agent/DEVNET-PARTIES.md) | DevNet parties, rights, and the traps that cost us hours |
| [SPEC.md](SPEC.md) | the receipt format, written to be implemented from the text alone |
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
