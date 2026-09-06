# SIG approach — how these proposals reach a Champion

The Development Fund's own process says what to do before submitting, in order:

> 3. Discuss the need with the relevant SIG, maintainers, developers, or affected
>    ecosystem participants.
> 4. Gather evidence that the problem is real and sufficiently important to solve.
> 5. Identify a Development Fund Champion.
> 6. Submit your proposal using the current proposal template.

Steps 3 to 5 are the ones most proposals skip. Of 300 Dev Fund pull requests,
**new proposals are 8 merged against 91 closed**. Amendments to already-championed
work run at 100%. The difference between those two numbers is a Champion and a
prior conversation.

The second number to plan around is how long it takes. Measured from filing to
merge, the eight that succeeded took 15, 37, 85, 103 and 113 days for the
substantial ones — a median near three months, and the most recent merge was
26 August 2026. A proposal filed today is decided around December. That makes the
SIG conversation more urgent rather than less: it is the part that can start this
week, and it is the part that shortens everything after it.

A Champion is not a favour. The review process describes their job as ensuring
"the milestones, scope, and acceptance criteria are well defined" — they are
staking their own standing on the proposal being worth the committee's time.
Nobody does that for a document they first saw the day it was filed.

---

## The map

Verified from `sig-directory.md` on 2026-09-06. SIGs operate ad hoc and each has a
dedicated Slack channel.

**Security SIG — 3 members. The correct SIG for RFP 27.**

| Name | Organization | GitHub |
|---|---|---|
| Edward Newman | Digital Asset | nycnewman |
| Richard Domikis | MPCH | — |
| Stanislav German-Evtushenko | SBI Security Solutions | stas-sbi |

Three people against eight security RFPs, every one of which says the Foundation
"anticipates approving multiple grants in this area." That is the thinnest SIG on
the list carrying the largest stated appetite. It is the best-matched and least
crowded room in the ecosystem, and it is where RFP 27 lives.

**Identity & Metadata SIG — 5 members. Named explicitly by RFP 12.1.**

| Name | Organization | GitHub |
|---|---|---|
| Leonid Rozenberg | C7 | leonidr-c7 |
| Simon Meier | Digital Asset | meiersi-da |
| Zhi Zhang | Edge & Node | zhihezhang2 |
| Paolo Domenighetti | Freename AG | pdomenighetti |
| Gherardo Varani | Freename AG | 0xvarano |

RFP 12.1 instructs proposals to "account for relevant work already underway
through the Identity and Metadata SIG." C7 is in it — the same C7 whose public
position is that "a Party ID identifies a node, not the institution behind it."
That is the adjacent problem, one layer up from a mandate.

**Cantor8 — six people across SIGs, and the warmest route available.**

| Name | SIG | GitHub |
|---|---|---|
| Paruyr Babayan | dApp Integration | yogurt1 |
| Niko Cherkezishvilli | Token Standards, Daml Tooling, DAR Package Management | cnnickolay |
| Alex Gorelik | Wallet Apps, Tokenomics | aagorelik |
| Davide Falcone | DeFi & Liquidity, Financial Workflows | davidefalcone-c8 |
| Alex Sumner | Attestor Pools / DAOs | azubr |
| Roman Borovtsov | Node Deployment & Operations | YoungBarick |

Cantor8 runs the *Build on Canton* hackathon this project was built for. No
Cantor8 member sits in the Security or Identity SIGs, so Cantor8 is a route to an
introduction and a sanity check — **not** the Champion for RFP 27. Treating it as
the latter would be asking the wrong people to vouch for the wrong thing.

---

## Order, and why

**1. Cantor8 first — but as a review, not an ask.**

The relationship already exists. Use it to find out whether the framing survives
contact with someone who knows Canton and has no reason to be polite. Niko
Cherkezishvilli is the closest technical match (Daml Tooling, Token Standards, DAR
lifecycle). The question to ask is not "will you champion this" — it is "does this
read as infrastructure or as an application, and where is it wrong?"

If the answer is "this is an application", the proposal is not ready and no amount
of routing fixes that. That is a useful outcome for the cost of one message.

**2. Security SIG — the substantive conversation, and where the Champion should
come from.**

Only after step 1. Open in the SIG's Slack channel rather than by direct message:
the process says discuss the need with the SIG, and a channel post is a discussion
where a DM is a solicitation. Edward Newman (Digital Asset) is the natural anchor —
he also sits in Daml Language & Developer Tooling and DAR Package Management, so he
sees both the security and the toolchain side.

**2b. Daml Language & Developer Tooling SIG — for the RFP 22 proposal, and the
warmer of the two routes.**

Sixteen members, the largest SIG on the list, and **Niko Cherkezishvilli of
Cantor8 is in it** — the same person step 1 goes to. That makes RFP 22 the
proposal with the shortest path from a conversation you are already entitled to
have to a Champion who is already in the right room.

Two consequences worth acting on. **File RFP 22 first** if only one can go first:
the scope is smaller, the deliverable already runs in CI, and the route is
warmer. And approach OpenZeppelin directly rather than around them — they own
`daml-lint`, `daml-props` and `daml-verify`, they were funded by this same Fund
(#262), and Milestone 1 commits to asking them whether this belongs inside
`daml-props`. Asking first is both the honest move and the one that turns the
most obvious objection into a collaborator.

**3. Identity & Metadata SIG — alignment, deliberately not a funding ask.**

Milestone 3 commits to a written alignment note agreed with this SIG. Approach it
as what it is: a boundary question. *This work records whether an authority was
exercised or refused. Credential issuance is yours. Where should the line sit?*
Going in with a funding request would compete with their own roadmap area and
invite a rejection that costs the RFP 27 route too.

---

## What to send

Short. The Fund's AI policy is explicit that padded, plausible-sounding
submissions "may be closed without further discussion", and the same standard
should be assumed for a first message. Three paragraphs, no attachments beyond one
link, and nothing that cannot be defended line by line.

The shape that works:

1. **The problem, in the SIG's own terms.** Under Canton's privacy model,
   compliance evidence has to be produced by the participant whose conduct is in
   question, and refused authorisations leave no ledger artefact at all.
2. **What exists already, with one number and a link.** Not a feature list. The
   strongest single fact is that 30 of 30 Daml fences are mutation-tested — delete
   any one and a *named* test goes red — because it is checkable in a clone and it
   demonstrates the method, not just the artefact.
3. **One question, and an offer to be told it is wrong.** "Does RFP 27 want this,
   or is it already covered by work I have not found?"

Do not attach the proposal in the first message. Do not ask for a Champion in the
first message. Both come after somebody has said the problem is real.

---

## What to expect to be asked, and the honest answers

**"Who else uses it?"** Nobody yet, and say exactly that. Three implementations,
all written by you.

What you CAN say is that trying it costs nothing: `pip install
knowyouragenticai-receipts` (1.0.0, MIT, zero dependencies, published 6 September
2026), or a web page that needs no install at all. **That is distribution, not
adoption**, and conflating the two is the fastest way to lose a reviewer who
checks — which is the kind of reviewer worth having.

This is why Milestones 3 and 4 are adoption-gated: half the grant is not paid if
nobody adopts it. Do not dress this up; the review process names "adoption metrics
or success criteria are missing" as a standard reason for revision, and inventing
adoption is worse than lacking it.

**"Why not just sign the log?"** Signatures answer *who wrote this*, and require key
distribution to verify. The anchor answers origin on-ledger; the chain answers
integrity with nothing installed. They are different questions.

**"Isn't this what Hacken's monitor does?"** No, and say so precisely. Hacken's
monitor observes at a participant's own trust boundary and reports to that
participant's operator. This is the artefact that operator hands to someone who
does not trust them. Complementary, one layer down.

**"You are one person."** True, and it is a real risk to the committee. Milestone 4
requires a named second maintainer with commit rights, inside the grant rather than
after it.

**"How much of this was AI-written?"** Answer honestly — the policy says there is no
requirement to mark it, but "do not hide it if asked." The defensible position is
that every quantitative claim is reproducible from a clean clone with a documented
command, and that the applicant can explain why each element is there. That is the
standard the policy actually sets: not who typed it, but whether you can defend it.

---

## Decision gates

Stop and reconsider rather than pushing forward if any of these happen.

- **Cantor8 reads it as an application, not infrastructure.** All 8 funded new
  proposals are protocol or toolchain work; none is an application. Reframing is
  cheaper before filing than after.
- **The Security SIG says RFP 27 is already covered.** Then the useful move is to
  ask what is *not* covered, not to file anyway.
- **OpenZeppelin says this belongs inside `daml-props`.** Then it does, and the
  RFP 22 proposal becomes a contribution to their tool rather than a fourth
  binary. That is a better outcome for the ecosystem and a cheaper one for the
  Fund; the proposal already says so in writing.
- **No Champion after a genuine conversation with both SIGs.** File as
  `Needs Champion` only if a reviewer has suggested it. Otherwise the proposal
  joins the 91.

---

## Before any of this

The proposal states 2,471 PyPI downloads and describes them accurately, including
that the figure contains CI and mirror traffic. Every other number in it was
re-verified on 2026-09-06. Keep that true: if a figure moves, change the document
before sending it anywhere. The one asset this proposal has that most of the 91 did
not is that its claims survive being checked, and that is worth more than any
introduction.
