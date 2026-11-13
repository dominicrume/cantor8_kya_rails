# The Canton ecosystem, measured before we speak into it again

Eight parallel measurements, 13 November 2026. Everything here names the
command or URL behind it. Where something could not be read it says CANNOT
CHECK rather than guessing.

This document exists because the owner said on 13 November 2026, in
conversation and paraphrased here rather than transcribed, that we do not
understand this system, that it has been limiting us for a while, and that it
is why we do things out of turn. The data says he was right, and names which
turns.

## The one finding that explains 47 days of silence

**We arrived in the week the rules changed.**

| date | event |
|---|---|
| 21 August 2026 | `rfps/` directory tree merged into canton-dev-fund |
| 25 August 2026 | last public repository created in any Canton org |
| **29 August 2026** | **the Cantor8 hackathon, our entry point** |
| 22 September 2026 | Dev Fund 2.0 workflows merged |
| 16 October 2026 | voting rules changed: a vote now closes two days after reaching threshold |
| 12 November 2026 | five already-funded documents renamed to carry RFP numbers |

So we have been writing in the old idiom (here is a thing I built, please
fund it) into a machine that now asks which of our 28 questions this
answers.

The cleanest proof is one organisation doing both. Moonsong Labs:

- `jekennedy`, no RFP cited: opened 19 March, merged 19 August. **153 days.**
- `tomimor`, titled "QuickStart Uplift (RFP 15)": opened 22 October, merged
  10 November. **19 days.**

Eight times faster. The difference is a number in the title.

## What predicts funding, measured over 274 days and 636 pull requests

| segment | funded |
|---|---|
| label `champion-confirmed` | **27.3%** |
| label `needs-champion` | **1.1%** |
| author is Digital Asset | **65.0%** |
| everyone else | 9.1% |
| all core proposals | 11.2% |

A champion is a 25x multiplier and it is **not a convention**. CIP-0100,
approved 14 January 2026: an external proposal requires a Champion from the
Tech and Ops Committee, and, verbatim:

> If no champion can be found, the Tech & Ops committee should communicate back to the proposer(s) that the proposal will not be taken forward.

The ask amount predicts nothing, and the direction is the opposite of the
intuition: funded asks have a **higher** median (2,855,000 CC) than unfunded
ones. Four proposals above 20 million CC have passed. **Small asks fail in
bulk**, and ours at 300,000 CC is below the 25th percentile.

## How proposals actually die

294 closed unfunded. **292 of them were never voted on. 99.3 percent.**
On 22 October, 74 were closed in a single day in the Dev Fund 2.0 sweep.

178 of 295 authors opened exactly one document and never returned. Dozens of
February proposals are still open, untouched, 265 days later. Nobody closed
them; they were not answered.

The fund does not reject. It lets things lapse and then sweeps.

**Where #860 sits:** 47 days, against a median open age of 76.5 days and a
median *merge* age of 8 days. Not yet an anomaly, and well past the point at
which merges happen.

## The opening, and it is real

`rfps/security-assurance-incident-readiness/` contains **one funded document
and a `.gitkeep`**. Eight RFPs in that category, one grant. That is the
largest gap between stated demand and delivered work of the five categories.

RFP 27 verbatim, from `2026-2028-strategic-roadmap.md`:

> Develop reusable tools and standards for security logging, monitoring,
> alerting, audit trails, compliance evidence, and security metrics while
> preserving Canton's privacy model. Proposals should identify the threats
> being monitored, whether the scope is at the entity or network level,
> required data sources and how privacy, access controls, and selective
> disclosure will be handled.
>
> We anticipate approving multiple grants in this area as work progresses
> over the coming year.

That second sentence is a four-part submission rubric. Our proposal does not
answer it in its own words.

**And the budget rule, verbatim:**

> The Foundation will target 80% of its Development Fund budget toward proposals that respond to Foundation RFPs, while reserving up to 20% for individual initiatives that fall outside the published roadmap.

## Four claims of ours that the measurement killed

**1. Our claim that nobody records refusals on a Canton ledger.** False, and verified by
reading the source. `khalydmaina/sentry` has `template RejectedTransfer`
with `signatory owner, observer agent`. `knowAshish/MandateGuard` has
`template AuthorizationDecision` with `signatory operator, institution`,
carrying `outcome`, `limitChecks` and `reasonCodes`.

The claim that survives is narrower and better, because it concedes the prior
art: **two Canton projects record refusals, and in both the audited party
controls the record.** Ours puts an auditor on the signatory line.

Better evidence than our zero-count, from the ecosystem's own normative spec,
CIP-0120 line 54: *"rejected transactions do not qualify for any validator
rewards. Only successful confirmation requests must generate validator
activity records."* An absence can be answered with "nobody needed it". That
sentence cannot.

**2. Our claim that Jatin is a binding voter.** False. `git-vote`'s own tables place him in
`tech-ops-alternates`. Across all 164 vote-close comments he appears 48 times,
every one non-binding, every one "In favor". The five who bind are
EduardoFromTheFuture, ali-abrar, heslin-zenith, jonathan-ieu and shaul-da.

What he is instead: Developer Relations Manager at the Canton Foundation, the
delivery assessor the primaries vote on top of, and the maintainer who
**approved and merged three of our pull requests** into the Canton Developer
Hub on 8 and 21 September 2026.

**3. Our assumption that review attention means progress.** False. Merged CIPs have a median of
**zero comments and one day**. The most-reviewed pull requests in that
repository are all still open, one for 252 days with 135 comments. The
decision happens on cip-discuss and in a vote; the pull request is merged
afterwards as the record.

**4. Our claim that a missing credential blocked the real-ledger proof.** False for 74
days. `daml sandbox` ships with the SDK already installed here. Closed on
13 November: `python3 tools/prove_refusal_on_sandbox.py`, exit 0 from a cold
start, with a negative control that must fail first.

## The CIP argument, and it is stronger than it looked

Simon Meier told us a non-consuming choice is an application design pattern
every provider can decide independently, so it needs no CIP.

A grep over all 121 CIPs hits `EventLog` in **exactly one file: CIP-0112**.
His own, Approved, the largest document in the corpus. Section 4.3.5
specifies an interface `EventLog` with a single nonconsuming choice
`EventLog_HoldingsChange`, standardising the interface, the package name, the
choice name and the field set.

And the test his objection has to pass, in his own words on another pull
request, verified at source 13 November 2026 at
<https://github.com/canton-foundation/cips/pull/171#discussion_r3870730811>
(`meiersi-da`, 27 August 2026):

> Removing this coordination need is the goal of these standardization CIPs.

The full comment and the command that produced it are in
`docs/evidence/external-quotes.md`.

So the question is not whether one app could decide alone. It is whether
leaving each one to decide alone forces every reader into coordination they
would not otherwise need. A refusal record an auditor must read is exactly a
consumer-side parsing problem.

What EventLog is **not**: it reports what did happen to holdings and has no
concept of an action that was stopped. The mechanism overlaps. The subject
does not.

**Duplication check across all 121 CIPs:** refus / refuse / refused / refusal,
denied, declined, "audit evidence", non-repudiation all return **zero**.

**A clock nobody noticed:** CIP-0000 gives Standards Track three months from
introduction on cip-discuss to going to a vote, or it is Withdrawn or
Deferred. Message #909 went out 29 October 2026. That is roughly
**29 January 2027**.

**The gate:** a CIP reaches Proposed only with two Super Validators, a sponsor
and an endorser. The only reason ever given in writing for closing a CIP,
twice with identical wording by `hythloda` on 15 September 2025, verified at
source 13 November 2026 at
<https://github.com/canton-foundation/cips/pull/65#issuecomment-3293654456>
and
<https://github.com/canton-foundation/cips/pull/74#issuecomment-3293655380>:

> No SV Sponsor/Endorser to move forward.

The full text and the command that produced it are in
`docs/evidence/external-quotes.md`.

## The forum, where we are not invisible

Over the last twelve months we are the **7th most prolific poster on the
entire forum** and the 2nd most prolific unaffiliated one. We hold **2 of the
22 accepted answers** the whole forum produced this year, which is 9 percent
of the year's supply. Topic 9114 is the **5th most-replied topic** of the
eleven-month window.

And no Digital Asset or Canton Foundation employee has ever replied in 9114 or
9323. Jatin's reply on 9475 is the only Foundation engagement in the dataset.

**Where to post, and where never to:**

| category | outsider topics answered |
|---|---|
| developer-support | **89%** |
| ecosystem | 28% |
| SIGs | **7%** |

67 of 97 dead topics were in ecosystem, 14 in the SIGs. Thirteen of the twenty
SIG subcategories hold zero topics. A code block in the first post is a 2.6x
marker for getting replies.

**The answer rate is collapsing.** Outsider topics answered: about 80 percent
through August, 40 percent in September, 49 percent in October, 36 percent in
November. Staff replies fell from 55-85 percent to 12-18 percent.

**Trust level 2 is forty minutes of reading.** Blocked on exactly two
counters: enter 20 topics (we have 10), read 100 posts (we have 54).
Everything else is met. No posting required.

## The honest weaknesses, stated by us before anyone else states them

1. **The demand side is unevidenced.** We asked twice, in 9114 and 9059,
   whether anyone had ever been asked to prove their app did not do something.
   In fourteen months nobody on that forum has said yes.
2. **Leonid's "big if" is unrebutted.** Proof on the ledger costs a create per
   refusal.
3. **The pruning question is open and may be fatal to the cheap path.** The
   party who can prune is the party being audited.
4. **Independence is not provable on-ledger.** The ledger names parties, not
   their operators (radevG, 27 October).
5. **No token standard anywhere in our Daml.** Zero occurrences of `Holding`,
   `TransferInstruction`, `Amulet`, `Splice` or CIP-0056 in either package.
6. **Our own two packages are not connected.** `grep -rn 'Journalled'
   step-1-mandate/` returns nothing.

## What to do, in order of leverage per unit of effort

1. **Answer Jatin on forum 9475.** The only Foundation person who has ever
   spoken to us, and the maintainer of the catalogue our tool sits in.
2. **Answer Michael (9312) and tonozzibeverley953 (9114).** Both on live
   technical holes, both unanswered since 11 November.
3. **Reposition #860 against RFP 27's four-part rubric in its own words**, and
   price it in the real band rather than below the floor.
4. **Open a second proposal under RFP 22**, built only on `tools/daml_mutate.py`
   and the OpenZeppelin findings: 49 of 62 uncovered authorization fences in
   two of their Canton packages at pinned commits. Different RFP, no
   competition with #860, and it is our best-evidenced asset.
5. **Forty minutes of reading** for trust level 2.
6. **Integrate our own two packages**, and put a Holding behind the mandate.
   Both are about a week and both are inside our control, unlike a vote.

## The sentence to keep

A record the actor writes about itself is not evidence, including ours. 267
commits in a repository nobody else has pushed to is that record. The visa
criterion is literally "recognised by others". The job market wants shipped
delivery in a team. The Dev Fund gate is an operator's keystroke. All three
are gated by other people's records of us.
