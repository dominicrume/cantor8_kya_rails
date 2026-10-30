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

When a Daml check refuses an action, the transaction aborts. Nothing is
committed, so nothing appears on the Update service and nothing reaches any
monitor reading it. The rejection is delivered to the command completion
service, which only the submitting application can read, so the party whose
conduct is in question is also the only party holding the record of it.

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

1. **A refused action produces no update.** `assertMsg` and `ensure` abort the
   transaction. There is no event, so there is nothing for the Update service
   to deliver.
2. **The completion stream is not independent evidence.** A rejection appears
   on the command completion service, visible to the submitting application.
   The party being audited is the only party who can see it, which is the
   definition of a record an auditor cannot rely on.
3. **An application's own log is also the application's.** Any off-ledger log
   written by the application is written by the party the evidence concerns.
   A hash chain over that log makes editing it detectable and omission from it
   undetectable, because the producer chooses what to commit to.

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
`daml-stdlib`. 165 Daml test scripts across the two packages, including
`testASecondJournalIsPrevented` and its stated boundary
`testWithNoAuditorASecondJournalIsStillPossible`.

A consumer-side counter for adapter output is at
`tools/refusal_detector.py` in the same repository: Python standard library
only, and it reads no payload.

**What has not been done.** None of this has run on DevNet or MainNet. The
author has never held a DevNet credential. Everything above is local Daml
script execution and should be weighed as a specification with a working
reference implementation rather than as deployed software. That is stated here
rather than discovered later.

## Post-History

* 2026-10-29: introduced to cip-discuss as message #909.
  https://lists.sync.global/g/cip-discuss/topic/cip_tbd_a_ledger_record_for/122004432
