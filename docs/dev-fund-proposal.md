# Proposal: KYA Receipt Chain — verifiable accountability for agent-operated payments

*Draft for the Canton Protocol Development Fund. Submitted as a PR to
`canton-foundation/canton-dev-fund` under `proposals/`. Requires a Tech & Ops
Committee champion.*

**Applicant:** Rume Dominic (O'Rume Dominic Uririe), MSc Artificial
Intelligence, Aston University. Creator of the KYA (Know Your AgenticAI)
Framework.
**Existing work:** https://github.com/dominicrume/cantor8_kya_rails (MIT)
**Contact:** dominicrume@gmail.com

---

## 1. Objective and scope

Agents on Canton already transact at volume. Every one of those transactions is
authorised by a key, and a key has exactly one answer: yes. Two things are
missing from that picture, and this proposal addresses both.

**First, a bounded mandate.** An agent should hold a written authority — a cap,
a counterparty allow-list, an expiry, an instant revoke — enforced by the ledger
rather than by the application submitting the command. Canton's authorisation
model is unusually well suited to this; almost nothing in the ecosystem uses it
this way.

**Second, and this is the part that generalises: a record of what was refused.**
Most systems log what succeeded. That answers *what happened*. It does not
answer *what was attempted and stopped, and which rule decided* — which is the
first question asked after an incident and the first question an auditor asks.
An agent that is refused has still acted, and today that action leaves no
artefact anywhere in the stack.

**In scope:**

1. **KYA Receipt Chain v1.0** — an open, ledger-agnostic format for
   tamper-evident receipts of agent actions, refusals included. Written
   specification, conformance vectors, and reference implementations.
2. **A reference mandate contract** — Daml templates enforcing cap, allow-list,
   expiry and revoke in the choice body, with a mutation-tested attack suite.
3. **An MCP server** so a language model can hold a mandate directly, and the
   refusal can be experienced rather than described.

**Out of scope:** custody, key management, payment licensing, and any claim to
be a money transmitter. This is an accountability and authorisation layer over
flows that already exist.

## 2. Technical approach

**The seal.** A receipt is a JSON object; the seal is
`sha256(canonical(body) + previous_seal)`, where canonical form is sorted keys,
`","`/`":"` separators and ASCII-only. Verification requires no network, no key
material and no trust in the producer — the reader recomputes. Editing any
receipt breaks that receipt and every receipt after it.

ASCII-only is not stylistic. Python escapes non-ASCII to `\uXXXX`; JavaScript's
`JSON.stringify` emits the raw character. The same receipt then hashes
differently in two languages, and a chain verifies on the server while failing
in the browser. The specification mandates the restriction and the reference
implementation refuses to seal a receipt that violates it.

**The mandate.** `KyaMandate` carries cap, allow-list, expiry and revoke, all
asserted inside the `Charge` choice body. `signatory owner, spender` means both
parties sign, so the agent consents to its own limits and cannot then remove
them. `Revoke` is consuming and creates nothing — there is no flag to race.
`ChargeRecord` puts each accepted charge on-ledger with `observer payee`, so a
counterparty can read what they were paid without gaining authority over
anything.

**What is already built and verified** (all reproducible from a clean clone):

| | Status |
| --- | --- |
| Specification | 176 lines, written to be implemented from the text alone |
| Reference implementations | 2 — Python (stdlib only) and browser JavaScript |
| Conformance vectors | 9, generated from the reference implementation |
| Daml attack suite | 11 scripts, every one named for the attack it proves |
| Mutation tested | yes — deleting the cap assertion turns a test red |
| Deployed on Cantor8 DevNet | package `6d13f9948206…`, vetted |
| Refusals returned by DevNet itself | over-cap, non-allow-listed payee, expired, revoked, agent-only cap raise |
| CI | conformance in both languages, vector reproducibility, MCP fences, Daml suite |
| Licence | MIT |

The expiry evidence is the piece worth singling out: the same mandate, same
payee, same amount, **accepted at T and refused at T+100s on a real clock**.
`expiresAt` is only a field until the assertion in `Charge` makes it a rule.

## 3. Architectural alignment

**It uses Canton for what Canton is uniquely good at.** The value here is not
that limits exist; it is that they are enforced by a ledger the agent does not
control, before the transaction can exist, with the counterparty able to see
only their own record. Privacy plus atomic settlement across parties who do not
trust each other is the combination Canton offers and very little else does.

**It is a building block, not an application.** `KyaMandate` is a template any
Canton application can hold alongside whatever it already does. The receipt
format is not Canton-specific at all — which is the point. A format adopted by
one repository is a library; a format with a specification, vectors and multiple
independent implementations is infrastructure.

**It reduces reliance on any single organisation**, which is the Fund's stated
aim. The specification is MIT, the vectors are the authority over the prose, and
the most useful contribution anyone can make is an implementation in another
language that proves it matches.

**It states its limits.** The specification's section 8 says plainly what the
format does *not* do: it is not signed, so it proves internal consistency and
not origin; it does not prove a rule was enforced, only that a decision was
recorded; and it makes editing detectable, not deletion. A security format that
overstates itself is worse than none.

## 4. Milestones and deliverables

**M1 — Specification hardening and a third implementation** *(6 weeks)*
Independent implementation in Go or Rust, produced from the specification text
alone and proved against the vectors. Any ambiguity found becomes a
specification fix and a new vector. Vector set expanded to cover empty and
maximal fields, deep chains, and misaligned `prev` links.

**M2 — Mandate library and audit** *(8 weeks)*
`KyaMandate` packaged for reuse: per-period limits in addition to the total cap,
documented upgrade path, and a published threat model. External review of the
Daml. Mutation testing extended to every fence, run in CI.

**M3 — Agent integration and reference deployment** *(6 weeks)*
MCP server hardened for real use. A worked end-to-end deployment on DevNet with
Canton Coin actually moving through the mandate, not merely recorded against it.
Documentation aimed at a team adopting this in a week.

**M4 — Adoption** *(ongoing, 12 weeks)*
Two independent teams building on the format, with their feedback folded into
v1.1. Workshop material for developer sessions.

## 5. Acceptance criteria

Each milestone is a pull request, publicly reviewable, and complete only when:

- **M1** — the third implementation passes all conformance vectors in CI, from a
  clean checkout, with no changes to the reference implementations. Every
  specification ambiguity it exposed is fixed and covered by a new vector.
- **M2** — an external reviewer's findings are published with responses. Every
  fence has a mutation test that goes red when the fence is deleted; CI enforces
  this. Per-period limits ship with tests named for the attacks they prove.
- **M3** — a Canton Coin transfer completes through a mandate on DevNet, with
  the sealed receipt chain for it published, verifiable offline by a third
  party. A developer outside the project reproduces the deployment from the
  documentation alone.
- **M4** — two named projects, not authored by the applicant, have adopted the
  format. v1.1 ships with their feedback addressed.

Acceptance is deliberately falsifiable. "A third party reproduces it" and
"deleting a fence turns a test red" are checkable by the Committee without
taking the applicant's word for anything — which is the same standard the
receipt format itself is built on.

## 6. Funding request and milestone breakdown

Denominated in Canton Coin, released on milestone acceptance.

| Milestone | Deliverable | Weeks | Share |
| --- | --- | --- | --- |
| M1 | Spec hardening + third implementation | 6 | 20% |
| M2 | Mandate library, per-period limits, external audit | 8 | 30% |
| M3 | Agent integration + reference deployment | 6 | 25% |
| M4 | Adoption, v1.1, workshop material | 12 | 25% |

*[Total amount to be set with the champion. M2 includes an external Daml review,
which is a third-party cost rather than applicant time and should be quoted
separately.]*

Work to date has been unfunded. The applicant is not requesting retrospective
payment for it; it is offered as evidence that the milestones above are
deliverable.

---

## Why the applicant

I did not arrive at this from theory. I run a payout business whose principal is
in one country and whose operations are in another, and its binding constraint
is exactly the problem above: someone must execute on the ground, and cannot
safely be given unbounded authority over the float. The failure mode is not
theft — it is the message *"change of account, send it here instead,"* which
does not require the operator to be dishonest, only convinced. In agent terms
that is prompt injection under a different name.

I am the first user of this work, which means the incentive to make the
guarantees real rather than presentable is not an abstract one.

Alongside this I filed four findings against the Cantor8 hackathon toolkit,
with fixes, including a default-argument binding that silently sends the wrong
ledger user and returns a 403 naming neither the user nor the cause.

**Verification:** every claim in this proposal is reproducible from
`https://github.com/dominicrume/cantor8_kya_rails` at the commit referenced in
the PR. `daml test`, `tests/conformance.py`, `tests/conformance.js` and
`tests/mcp_smoke.py` run from a clean clone with no network and no install.
