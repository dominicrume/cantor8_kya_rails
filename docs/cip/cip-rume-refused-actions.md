## Title

<pre>
  CIP: ?
* Layer: Applications
  Title: A ledger record for refused actions
  Author: O'Rume Dominic Uririe
* Discussions-To: https://lists.sync.global/g/cip-discuss/topic/cip_tbd_a_ledger_record_for/122004432
* Comments-Summary: No comments yet
  Status: Draft
  Type: Standards Track
  Created: 2026-10-26
  License: CC0-1.0
* License-Code: MIT
</pre>

## Abstract

A Canton application records what it did. It has no standard way to record
what it was stopped from doing, and the two are not the same evidence.

When a Daml check refuses an action, the transaction aborts during
interpretation at the submitting participant, before any message is sent, so no
other node is involved at all. The rejection is delivered to the command
completion service, which only the submitting application can read, so the party
whose conduct is in question is also the only party holding the record of it.

This CIP specifies a small interface and two templates that make a refusal an
ordinary ledger contract, so that it is carried by the same stream, the same
privacy model and the same tooling as everything else. It adds a counter of
attempts, so an auditor can divide by a number the operator cannot restate,
and it keeps the reason for a refusal separable from the count, so a
transparent denominator does not force a transparent numerator.

It changes no protocol behaviour, requires no new Ledger API service, and
needs no participant configuration. It is a Daml package an application takes
as a data dependency.

## Copyright

This CIP is licensed under CC0-1.0:
[Creative Commons CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/)

## Motivation

An institution on Canton that is subject to transaction-monitoring or
operational-resilience obligations is asked two questions by an examiner. What
did you do, and what did you stop. Canton answers the first well. It does not
currently answer the second at all.

The gap is structural rather than a missing feature:

1. **A refused action produces no update, and involves no other node.**
   `assertMsg` and `ensure` abort during interpretation at the submitting
   participant. Canton's Transaction Lifecycle reference names this case under
   Failure Modes: the engine "rejects the command (e.g., contract not found,
   authorization failure, assertion violation)", "the command is rejected
   synchronously before any messages are sent", and "no other nodes are
   involved". No confirmation request is sent, so there is no mediator verdict
   and nothing for the Update service to deliver.
   https://docs.canton.network/overview/reference/transaction-lifecycle
2. **The completion stream is not independent evidence.** A rejection appears
   on the command completion service, visible to the submitting application.
   The party being audited is the only party who can see it, which is the
   definition of a record an auditor cannot rely on.
3. **An application's own log is also the application's.** Any off-ledger log
   written by the application is written by the party the evidence concerns.
   A hash chain over that log makes editing it detectable and omission from it
   undetectable, because the producer chooses what to commit to.

4. **What is already visible is a different stage.** A rejection that reaches
   the mediator is independently observable. Each confirming participant
   re-interprets the views it hosts and sends a local verdict; the reject codes
   separate the ordinary from the hostile, the latter raised as an
   `AlarmErrorCode`
   (`community/base/src/main/scala/com/digitalasset/canton/protocol/LocalRejectError.scala`).
   The mediator stores the verdicts with views blinded, and Splice Scan has
   published accepted and rejected verdicts on `/v0/events` since Splice
   0.4.21. None of that reaches a refusal decided inside the submitter's own
   interpretation, which is where every application-level policy check lives,
   and which by the reference above never becomes a confirmation request.

This is observable today in deployed work. The open-source Canton ingestion
adapter published under Dev Fund milestone #302 calls
`/v2/updates/get-updates-page`, `/v2/state/active-contracts` and
`/v2/state/ledger-end`, and contains no reference to completions or
rejections. It is a correct adapter. A refused action simply is not in the
data it reads.

The consequence is narrow and worth stating precisely. A monitoring or
risk-scoring product built on Canton can report what happened. It cannot
produce the sentence "we blocked fourteen of nine hundred attempts", because
neither number is available to it.

## Specification

Three parts. An interface that constrains when work may run, a counter, and a
record.

### 1. The `Journalled` interface

```daml
data JournalledView = JournalledView
  with
    owner : Party
    guardian : Party
  deriving (Eq, Show)

interface Journalled where
  viewtype JournalledView

  perform : Update ()

  choice Perform : ()
    controller (view this).owner, (view this).guardian
    do perform this
```

An application implements `Journalled` on whatever it wants journalled and
names the `guardian` as a signatory of that template. `perform` is the
application's own work; this specification never inspects it.

The guardian's authority is reachable only from inside an attempt resolution.
An application holding only the owner's authority cannot exercise `Perform`,
so the ledger refuses the action rather than discouraging it.

Implementations MUST verify that the guardian named in the view really is a
signatory of the implementing contract. A view that names a guardian which is
not on the signatory line looks guarded and is not.

Implementations MUST also ensure the implementing template exposes no choice
that can effect the guarded work, or consume the guarded contract, without the
guardian's authority. A guardian on the signatory line does not gate a choice
the owner controls: controllers authorize the exercise, and a consuming choice
archives its own contract on the controller's authority, because signatory
authority is required to create rather than to archive this way. Auditing every
choice on the template and on its other interfaces is part of conforming, not
an optional review afterwards.

The reference implementation makes that requirement checkable rather than
stated. `testAnOwnerControlledChoiceStillBypassesTheJournal` builds an asset
that satisfies every other guarantee here, the guardian genuinely on its
signatory line and the interface route refused without that authority, and then
moves it outside the journal through one ordinary owner-controlled choice.

### 2. The attempt counter

One contract per `(owner, actor)` pair, carrying the number of attempts that
have passed through it and the positions that were refused. It is consumed and
recreated by every attempt, so the count is the ledger's rather than the
application's.

The auditor, where one is named, MUST be a signatory rather than an observer.
A create requires the authority of every signatory, so with the auditor on
that line a second journal cannot be opened without them. This converts
uniqueness from something detected after the fact into something prevented.
Contract keys cannot do this: keys returned in Daml-LF 2.3 are explicitly
non-unique and negative lookups are not validated.

Where no auditor is named, the guarantee degrades to detection, and
implementations MUST NOT describe it otherwise.

### 3. The refusal record

A contract carrying the action, the detail, the rule that refused it, the time
and the optional auditor. It is created in a transaction that contains nothing
else, so no later step can revert it.

The counter holds refusal **positions** and not refusal **reasons**. The
reason lives on the record, which can be withheld. A withheld reason then
leaves a position with no record against it, which is exactly the detection
this specification exists to provide.

**Two mechanisms, and which one to use.** The arguments of an exercised choice
are already visible to that exercise's informees, so a contract whose only job
is to carry them is redundant for signalling. CIP-0112 specifies this for the
token standard: an `EventLog` interface that emits "standalone events as
side-effect free non-consuming choices", whose "purpose is to make the call
arguments visible to its observers, nothing more". Implementations SHOULD
therefore offer a signalling form that creates no contract. The reference
implementation's `RefuseSignalled` is that form, and the auditor still learns
everything, because a contract's signatories are informees of every exercise on
it, consuming or not.

Implementations MUST NOT present the signalling form as evidence. Canton's
pruning reference states that a pruned node "will not be able to serve events
that precede t", and that pruning "never removes active (i.e., non-archived)
Daml contracts". A refusal that exists only as an exercise event therefore
lives in the update streams of the participants that witnessed it, one of which
is operated by the party the record concerns. Once that participant prunes, the
position in the counter remains with nothing behind it, which is
indistinguishable from a reason deliberately withheld.
`testASignalledRefusalLooksWithheldOnceEventsAreGone` shows the two cases
leaving an identical active contract set.

So: signal when somebody is watching now, record when somebody will ask later.
A monitor wants the first. An examiner arriving in eighteen months wants the
second and cannot get it from a stream that has been pruned.

### Privacy

The asymmetry is deliberate and is the point. An allowed attempt increments
the counter and writes nothing about what it was. The auditor learns the
denominator and nothing about the numerator.

This composes with payload hashing. An adapter that hashes contract payloads
still carries a refusal record's `template_id` and witness parties, so the
count survives while the reason does not leave the participant. An auditor
obtains a verifiable denominator without the monitor learning what was
refused.

## Rationale

**With thanks to the people who shaped this.** This specification exists
because two people answered a question in public and gave their work away.

Federico Rodriguez (Community Tech Partner, @Federico_Rodriguez) replied on
11 September 2026 and set the direction. He pointed out that an application's
own receipts cannot prove an omission, however well they are chained, and
proposed modelling a refusal as a committed Canton transaction instead. The
central idea of this CIP is his.

PREDGE (@PREDGE) replied on 21 October 2026 and made it enforceable, by moving
the auditor from the observer line to the signatory line. That change is the
difference between a control that notices and a control that holds.

Both replies are in the open, at
https://forum.canton.network/t/how-do-you-prove-your-app-didnt-do-something/9114

Simon Meier (@meiersi-da) replied on cip-discuss on 30 October 2026 and
supplied the mechanism this specification was missing. He pointed out that
creating a contract to carry a notification clutters the active contract set
and that a non-consuming choice is the better way to signal an event, which is
the mechanism he and Bernhard Elsner specified as `EventLog` in CIP-0112. He is
right, Daml's own performance guidance agrees, and an earlier draft of this
specification offered only the expensive form. `RefuseSignalled` and the two
tests that measure what it buys and what it costs exist because of that reply.

Georgi Radev (Community Tech Partner, @radevG) replied on 27 October 2026 and
found what was missing. In his words: "A guard signatory alone does not gate
owner-controlled choices", and "audit every choice on the asset and its
interfaces". An earlier draft of this specification required only that the
guardian be a signatory, which is necessary and is not sufficient. The second
requirement in the Specification above is his, and the test that proves it was
written after reading his reply.

Leonid (@leonidr) replied on 30 October 2026 and corrected the scope of the
claim. An earlier draft said a refusal reaches no monitor at all. That is true
of a refusal decided in the submitter's own interpretation and untrue of one
that reaches the mediator, and he set out the difference: the confirmation step,
the two kinds of reject code, the stored verdicts and `/v0/events`. The fourth
point in the Motivation above exists because of that reply, and the claim is
narrower and checkable where it used to be broad.

**What Canton already does with a count and no reason.** Scan's `/v0/events`
carries `verdict_result`, the submitting parties and participant, and the
confirming quorums per view. It carries no reject reason: there is no such field
in the schema. So at the confirmation layer Canton already publishes that a
rejection happened, to whoever reads Scan, without publishing what was refused.
That is the same asymmetry this specification builds for the interpretation
layer, arrived at independently and first. It is also why the asymmetry should
not be argued for here at length: the protocol settled the question.

The difference is durability. The Scan Bulk Data reference states that verdict
data "is ephemeral and routinely pruned within the mediator", and that Scan
cannot recreate pruned data. A refusal record is an ordinary contract and lasts
as long as the ledger does.

**Why this needs a CIP rather than per-application design.** Simon Meier put
the objection plainly on 30 October 2026: "this is an application design
pattern that every app provider can decide on independently. So it doesn't
require a CIP, as no ecosystem level coordination is needed."

The first answer is not an argument, it is another applicant. On 18 October
2026 Arpit Karnatak of Vacuumlabs, whose Delegated Automation Capability is Dev
Fund proposal #627, wrote on the forum: "We plan to store the logs for all runs
offchain since the aborted/failed actions aren't natively stored on-chain, and
since there's no standard pattern out there to commit them on-chain, it didn't
make sense to implement it within this proposal." A team building bounded
delegated authority on Canton put its refusal logs off-ledger, in the custody of
the party those logs are about, because no standard existed. The absence of
coordination changed a design decision. That is what a CIP is for.
https://forum.canton.network/t/were-building-delegated-automation-on-canton-seeking-feedback-champion/9084

The second answer is the precedent of CIP-0112. A change in a token's holdings
is also application-level, and nothing stops each issuer signalling it their own
way. It was standardised so that one client can read any issuer's events without
bespoke integration per issuer. An auditor reading refusal evidence across many
applications has that problem exactly. If per-application design were sufficient
for events of ecosystem interest, `EventLog` would not need to exist.

What is genuinely per-application is the policy: which actions are guarded, what
the rules are, and what a refusal means. This specification fixes none of that.
It fixes the shape of the record, so that the auditor reading it does not need to
learn each application's vocabulary first.

**Why a contract rather than a new Ledger API service.** A contract is already
carried by every adapter, respects Canton's sub-transaction privacy, and
inherits the existing authorization model. A new service would require
participant changes and would still have the completion-stream visibility
problem.

**Why the guardian is a second signatory.** It was the only mechanism found
that makes journalling non-optional. Earlier drafts relied on the application
choosing to call the journal, which is a convention and not a control.

**Why the auditor is a signatory and not an observer.** In PREDGE's words, on
21 October 2026: "if the auditor is a signatory on the journal, not only an
observer ... nobody can create another one without the auditor's authority,
since a create needs every signatory." Under the observer design a second
journal could only be detected after the fact. With the auditor as a signatory
it cannot be created at all.

**Why the claim is narrow.** This is a complete record of refusals that were
decided. It is not a complete log of everything attempted. If a check passes
and the transaction later reverts, the attempt leaves nothing, because the
work and the count are in one transaction and die together. Off-ledger logging
remains the right tool for crashes. The difference is incentive: nobody gains
by hiding a crash, and somebody can gain by losing a refusal.

**The limit that must be stated.** Daml grants a submitter the authority of
every party it submits as. An operator who can submit as the guardian reaches
the asset directly and no record is written. This is therefore a control when
the guardian is operated by someone who is not the actor, and a convention
when one person submits as both. Segregation of duties does the work; this
specification only makes it enforceable. A test in the reference
implementation performs that bypass and shows the counter never moves.

## Backwards compatibility

None. This introduces a new application-level package. It changes no protocol
behaviour, no existing template and no Ledger API semantics. Applications that
do not implement `Journalled` are unaffected.

Interfaces and implementations are kept in separate packages, per Daml's own
guidance, so an application may depend on the interface without depending on
any template.

## Reference implementation

Published, reproducible, and verifiable by a stranger today.

```
ghcr.io/dominicrume/canton-journal-interface:1.0.0
  255139 bytes
  sha256 97ce4baaf2505493903974a7d591cce380180e97ad402cd43bd6b4066fb83a4d

ghcr.io/dominicrume/canton-refusal-record:1.0.0
  396449 bytes
  sha256 a72a61918f6c75d7f839439d6338ee8ce8a738864a702cab40d81882b3a69df8
```

Both pull anonymously, and both rebuild byte for byte from committed source.
Also available from
https://github.com/dominicrume/cantor8_kya_rails/releases/tag/daml-v1.0.0

Daml SDK 3.4.11, target Daml-LF 2.1, MIT, no dependency beyond `daml-prim` and
`daml-stdlib`. 169 Daml test scripts across the two packages, including
`testASecondJournalIsPrevented`, its stated boundary
`testWithNoAuditorASecondJournalIsStillPossible`, and
`testAnOwnerControlledChoiceStillBypassesTheJournal`, which demonstrates the
second conformance requirement above by violating it, and
`testSignallingCostsNoContract` with
`testASignalledRefusalLooksWithheldOnceEventsAreGone`, which measure the two
mechanisms against each other.

A consumer-side counter for adapter output is at
`tools/refusal_detector.py` in the same repository: Python standard library
only, and it reads no payload.

**What has not been done.** None of this has run on DevNet or MainNet. The
author has never held a DevNet credential. Everything above is local Daml
script execution and should be weighed as a specification with a working
reference implementation rather than as deployed software. That is stated here
rather than discovered later.

## Post-History

* 2026-10-30: corrected after review on the forum. Georgi Radev found that a
  guardian signatory does not gate an owner-controlled choice, which added the
  second conformance requirement and a test. Leonid set out the confirmation
  stage, the stored mediator verdicts and Scan's `/v0/events`, which narrowed
  an over-broad claim in the Motivation.
  https://forum.canton.network/t/an-audit-control-that-the-audited-party-can-switch-off-is-not-a-control/9323
* 2026-10-29: introduced to cip-discuss as message #909.
  https://lists.sync.global/g/cip-discuss/topic/cip_tbd_a_ledger_record_for/122004432
