# Prior art, and who got there first

*Compiled 8 October 2026. This file exists because the alternative is being
corrected in public by someone who did this search before we did.*

Everything here is marked **VERIFIED** (checked directly from a primary
source while writing this file) or **REPORTED** (found by a research pass and
not independently confirmed here). A REPORTED line is a lead, not a fact.

---

## The sentence we can no longer say

> "Nobody else records what the agent was refused."

That is false, and it was false before the hackathon ended. It has been said
in outreach drafts and in `what-this-proves.md`. It is corrected in both.

## What is actually defensible

Three things together, and the word *together* is doing the work:

1. The refusal is a **first-class ledger contract** that commits while the
   payment does not move (`KyaMandate.TryCharge`, `ChargeRefused`).
2. The chain is verified by **three independent implementations** in Python,
   JavaScript and Go, agreeing on 20 conformance vectors.
3. Refusals can be **disclosed without the accepted payments**, and since
   SPEC 6c the outcome of every withheld entry is covered by one anchorable
   digest.

Any one of those on its own has prior art. The combination does not, as far
as this search found. Claim the combination; claim nothing wider.

---

## On Canton, in Daml, at the same time

**`khalydmaina/sentry`** — *"Ledger-enforced spending limits for AI agent
wallets. Daml on Canton. HackCanton Season 3 entry."* Repository created
**19 September 2026**, last pushed 3 October 2026. **VERIFIED**: 14 code
matches for `RejectedTransfer` across `main/daml/Wallet/Policy.daml`,
`main/daml/Wallet/Records.daml`, the README, the demo script and the
frontend. Its agent has a probe mode that submits forbidden commands and
shows the ledger refusing them.

So: **a second Canton project writes refusal records to the ledger.** Our
`TryCharge` landed 12 September, a week earlier, which is worth knowing and
is not worth leading with. What sentry does not have is a hash chain, a
cross-language verifier, or selective disclosure.

**`pkaysantana/canton-agent-mandate`** — allowlist, cumulative cap, expiry,
revocation, deliberately kept in Daml rather than Python. **REPORTED**:
rejections surface as `DAML_FAILURE` rather than as records, so the gap we
describe is still open there.

**`mmxMichelle/AI-agent-wallet` (GuardRail Wallet)** and **Team Mandate**
(1st place, same D1 track) — both spend-limited agent wallets on Canton.
Team Mandate's own thesis, in their words, is that a mandate should be a
*ledger invariant* rather than a rule asking the agent to behave. That is our
thesis, arrived at independently, and they won with it.

## Published before we started

**CAP-SRP, VeritasChain Standards Organization.** Spec v1.0 published
**17 February 2026**, CC BY 4.0, with a reference implementation. SHA-256
hash chains, Ed25519 signatures, Merkle trees, RFC 3161 anchoring, optional
SCITT transparency, and a **Completeness Invariant**:
`GEN_ATTEMPT = GEN + GEN_DENY + GEN_ERROR`. **REPORTED**, and the closest
published prior art to the whole thesis. It is about content-generation
refusals rather than payment refusals, and it had the answer to the
completeness objection eight months before we did. SPEC 6c is our version of
that answer and credits it there.

**Authority-Inference Separation (AIS)**, Gong, Samawi and Medda,
arXiv 2608.30519, submitted **31 August 2026**, two days after the
hackathon. **REPORTED**: a deterministic control plane validates mandate and
accountability lineage before granting temporary executable authority, with
the blockchain recording portable settlement evidence. Evaluated against 36
synthetic authorization attacks. No Canton or Daml.

**A Black Box for Agentic Processes** (arXiv 2609.04017) and **Agent Flight
Recorder** (arXiv 2609.01931) — blockchain-anchored audit trails for agent
behaviour. **REPORTED**. Neither focuses on refusals.

## Commercial, and better funded

**REPORTED** throughout this section.

- **Circle Agent Stack** (announced 11 May 2026): agent wallets with
  "predefined permissions, spending controls and policy guardrails". Circle
  is also a Canton participant, which makes them simultaneously the best
  prospect and the most dangerous competitor.
- **Coinbase Agentic Wallets** (11 February 2026): TEE-isolated keys,
  programmable spending limits, screening on every transaction.
- **Amazon Bedrock AgentCore Payments** (preview, April 2026), x402-based,
  session-level spending limits.
- **Catena Labs**: $48m raised, and **OCC preliminary conditional approval
  for Catena Trust Bank, N.A. on 18 September 2026**. A chartered bank whose
  reason to exist is agent accountability is a larger competitive fact than
  any repository on this page.

None of them, as far as this search found, ships a disclosable refusal
record. That is the opening, and it is an opening in someone else's product,
which is usually a feature request rather than a company.

## The naming problem

**VERIFIED**: **"Know Your Agent" (KYA) is an established industry term**,
originating with Skyfire around 2024 and now used as an ecosystem label.
**Experian has a Know Your Agent framework with Skyfire's KYA protocol as its
identity layer.** There is a `kyapay.org`.

This is why "Know Your AgenticAI" is always written in full and never
abbreviated to KYA. It is also an opportunity rather than only a risk:

> KYA answers *who is this agent and what may it do*.
> We answer *what did it try that it was not allowed to do*.

Those are complementary. The honest positioning is the layer underneath
theirs, and saying so is more credible than pretending the category is empty.

## Where the regulatory argument is weaker than we have said

**REPORTED**, and it should be checked against primary sources before any of
it goes in a deck.

- **The EU AI Act probably does not apply.** Annex III does not list payments
  or treasury, so a spend-limited agent wallet is likely not a high-risk
  system, and Articles 12, 14 and 26 would not bind it. Article 26(6) also
  points financial institutions back to records they already keep under
  existing financial services law.
- **The stronger hook is FINRA**: Rule 3110 read with 4511 and SEC 17a-4, as
  applied to AI agents in FINRA's 2026 Annual Regulatory Oversight Report,
  which names agents "acting beyond the user's actual or intended scope and
  authority". In force now. It creates no new rule, so the claim is "your
  examiner will ask for this", never "the law requires this".
- **Do not claim a Canton ledger satisfies SEC 17a-4(f).** It has its own
  audit-trail and third-party-access conditions.
- **OFAC 31 CFR 501.604** does literally require reporting rejected
  transactions, within 10 business days. It is the best evidence that
  "evidence of refusal" is a recognised regulatory artefact, and a bad sales
  hook, because the firms it binds already own sanctions-screening systems
  that produce exactly that report.

---

## How to use this file

Read it before any pitch. Then say the three defensible things and stop.

The reason to publish a list of people who got somewhere first is the same as
the reason `SHORTCUTS.md` exists: a claim that survives a stranger checking it
is worth more than a claim that sounds better.
