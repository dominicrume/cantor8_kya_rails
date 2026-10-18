# Getting a champion: the blueprint

*Written 17 October 2026, the night before the Cantor8 winners' dinner.*

## Why this is the only thing that matters on the proposal

The Dev Fund review process says a proposal moves to "In Review" **once it has
been assigned to a champion**. No champion, no review. Not slow review. None.

`PR #860` has read `Needs Champion` since 27 September. Zero reviews.

Three of the four proposals under RFP 27 have champions. Ours is the one that
does not, and two of them went to a vote on **16 October**, closing around
**6 November**.

This is not a merit problem. It is a procedural one, and procedural problems
are the cheapest kind to fix.

## What a champion actually is

Under CIP-0100 a champion must come from the **Tech & Ops Committee**.

**SIG membership alone does not confer champion status.** The directory says so
in those words. What SIGs do say they do is:

> *"Recommend proposals to appropriate members of the Tech & Ops Committee"*

So the path is two steps, not one. **Get a SIG member to recommend you. They
carry it to Tech & Ops.** Asking a SIG member to "be my champion" is asking for
something they cannot give, and it marks you as somebody who did not read the
directory.

## The people, and who to approach first

**Regulatory Compliance SIG** (auto-assigned to #860):

| Name | Organisation | GitHub |
|---|---|---|
| Julie Lascar | Digital Asset | |
| Kelly Mathiesen | Digital Asset | |
| Shaul Kfir | Digital Asset | `shaul-da` |
| **Nikos Andrikogiannopoulos** | **Metrika** | `nikos-metrika` |

**Security SIG:**

| Name | Organisation | GitHub |
|---|---|---|
| **Edward Newman** | Digital Asset (CISO) | `nycnewman` |
| **Richard Domikis** | **MPCH** | |
| **Stanislav German-Evtushenko** | **SBI Security Solutions** | `stas-sbi` |

## The warmest name, and it was there all along

**Stanislav German-Evtushenko (`stas-sbi`), SBI Security Solutions, is already
a requested reviewer on PR #860.** He is also on the Security SIG. As of
18 October he has not reviewed.

He is not somebody to go and find. He is already assigned. The other requested
reviewers are `tkatrichenko`, `hythloda`, `omaiko-intellecteu`,
`waynecollier-da` and `isegall-da`. Zero reviews have been submitted, and the
PR needs one approving review to merge.

This was missed for three weeks because nobody read the reviewer list on our
own pull request.

**Approach the non-Digital-Asset ones first.** Four of the seven are Digital
Asset, who are busy and heavily petitioned. Metrika, MPCH and SBI are
independent firms whose own work is monitoring, custody and security. They have
a reason to care and less noise to cut through.

**Edward Newman is the one who answers security questions on the forum.** He is
the most likely to read a technical post carefully. He also said publicly he is
not aware of any Canton security certification plans, which tells you the area
is thin and attention is available.

## Step 1, today, costs nothing

Submit the **SIG participation form**: https://wkf.ms/4qzsS3f

It grants Slack channel access. Access is not membership, and that is fine.
**The channel is where a recommendation starts.** Join Regulatory Compliance and
Security.

## Step 2, tomorrow at the dinner

**Correction, 18 October 2026.** This file said Jørgen Ouaknine was "Founding
Chairman of the Canton Foundation". **He is not.** The Foundation's own About
page lists him as a **Board Member**, and Global Head of Innovation and Digital
Assets at **Euroclear**. The **Chair of the Board is Dr Johnna Powell of DTCC**.
Calling a board member Chairman in front of the actual chair is how a
conversation ends, and this file nearly caused it.

If **Jørgen Ouaknine** is in the room he is still worth talking to, as is
anyone from C7, 7RIDGE or Alchemy. The ask is one sentence and it is not for
money:

> "My Dev Fund proposal is under RFP 27 and it has no champion, so it has never
> entered review. Who should I be talking to?"

**Ask for a name, not a favour.** A name costs him nothing and he will have one.

Same question to anyone from C7, 7RIDGE or Alchemy. They sit on committees.

## Step 3, Monday: fix what is broken before anyone looks

Three things are wrong with the proposal and all three are visible to a reviewer
before they read a word of the substance:

1. **It is in the wrong folder.** It declares RFP 27 alignment and sits in
   `/proposals/`, which the repo's own README reserves for work that does *not*
   respond to an RFP. The rival that got a vote filed under
   `/rfps/security-assurance-incident-readiness/`. **One file move.**
2. **Six labels.** `rfp-11`, `rfp-12`, `rfp-22`, `rfp-26`, `rfp-27` plus
   `regulatory-compliance`. The bot only ever adds labels and the body now
   matches only `rfp-27`, so these are stale residue. **Ask a maintainer to
   remove four**, with the keyword evidence.
3. **No adoption budget.** DevRel told another proposer on 31 August to
   allocate **~30% of total budget to adoption**, because "adoption should be
   the primary indicator of success". Ours is engineering-only.

## The framing that has to change

Every agent-themed Dev Fund proposal ever filed has been closed unmerged: #784,
#578, #381, #367. The one agent-mandate CIP, #202, was closed in August with
zero comments. Agentic AI appears **once** in the 269-line roadmap, as read-only
MCP data access.

**The agent framing has a perfect losing record here.**

RFP 27 asks, in its own words, for *"audit trails, compliance evidence... and how
privacy, access controls, and selective disclosure will be handled."*

So the proposal is not an AI agent wallet. It is:

> **A reusable Daml module that records refused authorisations as contracts, and
> discloses them to a named auditor party without disclosing the actions that
> were allowed.**

Every clause of that sentence is lifted from RFP 27's own text. Nothing in it
mentions an agent. The code does not change.

## The adoption half, which is also the champion half

Vacuumlabs (`arpitkarnatak_vl`) asked on forum 9084 on 27 August whether anyone
needs delegated automation. **Fifty-one days, 58 views, zero replies.** Their
PR #627 is open since 9 August and **also needs a champion**.

Their automation runs bounded actions with on-chain checks. When a check fails,
the transaction aborts and leaves nothing. That is exactly the gap this module
fills.

**Two proposals, same RFP area, both stuck on the same procedural step.** An
adopter named in a proposal is worth more than another page of engineering, and
a proposal that names a real adopter is far easier for a SIG member to carry
into Tech & Ops.

Answer them first. Ask for nothing. The champion conversation gets easier once
there is something to point at that is not your own work.
