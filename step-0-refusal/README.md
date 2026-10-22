# canton-refusal-record

**A refusal that survives, for any Canton application.**

One Daml module. No dependencies but `daml-prim` and `daml-stdlib`. MIT.

## The problem

In Daml a failed `assertMsg` aborts the whole transaction. Nothing is written.
After a refused action the ledger looks exactly as it would if the application
had never tried.

So what succeeded is corroborated by the ledger, and what was stopped is the
operator's word. That is the wrong way round, because the half a regulator asks
about is the second one.

This is specific to ledgers that do not commit failed transactions. On Ethereum
a reverted transaction is still included in a block and still costs gas, so the
attempt is visible. In Daml the transaction never commits at all.

## The pattern

Stop aborting. Evaluate the rule and commit either way.

```daml
now <- getTime
case refusalReason this amount payee of
  Some rule -> do
    _ <- create RefusalRecord with
      owner; actor; action = "withdraw"; detail = show amount
      rule; refusedAt = now; auditor
    pure ()
  None ->
    -- the real work, only on this branch
```

The contract id and the ledger time now come from the ledger rather than from
the operator, and cannot be invented, backdated or reordered.

## Why it says nothing about money

`action` and `detail` are your words for what was tried. A payment app, a
lending protocol and a collateral engine all fit, and none of them carries a
field that means nothing to it.

The lending and collateral rows below are taken from the test suite, verbatim.
The payments row is an illustration and is marked as one, because a table that
mixes tested values with invented ones invites a reader to check the first row
and trust the rest.

| application | `action` | `detail` | `rule` | |
|---|---|---|---|---|
| lending | `withdraw` | `pool=USDC-3M utilisation=0.94` | `utilisation above the withdrawal ceiling` | tested |
| collateral | `substitute collateral` | `out=GILT-2031 in=CORP-BBB haircut=0.22` | `outside the eligibility schedule` | tested |
| payments | `settle` | `95000.00 USD to merchant-4471` | `would exceed the cap` | illustration |

The first version of this lived inside our own mandate template and had `payee`
and `amount` on it. Anyone could have copied the fifteen lines, and saying
otherwise would be overstating it. What they could not do was **depend** on it:
a data-dependency on that DAR hands you an entire spend-limited wallet, and the
two fields describe a payment rather than whatever they were refusing. This is
a separate package for that reason.

## The auditor

`auditor` is named once, in advance, by the owner. That party observes every
record and nobody else does.

This is the part a transparent chain cannot do: the refusal is **on a ledger**
and is **not public**, and the party entitled to read it was named before any
of the attempts happened. They never have to ask the operator for it, which is
the difference between evidence and a report.

`None` discloses to nobody beyond the two signatories, and that is the default.

`Acknowledge` is non-consuming and returns the rule, so the auditor can
demonstrate they could read it without destroying the thing being read.

## The journal: the auditor reads the denominator

`Journal.daml` answers the objection `Refusal.daml` cannot. A refusal record
proves a refusal happened. It says nothing about a refusal that was never
written, and a hash chain cannot reach that either, because the producer
chooses what to commit to.

So stop trying to prove a negative about records and publish a positive number.
`AttemptJournal` is one contract per owner and actor, consumed and recreated by
every attempt, holding `attempts` and the positions in `refusals`. The auditor
is an **observer of the journal**, so the auditor reads the count off the ledger
rather than off a disclosure the operator assembled.

```
attempts = 50, refusals = [3, 7, 19]
records handed over = 2
-> one refusal is missing, and its position is 3, 7 or 19.
```

The application exercises the journal inside the same transaction as its real
work. Daml commits a transaction whole or not at all, so the work and the
increment cannot come apart: skipping the increment means skipping the work.

What the auditor still cannot see is the 47 attempts that were allowed. Not
what they were, not to whom, not for how much. **The count is disclosed and the
content is not.** An auditor who has to take the operator's word for the
denominator cannot audit a sample; a transparent ledger that discloses the
numerator too is unusable by a regulated firm. This sits between those.

Two things about it that are limits and not features:

- **A second journal is prevented, not merely detected.** Daml-LF 2.1 removed
  contract keys, and this file previously concluded that uniqueness could
  therefore only be shown to the auditor after the fact.

  **That was wrong, and PREDGE corrected it on
  [forum 9114](https://forum.canton.network/t/9114) on 21 October 2026.** A
  create needs the authority of every signatory, so the auditor goes on the
  signatory line rather than the observer line and a second journal cannot be
  opened without them. No keys required.

  It costs nothing at runtime: a choice that recreates the journal already
  carries its signatories' authority, so the auditor need not be online for an
  attempt. They are needed only to open a journal, which is the one moment you
  want them involved. `testASecondJournalIsPrevented`.

  The guarantee is exactly as strong as naming an auditor. With `None` there is
  no third signatory and a second journal can be opened freely, which
  `testWithNoAuditorASecondJournalIsStillPossible` holds.
- **This module cannot force an application to route through it.** An
  application with a second, unjournalled path to the same asset has a hole,
  and no module it imports can see that. What changes is where the hole has to
  be: from "any attempt, invisibly" to "a code path a reviewer can look for".

- **A revert after the check passes loses the attempt.** Raised by Arpit
  Karnatak of Vacuumlabs on [forum 9084](https://forum.canton.network/t/9084)
  on 18 October 2026. If the check passes, the work runs, and something later
  in the same transaction reverts, Daml rolls back the count too. The
  trade-off has no free side: in the same transaction the record and the work
  are inseparable but both die on a revert; in its own transaction first the
  record survives but can describe work that never happened.

  The refuse branch does not have this problem, and that asymmetry is the
  whole answer. When the check says no, the record is the only thing in the
  transaction and nothing later can revert it.

- **The commitment binds but did not hide, until 19 October.** The first
  version hashed the action and detail with no salt. `sha256` over "withdraw"
  and a round amount is brute-forced in seconds by anyone who guesses the
  format, and payments are exactly that low-entropy case. The claim that an
  open attempt revealed nothing was **false**. It now takes a random salt,
  held off the ledger and revealed at resolution.
  `testTheCommitmentHidesAndNotJustBinds` holds it.

- **Signatories can archive an open attempt.** Daml's implicit `Archive` is
  controlled by the signatories, and in the ordinary case one firm controls
  both parties. So the subject of the evidence can delete it. That cannot be
  prevented, so it is made **detectable**: every legitimate ending mints a
  `Resolution` marker carrying only the position and the outcome kind. An
  attempt archived with no resolution leaves a numbered hole in the auditor's
  arithmetic. `testArchivingAnAttemptLeavesANumberedHole` performs the
  deletion and then finds it.

`testAnUnjournalledAttemptIsStillInvisible`,
`testAnAllowedAttemptThatRevertsIsLost` and
`testARefusalHasNothingLaterThatCanRevertIt` assert those limits, so the claim
cannot grow past the code without a test going red.

**Why offchain logging is still right for reverts.** The difference is
incentive, not mechanism. Nobody gains by hiding a crash. Somebody can gain by
losing a refusal. Only the second needs to sit where it cannot be dropped.

## Making the journal non-optional

Every guarantee above used to end with the same admission: nothing forced an
application to route through the journal. An auditor asking "can I trust this
record" was being answered with "if the application chose to write one".

That is now closed by Daml's authorization model rather than by convention.

Put a **guardian** party on the asset as a signatory. The guardian is also a
signatory of the journal and of every attempt it opens, so its authority
reaches the second transaction, where the work happens. An application that
tries to move the asset any other way does not hold that authority and the
ledger refuses it.

```daml
template Wallet
  with holder : Party; guard : Party; balance : Decimal
  where
    signatory holder, guard          -- the whole fix is this line

    interface instance Journalled for Wallet where
      view = JournalledView with owner = holder; guardian = guard
      perform = do ...               -- your own work, unchanged
```

`testTheAssetCannotMoveOutsideTheJournal` proves the bypass fails.

The interface lives in its own package, `canton-journal-interface`, on Daml's
own advice that mixing interfaces and templates makes a package hard to
upgrade. An application depends on that one and never has to depend on ours.

**The limit, tested rather than asserted.** Daml gives a submitter the
authority of every party it submits as. So an operator who can submit as the
guardian reaches the asset directly, and you are back to a convention.
`testSubmittingAsTheGuardianDefeatsIt` performs exactly that and shows the
counter never moves.

**This is a control when the guardian is operated by someone who is not the
actor, and a convention otherwise.** Segregation of duties does the work; the
code only makes it enforceable. Say that to an auditor before they say it to
you.

One thing that came free: because the guardian is a signatory of every
`Attempt`, the operator can no longer archive an open attempt alone. What was
a detectable deletion is now a prevented one.

## Scheduled and recurring actions

Asked on [forum 9314](https://forum.canton.network/t/9314): end-of-day close,
monthly interest, maturity settlement. Nothing in Daml initiates anything, so
something off-ledger has to fire. The question is what stops it firing at the
wrong time.

**Liveness is off-ledger. Correctness is on-ledger.** Your cron, Temporal or
Airflow pokes the contract; the contract refuses to run outside its window. A
scheduler that fires early, twice, or a week late costs you a rejected
transaction instead of an early payment.

`DueOnce` for maturity and end-of-day, `DueEvery` for interest. A recurring
run mints the next occurrence, so **the schedule lives on the ledger** rather
than in a cron file somebody can edit without review, and `runsLeft` bounds it.

**Do not gate on `getTime`.** In Daml 3 it pins the transaction's ledger time,
which constrains preparation *and* submission to within
`ledgerTimeRecordTimeTolerance`, one minute by default. Prepare offline, sign,
submit two minutes later, and it is rejected for a reason that has nothing to
do with your schedule. `assertDeadlineExceeded` and `assertWithinDeadline` do
the same comparison without pinning.

## What it does not do

- **An attempt that never touches the journal leaves nothing behind.** The
  journal makes omission detectable on the path it covers. It does not make an
  attempt that bypassed it appear, and no ledger artefact can.
- **A refusal that happened** is impossible to invent, delete, backdate or
  reorder.
- **A record is archivable by its signatories.** The honest claim is that
  removing one is itself a ledger event, not that it cannot be removed.
- **It proves a rule fired, not that a rule is correct.**

## Use it

```
daml build
```

Then add the DAR as a `data-dependencies` entry in your own `daml.yaml`.

Fifty four scripts cover it: eight on the record, thirteen on the journal, seventeen on two-phase attempts, six on enforcement and nine on scheduling. The
ones that matter are a lending protocol and a collateral engine using it with
no concept of a payee, an auditor who sees every record while a stranger sees
none, `testAWithheldRefusalIsDetectable`, and `testTheAuditorCannotSeeWhatWasAllowed`. `python3 tests/daml_tests.py` from the
repository root runs them alongside everything else.

## Credit

The pattern was named `RejectedAttempt` by **Federico_Rodriguez**, a Canton
Community Tech Partner, on
[forum.canton.network/t/9114](https://forum.canton.network/t/9114) in September
2026. He read the design, found that application-written receipts cannot prove
completeness, specified the fix, and named the limit it does not close. All
three are in this module.
