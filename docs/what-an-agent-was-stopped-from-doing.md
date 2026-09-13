# What an agent was stopped from doing

*A note on auditability for agentic payments. September 2026.*

The industry says that putting agents on a blockchain makes them auditable.
Every decision recorded on an immutable ledger, recallable later.[^1]

Half of that is true. The missing half is the half a regulator asks for.

## What a ledger actually records

A ledger records what happened. It does not record what was prevented.

An agent pays, the payment settles, the record exists. An agent tries to pay
and a rule stops it, and the usual implementation aborts the transaction.
Nothing is written. The ledger afterwards looks exactly as it would if the
agent had never tried.

In Daml this is exact, not approximate. A failed `assertMsg` aborts the whole
transaction, so a refused action leaves no trace on Canton at all.

The asymmetry runs the wrong way.

| | corroborated by | worth as evidence |
|---|---|---|
| payments that went through | the ledger | high |
| payments that were stopped | the operator's own logs | the operator's word |

The half you can check independently is the half nobody asks about. The half
everybody asks about is written by the party under examination, about itself.

## Why this is now a compliance problem, not a design preference

EU AI Act Article 12 requires high-risk AI systems to log events automatically
across their lifecycle. DORA requires integrity-protected audit trails. Read
together, they move the burden from *having* a control to *evidencing that it
operated*.[^2]

A control that operates produces refusals. If refusals leave nothing behind,
the control cannot be evidenced.

"Our agent has a spending cap" describes a configuration. "Here are the eleven
times it hit the cap last quarter, and you can check each one without trusting
us" is evidence.

## What is already being done, and why it is not enough

This is not an unnoticed gap. Work on hardening x402 emits an event for every
control decision, allowed or policy-blocked. Each carries a timestamp, the
agent, the outcome, and an HMAC link to the previous entry.[^3] That is a
hash-chained log of refusals, and it beats no log at all.

It does not close the gap. The reason applies equally to the first version of
our own work, which is why it is worth saying plainly: **the application still
writes the log.**

A hash chain makes an existing entry tamper-evident. It cannot show that an
entry was never written. An operator who omits a refusal produces a chain that
verifies perfectly.

Tamper-evidence and completeness are different properties. An auditor needs the
second one.

## The fix, on Canton specifically

Make the refusal a transaction that succeeds.

Instead of aborting, the choice evaluates the rule and commits either way. If
the rule passes, it pays. If the rule fails, it creates a rejection record and
moves no money. Both paths commit, so the refusal has a contract id and a
ledger time that the operator did not write, and cannot invent, backdate or
reorder afterwards.

Canton is the right place for this, for a reason public chains cannot match.
Sub-transaction privacy means a refusal record is not public merely by
existing. An auditor can be granted observer status on the specific contracts
they are entitled to see.[^4]

In the reference implementation the auditor is named once, by the owner, when
the mandate is written. Every later refusal is readable by them and by nobody
else. They never have to ask the operator for it, which is the difference
between evidence and a report: an auditor who must request the refusals is
being handed what the operator chose to hand over.[^6]

On a transparent chain, auditability and confidentiality trade against each
other. Here they do not.

That matters to the institutions already there. Franklin Templeton brought its
Benji tokenized fund to Canton in November 2025, in a network that includes
Goldman Sachs and Tradeweb.[^5] For those firms, "publicly recallable using
block explorers" is not a feature.

## What this still does not do

Stated here rather than left to be discovered, because a claim that oversells
itself is worse than none.

- **An attempt that was never submitted leaves nothing behind.** This makes a
  refusal that happened impossible to fake, delete or move in time. It does not
  make one that never reached the ledger appear.
- **A rejection record is archivable by its signatories.** The honest claim is
  that removing one is itself a ledger event, not that it cannot be removed.
- **It proves a rule fired, not that a rule is correct.** Whether the fence
  would have stopped the payment had the record not been written is a fact
  about code, not about records.

## What it is

An evidence layer that sits under an agent platform. A platform decides what an
agent may do. This is the record of what it tried and was refused, sealed so
the other side can check it without trusting whoever ran the agent.

The reference implementation is MIT, has no dependencies, and is about twenty
lines in any language.

Refusals can be handed to a regulator on their own. The payments stay withheld,
their positions stay visible, and nothing can be quietly removed from what the
regulator is shown.

---

[^1]: Sandy Kaul, Head of Digital Assets and Innovation, Franklin Templeton,
      *Agentic AI: The Killer Use Case for Blockchain and Crypto*, 2026. The
      claim is not unusual; it is the standard formulation.
[^2]: EU AI Act Article 12 (record-keeping); DORA audit trail obligations.
[^3]: *Hardening x402: PII-Safe Agentic Payments via Pre-Execution Metadata
      Filtering*, arXiv:2604.11430.
[^4]: Canton Network privacy model: sub-transaction privacy, with observer
      rights grantable per contract. `docs.canton.network/overview/learn/privacy-model`
[^5]: Franklin Templeton extended its Benji platform to Canton, November 2025.
[^6]: `KyaMandate.daml`, and the tests that hold it to this:
      `testAuditorSeesTheRefusalWithoutAsking`, `testOnlyTheNamedAuditorSeesIt`
      (a stranger and the refused payee both see nothing), and
      `testNoAuditorDisclosesToNobody` (the default discloses to no one, and
      the owner still holds their own record).
