# An example disclosure

`settlement-refusals.json` is a real run of the real library, with invented
figures. No money moved, no ledger saw it, and none of these merchants exist.
It is here so you can check the format before you produce one of your own.

## What it is

A settlement agent ran seven steps under a 250,000.00 USD daily cap and an
allow-list of three payees. Four steps are shown in full. Three are payments,
and their detail is withheld.

## Try it

1. Open `../index.html` in a browser. Nothing to install, no network call.
2. Drop `settlement-refusals.json` on it.

It should say the disclosure holds, that four entries are shown and three
withheld, and then draw the refusals:

```
#4  REFUSED  would exceed the cap: 180000.00 + 95000.00 > 250000.00 USD
#5  REFUSED  payee is not on the allow-list: merchant-9902
#7  REFUSED  amount cannot be negative (-250.00)
```

Entries 2, 3 and 6 appear as gaps with their seals and nothing else.

## What checking it proves

Every entry keeps its position, its outcome, the seal before it and its own
seal. The seals chain, so nothing can be taken out: delete a refusal and the
links stop meeting. Correct the counts to cover for it and the numbering still
shows a gap. Edit a refusal you are showing and its body stops re-sealing to
the seal printed beside it. All of that is recomputed in the browser from the
file, without asking us anything.

The document also states the rule it disclosed under, in its own text: every
entry whose outcome is not ACCEPTED. That is what makes a withheld entry's
outcome checkable. A withheld body cannot be recomputed, so without a declared
rule, "these are all my refusals" would be unfalsifiable. With one, a withheld
entry labelled REFUSED contradicts the document, and the page names it.

## The refusal that is only our word, and what fixes it

This is the honest limit of the file above, and it is the one worth reading.

Entries 4, 5 and 7 say REFUSED. Nothing outside this file corroborates them.
Entries 2, 3 and 6 are accepted payments, and those are corroborated by the
money having moved: a ledger recorded it. The half you can check against the
world is the half nobody asks about, and the half anybody asks for is the
producer writing about themselves. That is backwards, and for a regulated
issuer it is the difference between evidence and a nicer log file.

The cause is not in this format. It is that the usual way to enforce a rule is
to abort, and an aborted transaction leaves nothing behind. In Daml a failed
`assertMsg` rolls the whole transaction back, so after a refused payment the
ledger looks exactly as it would if the agent had never been asked.

So the refusal is made into a transaction that succeeds:
[`KyaMandate.TryCharge`](../../step-1-mandate/daml/KyaMandate.daml) runs
the same rules, and when one says no it writes a `ChargeRefused` contract and
leaves the mandate untouched. No money moves. The contract id and the record
time come from the ledger rather than from us.

Four Daml tests hold it to that, and you can run them yourself:

```
python3 tests/daml_tests.py
```

| test | what it refuses to let us claim |
|---|---|
| `testRefusalIsOnLedgerAndNothingMoved` | the refusal is really on the ledger, and `spent` did not move |
| `testEveryFenceRecordsItsOwnRule` | each rule records its own reason, not a generic "refused" |
| `testTryChargeAcceptedBehavesLikeCharge` | this is not a softer `Charge` that lets payments through |
| `testTheOperatorCanArchiveARefusalButNotSilently` | we can archive one, so the claim is "removing it is a recorded event", not "it cannot be removed" |

A receipt for such a refusal carries `ledger_ref`, the contract id. The example
above does not have any, because no ledger has seen it. When a receipt does
carry one, the verifier page prints it and says, in those words, that it did
not check it: the page has no network, so that part is yours to do on a
participant node you trust.

## What it does not prove

Where the file came from. A seal says the contents have not changed since they
were sealed; it does not say who sealed them. The page reports the assurance
level it actually established, which for a file handed to it is
`self-attested`.

And one thing this example gives away on purpose. Entry 4 says
`180000.00 + 95000.00`, and 180,000.00 is entries 2 and 3 added up. A cap
refusal cannot explain itself without stating the spend to that point, so the
accepted total at that moment travels with it even though the payments do not.
The library says so before you send: `what_this_reveals()` names it. Nothing
here is hidden from the person producing the file.
