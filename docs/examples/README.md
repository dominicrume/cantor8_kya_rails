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
