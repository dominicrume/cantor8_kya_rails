---
name: canton-evidence-layer
description: The hard-won Canton and Daml facts this company owns. Use when designing or reviewing Daml, reasoning about what a ledger does and does not record, answering a reviewer about refusals, privacy, contention or upgrades, or deciding whether a claim about Canton is safe to make. Each fact names where it was learned and what checked it.
---

# The Canton evidence layer

The product is not a wallet. It is the evidence that an automated actor was
bounded, including the actions it was **refused**. Everything below was learned
by being corrected, and every item names the check.

## What a ledger does not record, precisely

A Daml check that refuses an action aborts during **interpretation at the
submitting participant**, before any message is sent. It produces no update and
involves no other node. Canton's Transaction Lifecycle reference names an
assertion violation under Failure Modes: rejected synchronously, no other nodes
involved. The rejection goes to the command completion service, which only the
submitting application can read, so it is not independent evidence either.

**The boundary, and it is narrow.** A rejection that reaches the **mediator** IS
independently observable: confirming participants' local verdicts are stored with
views blinded, and Splice Scan publishes accepted and rejected verdicts on
`/v0/events` since Splice 0.4.21. That covers anything that became a confirmation
request. A policy refusal never does.

Leonid corrected this on 30 October 2026, on forum topic 9114. An earlier version
claimed a refusal reaches no monitor at all. Checked against `scan.yaml` and
`LocalRejectError.scala` rather than taken on trust. `tools/refusal_detector.py`
carried the same over-broad sentence and was corrected with it.

So the sayable claim is: a monitor can score what happened and not what a control
stopped. The denominator is missing.

## The fix needs nothing from the monitor

Write the refusal as a **contract** rather than throwing it as an error. It is then
an ordinary created event and any adapter already carries it. `TryCharge` creates
`ChargeRefused`; `testRefusalIsOnLedgerAndNothingMoved` holds that no money moved.

**The privacy property is the part worth noticing.** Adapters commonly hash
contract payloads. With payloads hashed, a refusal record still arrives with its
`template_id` and its witness parties, so the **count** is visible while the
reason stays unreadable. An auditor gets the denominator without the monitor
learning what was refused.

## Authorization, not convention

- **Signatory, not observer.** Observer is a view; signatory is a requirement. The
  auditor on the signatory line means a create needs their authority, so a second
  journal cannot be opened behind their back, with no contract keys needed
  (`testASecondJournalIsPrevented`). The guardian as signatory of every `Attempt`
  means owner and actor together cannot archive one
  (`testArchivingAnAttemptLeavesANumberedHole`), and as signatory of the asset
  means the asset cannot move outside the journal
  (`testTheAssetCannotMoveOutsideTheJournal`).
- **The limit, and it is stated and tested.** A submitter holding **both** actor
  and guardian authority bypasses all of it: `testSubmittingAsTheGuardianDefeatsIt`.
  This is a control under segregation of duties and a convention without it.
- **A guardian on the signatory line does not gate a choice the owner controls.**
  Georgi Radev, 27 October 2026. Nothing had caught it because the test wallet
  carried no choices at all, and that minimality was doing work the design was
  being credited with. `testAnOwnerControlledChoiceStillBypassesTheJournal`.
- **The ledger names parties, not operators.** `PartyToParticipant` records
  participant IDs, hosting permissions and confirmation threshold. Different node
  IDs do not prove independent operators, and historical configuration identifies
  *eligible* confirmers, not who actually approved a given transaction. So the
  honest claim is that authority was split between **named parties**, not that
  those parties were independently operated. Independence stays an off-ledger
  assertion. Georgi Radev, forum topic 9323, third narrowing.
  `testTheLedgerNamesThePartiesAndNotTheirOperators`.

## Two-phase attempts, and what they buy

An `Attempt` is opened in its own transaction and consumed by the work. An attempt
left open **is** the evidence, so a record survives the work reverting. The
resolution carries a **salted**, length-prefixed sha256 commitment, so it cannot
lie about what the attempt was (`testTheResolutionCannotLieAboutTheAttempt`) and
the salt held off-ledger means the digest **hides** as well as binds
(`testTheCommitmentHidesAndNotJustBinds`).

## Contention is not batching

One journal serialises every attempt. N shards do not, and
`testOneJournalSerialisesAndTwoShardsDoNot` holds the original contract id and
uses it twice: one journal refuses, two shards allow both. `JournalSet` declares
the count so `missingShards` names a hidden one.

**Do not stretch this into an answer about batching.** Batching groups operations
into one transaction; contention is one contract being consumed. Adjacent is not
the same, and a Digital Asset engineer's batching criticism is not answered by
sharding. Claiming otherwise is the overclaim habit wearing new clothes.

## Cost, which is a reviewer's first question

Two mechanisms exist. `Refuse` is consuming, O(n) contracts. `RefuseSignalled` is
a non-consuming choice, O(1), following Simon Meier's EventLog pattern from
CIP-0112 (he made the point on cip-discuss on 30 October 2026).
`testTheCostOfBothMechanisms` runs 20 refusals through both: recording leaves 20
contracts, signalling leaves none, and the auditor reads back the same count and
the same positions from either.

**The cost of the cheap one, said unprompted.** Once events are pruned, a
signalled refusal and a refusal whose reason was withheld are the same thing on
the ledger, and the party who can prune is the party being audited.
`testASignalledRefusalLooksWithheldOnceEventsAreGone`. So the expensive mechanism
buys survival of pruning and nothing else. Worth it for evidence, not telemetry.

## Upgrade constraints that end designs

From the Canton 3.5.1 release notes, Smart Contract Upgrades, verbatim: *"It is
forbidden to add or remove a key definition from a template in a later version of
that template."* and *"This is enforced at package vetting time."*

`kya-rails-mandate 1.1.0` is vetted on DevNet, so **no later version of it can
ever add a key to an existing template.** Adding a key means a new template name
in a new package lineage, which is a different thing wearing the same name.
Separately, changing `--target` from 2.1 to 2.3 changes the package id on its own.

Canton's upgrade check also refuses a version that drops a data type its
predecessor had, which is why the desk's Daml modules (`KyaCycle`, `KyaInbound`,
`KyaQuote`) stay in `step-1-mandate` even though the desk moved out on
12 September 2026.

Contract keys exist from LF 2.3 but are **non-unique**, which is why they cannot
enforce single-journal uniqueness.

`DA.Crypto.Text` is an **alpha** module: *"It can change without notice."* If it
changes, every commitment already written becomes unverifiable, and there is no
migration path for a contract already on a ledger. Accepted because there is no
stable alternative in Daml-LF 2.1, and recorded in `SHORTCUTS.md` rather than
left silent.

## What is not claimed

- The journal counts **refusals, not attacks.** An attacker never opens an
  attempt, so the ledger refuses during interpretation and the counter stays at
  zero. `testAnAttackerWithOneStolenKeyLeavesNoCount` makes five attempts and
  shows the auditor seeing nothing. A guarded asset survives a single stolen key
  because the control is a conjunction; the evidence does not survive.
- **Write-time omission is unreachable by any commitment scheme**, because the
  producer chooses what to commit to. SPEC 6c says so in its own heading. On the
  path `Journal.daml` covers, an auditor reading `AttemptJournal` can name a
  withheld position, but it cannot see an attempt that bypassed it:
  `testAnUnjournalledAttemptIsStillInvisible`.
- **Prior art exists.** `khalydmaina/sentry` writes `RejectedTransfer` to Canton
  in Daml, with reasons and a ledger timestamp. See `docs/prior-art.md`.

## Hard boundaries in this repository

Python is stdlib only. Spending rules never move out of Daml. Receipt chain
canonicalisation stays byte-identical in `kya_chain.py` and `verifier.html`:
JSON with sorted keys, separators `","` and `":"`, sha256 over
`canonical(receipt_without_seal) + prev_seal`. Amounts are strings. Anything
mocked is labelled MOCKED. The organisers' toolkit at `~/hackathon-toolkit` is
read and called, never edited. No payment screen, webhook or wallet address comes
back into this tree; that belongs in the desk repo.

**Never run on a real ledger yet.** `TryCharge` has never executed on DevNet.
Every claim about on-ledger refusal is a design, not a fact. Blocked on
`C8_CLIENT_SECRET`, asked 31 August 2026. The command is written and dry-run
tested: `tools/prove_refusal_on_devnet.py`.

## Feedback contract

Report: the fact you relied on, where it was learned (person, date, source file),
the test or command that holds it, and the limit beside it. If a reviewer's
correction narrowed a claim, say what the claim is now, not what it was.
