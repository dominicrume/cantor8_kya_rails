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

All figures below measured 10 November 2026. Re-run the tool before quoting
any of them; the numbers moved between 9 and 10 November and the direction was
not the one anybody expected.

- 29 of 400 proposals have ever reached a vote at all, 7.2%.
- **All 29 votes were opened by @hythloda (Amanda Martin). Not one by anybody
  else.** That is the gate.
- **COUNT VOTE EVENTS, NOT LABELS.** `gh pr list --label gitvote/failed`
  returns three. Seven votes have actually failed. A re-opened vote has its
  label reset to `gitvote/open`, so the first failure stops being visible and
  the obvious measurement is wrong by four with nothing in its output saying
  so. Use `vote_events()` in `tools/vote_pipeline.py`, which reads the
  git-vote comments.
- Every failure, with its tally and whether the clock restarted:

  | Proposal | For | Against | Abstain | Did not vote | Re-opened |
  |---|---|---|---|---|---|
  | #866 | 0 | 0 | 0 | 5 | 9 Nov |
  | #853 | 0 | 0 | 0 | 5 | no |
  | #577 | 0 | 0 | 0 | 5 | 10 Nov |
  | #813 | 1 | 0 | 0 | 4 | 6 Nov |
  | #453 | 1 | 0 | 0 | 4 | 6 Nov |
  | #300 | 1 | 1 | 0 | 3 | no |
  | #752 | 2 | 0 | 1 | 2 | no |

- **Six of the seven record no vote against at all.** Exactly one objection
  exists in the whole history, on #300. **Proposals die of absence, not
  rejection.**
- **A failed vote is a restarted clock, not a verdict.** Four of seven were
  re-opened within four days, by the same person who opened the first.
- All seven were opened **within ninety seconds of each other** on 16 October
  at 16:46 and 16:47, so all seven expired on the same day. That is one batch,
  not seven decisions.
- Eight have passed, drawing 3 to 4 yes, mean 3.5.
- Binding votes arrive in clusters, which means a roll call in a meeting rather
  than async review: 19 Oct **Mon** 09:52 UTC, 6 votes over 203 minutes;
  21 Oct Wed 12:17, 10 in 13 minutes; 28 Oct Wed 12:40, 7 in 19 minutes;
  4 Nov Wed 12:20, 20 in 73 minutes. Gaps of 2, 7 and 7 days.
  **Weekly Wednesday around 12:20 UTC is an observed pattern over four
  sittings, and the Monday does not fit it.** Reading two proposals suggested
  fortnightly; the full dataset said weekly. That is why this is a tool and
  not a note.
- Caveat kept deliberately: #863 drew 12 binding votes, so the allowed-voter set
  has not been constant.

**#866 did not die, and this skill said it did until 10 November.** It had a
champion (Yiannis Varelas, 9 October), two revisions and four named public
backers. Both the 28 October and 4 November sittings fell inside its 21-day
window and it was called at neither. The vote closed 6 November with 0 in
favour, 0 against, 0 abstain, 5 did not vote.

Then @hythloda opened a second vote on **9 November**. The proposal is live
again.

Two lessons, and the second is about this file rather than about Canton.
**A champion is necessary and not sufficient; being called in the room is the
thing.** And a skill that states an outcome freezes it: this one taught "died"
for a day after it stopped being true. State the mechanism, name the tool, and
put the date on the number.

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
