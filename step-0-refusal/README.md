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

## What it does not do

- **An attempt that was never submitted leaves nothing behind.** This makes a
  refusal that happened impossible to invent, delete, backdate or reorder. It
  does not make one that never reached the ledger appear, and no ledger
  artefact can.
- **A record is archivable by its signatories.** The honest claim is that
  removing one is itself a ledger event, not that it cannot be removed.
- **It proves a rule fired, not that a rule is correct.**

## Use it

```
daml build
```

Then add the DAR as a `data-dependencies` entry in your own `daml.yaml`.

Eight scripts cover it, including the two that matter: a lending protocol and a
collateral engine using it with no concept of a payee, and an auditor who sees
every record while a stranger sees none. `python3 tests/daml_tests.py` from the
repository root runs them alongside everything else.

## Credit

The pattern was named `RejectedAttempt` by **Federico_Rodriguez**, a Canton
Community Tech Partner, on
[forum.canton.network/t/9114](https://forum.canton.network/t/9114) in September
2026. He read the design, found that application-written receipts cannot prove
completeness, specified the fix, and named the limit it does not close. All
three are in this module.
