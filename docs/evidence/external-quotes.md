# Quotes from outside this repository, each verified at source

Every quote below was read from the live API on the date given, with the
command that produced it. This file exists so that a quote used anywhere in
this repository is checkable by a reader here, not only by whoever ran the
command.

`tools/before_posting.py` refuses a draft whose quote is in no source file.
It refused `docs/the-system-measured.md` twice on 13 November 2026 for exactly
that reason, which is the gate working: a quote I had verified in a terminal
was not verifiable by anyone else. This file is the fix.

## Simon Meier on what standardisation CIPs are for

Verified 2026-11-13. `meiersi-da`, 2026-08-27, on canton-foundation/cips
pull request 171.
<https://github.com/canton-foundation/cips/pull/171#discussion_r3870730811>

    gh api repos/canton-foundation/cips/pulls/171/comments --paginate \
      --jq '.[] | select(.body|test("coordination need";"i"))'

> Here I'm inclined to give an actual HTTP OpenAPI spec. Otherwise name providers and consumers cannot act independently and have to do more coordination. Removing this coordination need is the goal of these standardization CIPs.

Why it matters here: it is the purpose test for a standardisation CIP, stated
by the person who argued on cip-discuss that a refusal record needs no CIP
because an application can decide it independently. The test is not whether
one party could decide alone. It is whether leaving each party to decide alone
forces consumers into coordination they would otherwise not need.

## The only reason ever given in writing for closing a CIP

Verified 2026-11-13. `hythloda`, 2025-09-15, identical text on two pull
requests.
<https://github.com/canton-foundation/cips/pull/65#issuecomment-3293654456>
<https://github.com/canton-foundation/cips/pull/74#issuecomment-3293655380>

    gh api repos/canton-foundation/cips/issues/65/comments \
      --jq '.[] | select(.body|test("Sponsor/Endorser";"i"))'

> No SV Sponsor/Endorser to move forward. Please make any needed changes and resubmit. Best process is to send proposal to cip-discuss@lists.sync.global to see what is needed before the GitHub PR. The full process is listed in CIP0-0000

Why it matters here: the binding constraint on a CIP is two Super Validators,
a sponsor and an endorser. It is not document quality, and it is not review
attention.

## RFP 27, in full

Verified 2026-11-13 from `2026-2028-strategic-roadmap.md` in
canton-foundation/canton-dev-fund, lines 260 to 263.

> 27. Security Monitoring, Auditability and Evidence
>     1. RFP
>        1. Develop reusable tools and standards for security logging, monitoring, alerting, audit trails, compliance evidence, and security metrics while preserving Canton's privacy model. Proposals should identify the threats being monitored, whether the scope is at the entity or network level, required data sources and how privacy, access controls, and selective disclosure will be handled.
>        2. We anticipate approving multiple grants in this area as work progresses over the coming year.

Why it matters here: the second sentence is a four-part submission rubric, and
#860 does not answer it in the RFP's own words.

## CIP-0120 on rejected transactions

Verified 2026-11-13, canton-foundation/cips, cip-0120, line 54.

> rejected transactions do not qualify for any validator rewards. Only successful confirmation requests must generate validator activity records.

Why it matters here: this is the ecosystem stating our own asymmetry in its
own normative specification. It is better evidence than our count of zero
occurrences of "refusal" across the CIP corpus, because an absence can be
answered with "nobody needed it" and this sentence cannot.

## CIP-0100 on the champion requirement

Verified 2026-11-13, canton-foundation/cips, cip-0100.

> If no champion can be found, the Tech & Ops committee should communicate back to the proposer(s) that the proposal will not be taken forward.

Why it matters here: the champion is a written requirement for an external
proposal, not a convention. Measured effect: `champion-confirmed` proposals
are funded at 27.3 percent against 1.1 percent for `needs-champion`.

## The 80/20 budget rule

Verified 2026-11-13, `2026-2028-strategic-roadmap.md` in
canton-foundation/canton-dev-fund.

> The Foundation will target 80% of its Development Fund budget toward proposals that respond to Foundation RFPs, while reserving up to 20% for individual initiatives that fall outside the published roadmap.

Why it matters here: being RFP-aligned is where four fifths of the money goes.
A proposal filed as an individual initiative is competing for the other fifth.

## Georgi Radev on what a guard signatory does and does not gate

Verified 2026-11-13. `radevG`, 2026-10-27, post 2 of forum topic 9323.
<https://forum.canton.network/t/9323/2>

    curl -s https://forum.canton.network/t/9323.json   # post_number 2

> A guard signatory alone does not gate owner-controlled choices.

Why it matters here: he was right, the test suite had missed it because the
test wallet carried no owner-controlled choices, and it became
`testAnOwnerControlledChoiceStillBypassesTheJournal` plus a requirement on
implementers in the draft specification, credited to him.

## OpenZeppelin's own invitation to test their Canton packages

Verified 2026-11-13. `Pepe_Blasco`, 2026-08-12, post 1 of forum topic 9059.
<https://forum.canton.network/t/9059>

    curl -s https://forum.canton.network/t/9059.json   # post_number 1

> Clone the repos, read the design reports, and open an issue with how it works for what you’re building, or where it should change.

Why it matters here: the mutation findings against two of their Canton
packages answer this invitation, and they were reported as public issues on
each repository. The apostrophe in the quote is the curly one, as published.

## The four free-text questions on OpenZeppelin's application form

Read 2026-11-13 from the posting for Senior Blockchain Security Developer
(Canton), as pasted in full by the applicant, who had the live form open. The
posting page itself shows only an Apply link, and a fetch of it on the same day
did not render the form fields, so this is the applicant's copy of the form and
not a fetch. The apostrophe in the first question is the curly one, as
published.
<https://www.openzeppelin.com/careers/opening?gh_jid=7742510003>

> Our mission is to accelerate the world’s transition to an open financial system. How do you identify with that mission?

> What has been your experience working with Canton to this point?

> Describe an instance where you built tools that other people have leveraged for their benefit.

> How do you leverage AI in your daily workflow?

Why it matters here: an answer written to a paraphrase of a question is an
answer to a different question. These are the words the form actually asks.
