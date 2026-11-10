---
name: ecosystem-mechanics
description: How the Canton ecosystem actually decides things, measured rather than assumed. Use before asking anyone for anything, before writing a proposal or a forum post, and whenever a plan depends on somebody else saying yes. Covers the Dev Fund vote mechanism, the review pipeline, the CIP route, and who is who.
---

# Ecosystem mechanics

Forty-three days were spent asking for a champion when the gate was a vote nobody
had opened. The lesson generalises: **find the mechanism before arguing the
merits.** A plan aimed at the wrong gate fails no matter how good the work is.

Measure it, do not recall it:

    python3 tools/vote_pipeline.py
    python3 tools/vote_pipeline.py 860
    python3 tools/champions.py
    python3 tools/ecosystem_scan.py

`vote_pipeline.py` carries a positive control: if it cannot reproduce a known
vote it refuses to print any number rather than printing a plausible wrong one.
Full working in `docs/dev-fund-vote-mechanism.md`.

## The Dev Fund vote, as measured 9 November 2026

From `.github/.gitvote.yml` in `canton-foundation/canton-dev-fund`:

- `automation.enabled: false`. **No vote is ever created automatically.** Every
  one is opened by hand.
- `duration: 21d`, `pass_threshold: 51`, `allowed_voters.teams: [tech-ops-voting]`,
  `close_on_passing: true`, `close_on_passing_min_wait: 2d`.
- The threshold is 51% **of allowed voters, not of votes cast**. With five
  eligible, three must actively vote yes and an absence counts as a no.

From the repository's own history:

- 27 of 400 proposals have ever reached a vote at all, 6.8%.
- **All 27 votes were opened by @hythloda (Amanda Martin). Not one by anybody
  else.** That is the gate.
- Of 14 concluded: 8 passed, 6 failed. Passed votes drew 3 to 4 yes, mean 3.5.
  Failed votes drew 0 to 2, mean 0.7. Three had **nobody vote at all**: #866,
  #853, #577.
- Exactly one vote in the whole history records an "against" (#300). **Proposals
  die of absence, not rejection.**
- Binding votes arrive in clusters, which means a roll call in a meeting rather
  than async review: 21 Oct Wed 12:17 UTC, 10 votes in 13 minutes; 28 Oct Wed
  12:40, 7 in 19 minutes; 4 Nov Wed 12:20, 20 in 73 minutes. Gaps of 7 and 7 days.
  **Weekly Wednesday around 12:20 UTC is an observed pattern over three sittings,
  not a published schedule.** Reading two proposals suggested fortnightly; the
  full dataset said weekly. That is why this is a tool and not a note.
- Caveat kept deliberately: #863 drew 12 binding votes, so the allowed-voter set
  has not been constant.

**Why #866 died.** It had a champion (Yiannis Varelas, 9 October), two revisions
and four named public backers. Both the 28 October and 4 November sittings fell
inside its 21-day window and it was called at neither. The vote closed 6 November
with 0 in favour, 0 against, 0 abstain, 5 did not vote. **A champion is necessary
and not sufficient. Being called in the room is the thing.**

## The review pipeline

From the fund's own `Development Fund Proposal Review Process.md`:

Proposal Submitted, SIG reviewer self-assigns, In Review, Needs Revision loop,
Ready for Vote (about a week), then Voting Committee plus Core Contributors plus
Security review, then the vote. Board:
`github.com/orgs/canton-foundation/projects/3/views/1`.

Three sentences that change the ask:

- A proposal "moves to 'In Review' once it has been assigned to a champion **or
  reviewer**". A reviewer is enough to move it out of the queue.
- SIG members "may use the proposal tracking board to self assign proposals they
  want to review directly".
- "Participation in SIGs is **not limited to Foundation members**."

`AI_POLICY.md` in the same repository: submissions that are "overlong and padded"
or "filled with bot-style prose" may be **closed without further discussion**, and
repeat submissions may lead to being blocked. The #860 comments run to 2,475
characters. Everything goes short.

## Labels are not declarations

#860 carries six RFP labels and declares one. Line 8 declares RFP 27 only; the
labels were applied by the SIG auto-labeller matching keywords in the body, not by
the author, and only a maintainer can change them. A proposal that answers six
calls reads as a proposal that answers none.

## The CIP route

The draft was introduced to cip-discuss as message #909 on 30 October 2026. Note
two live problems before relying on it: the header says `Type: Standards Track`
while the abstract says it "changes no protocol behaviour, requires no new Ledger
API service, and needs no participant configuration", and one of those is wrong;
and #909 describes a draft that has since gained a second conformance requirement
and a narrowed Motivation, so a reader checking the file against the message finds
a mismatch.

cip-discuss content is not reposted to social media or other public forums.

## People, with what is actually known

Name, affiliation and date, or do not name them. A reply once described a forum
poster as working at Digital Asset; he works at C7, and the affiliation had been
inferred from the quality of his writing and a file path he quoted.

- **Amanda Martin (@hythloda)**, Canton Foundation. Opened every vote in the
  repository's history. Asked on 21 October 2026 for an overlap assessment before
  a vote, which was written covering all three RFP 27 proposals, with the interest
  declared in its first line (`docs/rfp-27-overlap.md`), and posted on #866 on 22
  and 31 October.
- **Edward Newman (@nycnewman)**, Digital Asset. Has reviewed 13 Dev Fund
  proposals including #788 under the same RFP and #262 (OpenZeppelin's stack), and
  sits in the Security column of the Tech and Ops roster.
- **Georgi Radev**, Community Tech Partner. Two corrections, 27 October and forum
  topic 9323, both of which cost a claim and improved the specification.
- **Leonid (@leonidr)**. Corrected the Motivation on 30 October, forum topic 9114.
- **Simon Meier**, Digital Asset. The EventLog pattern in CIP-0112, cip-discuss
  30 October. Also the batching criticism that sharding does not answer.
- **Brian Healey**, Digital Asset. Closed dpm #331 correctly.
- **Yiannis Varelas**. Championed #866 on 9 October.

Three merged pull requests in a repository we do not own: Canton Developer Hub
#156, #160 and #168. #160 renders the links of nineteen entries, ours is one of
them, and the pull request is written about the other eighteen. That is the shape
of a contribution that would have been right regardless.

## Feedback contract

Report: the gate you identified, the command or URL that established it, the
single action that moves the thing through that gate, and who can take it. If the
answer is that nothing can be done from this side, say that plainly rather than
inventing an action.
