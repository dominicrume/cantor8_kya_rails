# Reply to Archana Nigam, forum 9314

**Thread:** https://forum.canton.network/t/implementing-scheduled-and-recurring-actions-in-daml-3-5
**Posted:** 17 October 2026, 09:41, by `nigam_archana`. App Development. **Zero replies.**

Her use cases are EOD trade close, monthly interest payments, and maturity
settlement. All three are regulated, repeating financial processes.

## What the first draft got wrong

She wrote "Any guidance or **sample implementations** would be appreciated"
and the first draft sent her four paragraphs of documentation quotes with no
code in them. She asked for code.

So `Scheduled.daml` was built, tested and mutation-tested before this reply
was rewritten. Nine scripts: early, late, double-fire, the count running out,
and the authority split. Deleting either time check turns a named test red.

## Why answer this one

She asked four direct technical questions and nobody has answered any of them
in two days. Two of them land on exactly what this repository is about, and the
other two have first-party documented answers that most people get wrong.

Every claim below is a quote from a current primary source or a stated
observation. Nothing is from memory.

## The two claims to hedge, and why

- **No release note announces the removal of Daml Triggers.** The deprecation
  notice is in the 2.10 docs, and the absence from 3.x is established by the
  source tree and the docs sitemap, not by a Digital Asset statement. So the
  post says what was observed rather than claiming a documented removal.
- **Vacuumlabs' delegated automation is an unfunded Dev Fund proposal seeking
  a champion, not shipped code.** Calling it a product would be false and would
  also embarrass them.

---

## THE POST

Archana, short answers then working code.

**1. No built-in scheduler.** Nothing on the ledger initiates anything:
"Daml code has no independent thread of execution... Any action on the ledger
must be initiated by external components."
https://docs.canton.network/appdev/deep-dives/app-architecture-design

Canton's admin API does have a cron scheduler. It drives pruning, not command
submission.

**2. Triggers are deprecated and not in 3.x.** `sdk/triggers` is present at
tag `v2.10.6` and absent at `v3.4.11`, at the 3.5 snapshots and on `main`.
They were event-reactive anyway, never time-based, so they would not have
solved this.

**3 and 4. External scheduler, and the choice barely matters.** Put liveness
off-ledger and correctness on-ledger: your cron pokes the contract, the
contract refuses to run outside its window. Then a scheduler that fires early,
twice, or a week late costs you a rejected transaction rather than an early
payment.

Here is the pattern, built and tested rather than sketched.

Maturity and end-of-day:

    template DueOnce
      with
        owner : Party
        runner : Party
        what : Text
        dueAt : Time
        expiresAt : Optional Time
      where
        signatory owner, runner

        choice Run : ()
          controller runner
          do
            assertDeadlineExceeded ("not due yet: " <> what) dueAt
            case expiresAt of
              Some limit -> assertWithinDeadline ("window closed: " <> what) limit
              None -> pure ()
            -- your work here

Monthly interest, rescheduling itself:

    template DueEvery
      with
        owner : Party
        runner : Party
        what : Text
        nextAt : Time
        period : RelTime
        runsLeft : Int
      where
        signatory owner, runner

        choice RunNext : Optional (ContractId DueEvery)
          controller runner
          do
            assertMsg "schedule finished" (runsLeft > 0)
            assertDeadlineExceeded ("not due yet: " <> what) nextAt
            -- your work here
            if runsLeft <= 1
              then pure None
              else do
                next <- create this with
                  nextAt = addRelTime nextAt period
                  runsLeft = runsLeft - 1
                pure (Some next)

Three things that buys you. `Run` consumes the contract, so a double-firing
scheduler gets one payment. The schedule lives on the ledger rather than in a
cron file somebody can edit without review. And `runsLeft` bounds it, because
an unbounded recurring payment nobody remembers is how a treasury drains
quietly.

**The gotcha that will cost you if you miss it.** Do not gate on `getTime`.
In 3.x it pins the transaction's ledger time, which constrains preparation
AND submission to within `ledgerTimeRecordTimeTolerance`, one minute by
default. Prepare offline, sign, submit two minutes later, and it is rejected
for a reason that has nothing to do with your schedule. The `DA.Assert`
deadline helpers do the same comparison without pinning, and the docs say so:
"they do not constrain the time bound between transaction preparation and
submission."
https://docs.canton.network/appdev/modules/m3-working-with-time

Full module and nine tests, MIT, no dependencies past the standard library:
https://github.com/dominicrume/cantor8_kya_rails/tree/main/step-0-refusal

One last thing for your cases specifically. When the scheduler fires outside
the window the transaction aborts, so the ledger holds no record it was
attempted. Next month, when somebody asks whether the interest run happened on
the 1st, the answer is a line in a Kubernetes log. The same package records
refused runs as contracts for exactly that reason.
