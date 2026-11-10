# How a Canton Dev Fund proposal actually reaches a vote

Measured 10 November 2026 with `python3 tools/vote_pipeline.py`. The tool
reads the live repository and refuses to print numbers if its own positive
control on proposal #942 fails. Re-run it before quoting any figure here.

**This document was wrong on 9 November and is corrected below.** It said
#866 "died". It did not. Its vote expired unvoted on 6 November and a second
vote was opened on 9 November. The tool missed it because the tool counted
labels, and a re-opened vote has its label reset. The correction is the
finding.

For 43 days #860 was pushed with the question "who will champion this". That
was the wrong question. The mechanism is not a championing process. It is a
vote that one person opens by hand and a committee clears in a weekly
meeting, and #860 has never entered it.

## Disclosure

I have a financial interest in this subject. **Canton Dev Fund proposal #860
is mine**, it asks for 300,000 CC, and at the time of writing no vote has ever
been opened on it. The mechanism described below is the mechanism my own
proposal is stuck in.

That is a reason to check the numbers rather than take them. Every figure here
comes from `tools/vote_pipeline.py`, which reads the live repository, refuses
to print anything if its positive control on #942 fails, and can be run by
anyone with `gh` installed. Where a figure of mine was wrong, the correction
is in the document rather than quietly replaced.

No sponsorship, no commercial relationship with the Canton Foundation, and no
payment from anyone for this work.

## The rules, from `.github/.gitvote.yml`

| Setting | Value | What it means |
|---|---|---|
| `automation.enabled` | `false` | No vote is ever created automatically. Every one is opened by a person. |
| `duration` | `21d` | A vote that nobody calls within 21 days closes and fails. |
| `pass_threshold` | `51%` | Of **allowed voters**, not of votes cast. An absent voter is a no. |
| `allowed_voters.teams` | `tech-ops-voting` | One team. Recent votes show five eligible, so three binding "In favor" are needed. |
| `audit.enabled` | `true` | The history is public at gitvote.com/audit/canton-foundation/canton-dev-fund. |

## What the history says

Of 400 proposals read, **29 have ever reached a vote (7.2%)**. Eight have
passed. Seven votes have failed, which is not the same as seven proposals:
see the section below on why counting by label gives three.

**Every one of those 29 votes was opened by @hythloda.** Not one was opened
by anybody else. That is the gate, and it is a single person.

Passed votes carry 3 or 4 yes (mean 3.5). Failed votes carry 0 to 2
(mean 0.7). In the entire history **one vote has ever recorded a single
"against"** (#300). Proposals do not die of rejection here. They die of
absence.

Three failures had **nobody vote at all**: #866, #853, #577, each 0 in
favour, 0 against, 0 abstain, 5 did not vote.

## Votes are cast in a meeting, not reviewed asynchronously

Binding-vote timestamps cluster into sittings minutes wide:

| Sitting | Binding votes | Span |
|---|---|---|
| 2026-10-19 **Mon** 09:52 UTC | 6 | 203 min |
| 2026-10-21 Wed 12:17 UTC | 10 | 13 min |
| 2026-10-28 Wed 12:40 UTC | 7 | 19 min |
| 2026-11-04 Wed 12:20 UTC | 20 | 73 min |

Gaps of 2, 7 and 7 days. Three of the four are Wednesdays starting within
twenty-three minutes of each other, and on 4 November the committee cleared
four proposals in 73 minutes.

The fourth is a Monday morning spread over more than three hours, which does
not look like a meeting at all. An earlier reading of only two proposals
suggested a fortnightly cadence; the full set says weekly with one
exception. Both readings were produced by the same person looking at the
same repository, which is the argument for the tool over the note.

**This is an observed pattern over four sittings, not a published
schedule**, and one of the four does not fit it. The next sitting is probably
Wednesday 11 November around 12:20 UTC. Nobody has confirmed that. Asking
the Foundation for the actual calendar is in ASK-THE-ORGANISERS.md.

## A failed vote is not final, and the labels hide that

On **16 October 2026 at 16:46 and 16:47**, within ninety seconds, @hythloda
opened votes on a batch of proposals. Twenty-one days later, on
**6 November**, seven of them closed without passing. Every tally:

| Proposal | In favour | Against | Abstain | Did not vote | Re-opened |
|---|---|---|---|---|---|
| #866 | 0 | 0 | 0 | 5 | 9 November |
| #853 | 0 | 0 | 0 | 5 | no |
| #577 | 0 | 0 | 0 | 5 | **10 November** |
| #813 | 1 | 0 | 0 | 4 | 6 November |
| #453 | 1 | 0 | 0 | 4 | 9 November |
| #300 | 1 | 1 | 0 | 3 | no |
| #752 | 2 | 0 | 1 | 2 | no |

Three findings, in order of how much they change what you would do.

**Six of the seven recorded no vote against at all.** One proposal in the
entire set, #300, drew a single objection. The others did not fail because
anybody disagreed. They failed because three of five eligible voters did not
vote, and under a threshold of 51% of allowed voters an absence counts as a
no. The Dev Fund's failure mode is not rejection. It is non-attendance.

**Four of the seven were re-opened within four days.** #813 the same day it
expired, #866 and #453 on 9 November, #577 on 10 November while this document
was being written. The same person who opened the first vote opened the
second. So a failed vote is a restarted clock, not a verdict.

**The labels make the first failure invisible.** `gitvote/passed` and
`gitvote/failed` describe a proposal's current state. When a second vote
opens, the label resets to `gitvote/open`. Count by label and the repository
reports three failures. Count by vote event and it reports seven. This tool
counted by label until 10 November and was therefore wrong by four, in the
direction that made the process look more decisive than it is.

That last one is the reason the method matters more than the numbers. Reading
`gh pr list --label gitvote/failed` is the obvious measurement and it gives a
wrong answer, silently, with no way to tell from the output.

`vote_events()` in `tools/vote_pipeline.py` reads the git-vote comments
instead, so a "Vote closed. The vote did not pass." that has since been
papered over by a new vote still counts.

### What this means for a proposal author

#866 had everything #860 is accused of lacking: a champion, two rounds of
revisions answering committee feedback, and four organisations publicly
backing it by name. Its vote opened, ran the full 21 days, and nobody voted.
Both the 28 October and 4 November sittings fell inside its window. It was
called at neither.

So **opening a vote is necessary and not sufficient.** The proposal has to be
called in the room while the clock is running, and the people with binding
votes have to be in the room.

@shaul-da commented on #866 on 8 November, two days after it closed: "I'll
miss the next meeting so voting yes in advance." Even a supporter lost track
of the window. That is not a failure of will. It is a process with a
21-day deadline, no reminder, and no automation.

## Where #860 stands

`python3 tools/vote_pipeline.py 860` prints:

    gitvote       NO VOTE HAS EVER BEEN OPENED

Opened 27 September. 44 days as of 10 November. The 21-day clock has never started, because
nothing starts it automatically and the one person who starts them has not.

## What this changes

1. The ask is not "will you champion this". It is "will you open a vote,
   and will you call it at a sitting while the window is open".
2. It is addressed to @hythloda, because 29 of 29 votes were hers to open.
   Asking @zeroknowledger on 4 November was aimed at the wrong role.
3. Passing needs three of five to actively vote yes. Absence is a no, so
   the work before a vote is with the eligible voters individually, not
   with the proposal text.

## A second case, and it is not a proposal

Measured 2026-11-10 against `canton-foundation/canton-dev-fund#874`, the first
milestone of Hacken's approved grant (proposal #302, merged 2026-08-26). This
matters because it removes every excuse available to #866.

    gh api repos/canton-foundation/canton-dev-fund/issues/874/comments

The sequence, read off the thread:

| when | what |
|---|---|
| 2026-10-05 | `lwolski-hacken` marks the milestone delivered |
| 2026-10-07 17:12 | `@hythloda` comments `/vote`, git-vote opens it |
| 2026-10-28 17:12 | **Vote closed, did not pass. In favour 0.00%, against 0.00%** |
| 2026-11-04 13:44 | `@hythloda` comments `/vote` again |
| 2026-11-10 01:02 | `@hythloda` comments `/count-vote`, 3 in favour, vote still open |

Hacken had everything a proposal is told it needs. An approved grant. Funded
work delivered and public under Apache-2.0. Support in the thread from a
Digital Asset employee. Reviewers from Obsidian and IntellectEU who later voted
in favour. **The first vote still died at zero in favour and zero against, the
same way #866 did**, and it only moved because the one person who can open a
vote opened a second one.

Three things this settles that one case could not:

1. The no-quorum death is **not** a judgement on the proposal. A delivering
   grantee hit it. Reading #866's failure as "the work was not good enough" was
   wrong, and so is reading #860's silence that way.
2. **Being called a second time is a real outcome**, and it is available. Not
   passing is not the end of the path; nobody calling it is.
3. The opener is the same person in both cases, which is the third independent
   confirmation that `automation.enabled: false` means a human starts every
   vote and that human has been @hythloda 29 times out of 29.

## Caveat on the voter count

#863, concluded 21 October, carries 12 binding votes rather than 5. The
allowed-voter set has not been constant. The "three of five" arithmetic
holds for votes concluded in the last month and should be re-read from the
tool rather than assumed.
