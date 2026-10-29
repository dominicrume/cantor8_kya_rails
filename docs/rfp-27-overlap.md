# RFP 27: what overlaps, what does not, and what no CIP covers

**Declared interest, first, because it changes how you should read this.** I am
the author of #860, one of the three proposals assessed below. I have tried to
describe the other two as their authors would recognise them, and where I
could not be neutral I have said so. Check the numbers rather than trusting
me: every one of them is a command at the bottom.

*O'Rume Dominic Uririe, 29 October 2026.*

## Why this exists

On 21 October, on #866, Amanda Martin wrote:

> "Before proceeding to a vote, we should assess how this proposal overlaps
> with existing CIPs and other ongoing initiatives to ensure alignment and
> avoid duplicating efforts."

That assessment had not been written. This is it, covering all three open
proposals under RFP 27.

## The three proposals do not overlap. They are three layers of one pipeline

| | **#788 LedgerShield** | **#860 Refused actions** | **#866 OS Ledger** |
|---|---|---|---|
| Author | Vinh, Upflam | O'Rume Dominic Uririe | Long Do, Outer Sunset |
| Where it sits | in front of the Ledger API | inside Daml | after the ledger |
| What it refuses | an API request, by OPA policy | an action, by a Daml check | nothing; it reports |
| Where the record goes | DuckDB, in the proxy | a contract, on the ledger | journal entries, plus an on-ledger attestation |
| Primary RFP | 25, with 27 secondary | 27 | 27, with 20 secondary |
| Ask | 1,650,000 CC | see #860 | 10,300,000 CC |

A request that LedgerShield rejects never reaches Daml. An action that Daml
refuses never reaches the books. A period that OS Ledger closes contains
neither. The three can be deployed together without either of the other two,
and nothing one does is done twice by another.

**Where I cannot be neutral:** I think the three compose. An author who
believes his own proposal is complementary to its competitors has an obvious
motive for saying so, and you should weigh that.

## What the CIPs already cover, and I was wrong about this

I previously said no CIP touches audit or compliance. That was a search of
CIP **titles**. Searching the **bodies** says otherwise.

Over the 83 CIPs whose prose is in the repository:

| word | files |
|---|---:|
| regulat | 26 |
| compliance | 18 |
| audit | 13 |
| evidence | 10 |
| attestation | 8 |
| monitoring | 6 |
| **refus** | **0** |

So the category is discussed often. But of the 13 CIPs that mention audit, 10
are Super Validator admissions, where the word appears because the firm being
admitted does auditing: Quantstamp, Bitwave, Blockdaemon, Hypernative, Talos,
Zodia, Figment, Layer Zero, Wormhole, Chainlink. The other three are
CIP-0049 on cold backups, CIP-0082 on the Development Fund, and CIP-0100 on
its governance.

**No CIP specifies auditability as a mechanism.** The ecosystem has admitted
many auditors and standardised nothing for them to read.

And the word "refus" does not appear in any of the 83. Not once. That is the
only gap I can demonstrate rather than assert.

## Two things worth telling the other two authors

**For #866.** Its RFP 27 answer says on-ledger attestations have "the operator
as signatory and an optional auditor co-signatory, so an auditor can verify a
close without the data becoming public." That is the same mechanism #860
arrived at independently, after PREDGE suggested it on 21 October in
forum.canton.network/t/9114. Two proposals converging on auditor-as-signatory
without talking to each other is evidence the mechanism is right, and it is
the strongest argument either of us has.

Its ingestion reads Ledger API v2 UpdateService and StateService. Those
services carry committed activity. An action a control refused aborts its
transaction, so it produces no update and cannot appear in a close built from
those streams. This is not a defect in OS Ledger. It is a property of the
data: a finance close can state what happened and cannot state what was
stopped. If a future audit package is expected to answer "what did your
controls block", that number has to come from somewhere else.

**For #788.** LedgerShield does record refusals, which no other proposal here
does at its layer, and that deserves more prominence than it currently gets.
The records live in DuckDB inside the proxy. That is the right engineering
choice for quota and latency, and it means the refusal record is held by the
operator whose conduct it describes. For an internal control that is fine. For
evidence an external examiner relies on, the holder matters as much as the
content.

## Check every number yourself

```sh
# the three proposals
gh pr view 788 --repo canton-foundation/canton-dev-fund
gh pr view 860 --repo canton-foundation/canton-dev-fund
gh pr view 866 --repo canton-foundation/canton-dev-fund

# the CIP corpus, then the counts above
git clone --filter=blob:none https://github.com/canton-foundation/cips
cd cips
grep -ril refus      cip-0*/cip-0*.md | wc -l   # 0
grep -ril audit      cip-0*/cip-0*.md | wc -l
grep -ril compliance cip-0*/cip-0*.md | wc -l
```

These commands read every CIP file in the repository. My counts are over the
83 the README links and that carry prose, so the denominators will not match
exactly and the audit and compliance figures may come out a little higher.
The figure that matters is unaffected: `refus` returns zero either way, and a
single hit would disprove the only claim in this document that rests on
absence.

**Coverage, stated so you can discount it.** The README table has 118 rows. 91
have a well-formed link to a markdown file. 8 of those are stubs pointing at
PDFs, whose text I did not read. So the counts above are over 83 CIPs, not
118. A claim about the other 35 is not in this document because I have not
read them.

One of the 27 missing links is CIP-0129, whose README row points at
`/cip-0126/`. [PR #286](https://github.com/canton-foundation/cips/pull/286)
fixes it.
