# How a Canton Dev Fund proposal actually reaches a vote

Measured 10 November 2026 with `python3 tools/vote_pipeline.py`. The tool
reads the live repository and refuses to print numbers if its own positive
control on proposal #942 fails. Re-run it before quoting any figure here.

**This document has been wrong twice and is corrected below both times.**

On 9 November it said #866 "died". It had not. Its vote expired unvoted on
6 November and a second vote opened on 9 November. The tool missed it because
the tool counted labels, and a re-opened vote has its label reset.

On 10 November every rate in it was computed over the wrong denominator. The
tool read the proposal list with `gh pr list --limit 400`. The repository holds
616 proposals. A cap looks exactly like a count, so "29 of 400 reached a vote
(7.2%)" was really 29 of the most recent 400, and two vote-bearing proposals
outside that window, #161 and #197, were invisible. The true figure is 31 of
616, which is 5.0%.

Both errors have the same shape, and it is the shape this document is about: a
measurement that is wrong with nothing in its output saying so. `proposals()`
now refuses to return a capped list at all, and raises instead of handing back
a figure somebody would quote.

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

Of **616 proposals, every one in the repository, 31 have ever reached a vote
(5.0%)**. Ten have passed. Nine votes have failed, which is not the same as
nine proposals: see the section below on why counting by label gives four.

**Every one of those 31 votes was opened by @hythloda.** Not one was opened
by anybody else. That is the gate, and it is a single person.

Passed votes carry 3 or 4 yes (mean 3.5). Failed votes carry 0 to 2
(mean 0.8). In the entire history **one vote has ever recorded a single
"against"** (#300). Proposals do not die of rejection here. They die of
absence.

Five failures had **nobody vote at all**: #866, #853, #577, #672 and #161,
each 0 in favour, 0 against, 0 abstain, 5 did not vote.

## Votes are cast in a meeting, not reviewed asynchronously

Binding-vote timestamps cluster into sittings minutes wide:

| Sitting | Binding votes | Span |
|---|---|---|
| 2026-10-19 **Mon** 09:52 UTC | 6 | 203 min |
| 2026-10-21 Wed 12:17 UTC | 10 | 13 min |
| 2026-10-28 Wed 12:40 UTC | 7 | 19 min |
| 2026-11-04 Wed 12:20 UTC | 20 | 73 min |

### The cadence reading was wrong, and it is retired rather than patched

On 10 November this section said the next sitting was "probably Wednesday
11 November around 12:20 UTC" and that nobody had confirmed it. That
prediction was testable, so it was tested.

**Wednesday 11 November produced one binding vote, at 04:03 UTC.** Nothing at
or near 12:20. The five `gitvote/passed` labels that landed together at 09:32
were the bot's 21-day expiry sweep, not a meeting. The nearest thing to a
sitting that week was Tuesday 10 November: five binding votes spread from
13:03 to 20:47, seven hours wide, which is what people clicking when they get
to it looks like, not a room.

So the three tight Wednesday clusters were three busy afternoons, and three
points plus a miss is not a schedule. The claim is withdrawn. What survives it
is narrower and still useful: votes are cast in bursts by a handful of people,
there is no published calendar, and nothing in the repository tells an author
when their proposal will be called.

Asking the Foundation for the actual calendar is in ASK-THE-ORGANISERS.md, and
after this it is the only way to know.

## A failed vote is not final, and the labels hide that

On **16 October 2026 between 16:45 and 16:47**, inside two minutes, @hythloda
opened votes on a batch of proposals. Twenty-one days later, on
**6 November**, eight of them closed without passing. A ninth, #672, failed on
11 November. Every tally:

The 10 November version of this section said the batch began at 16:46 and that
seven failed. Both were artefacts of the 400-proposal cap: #161's vote was
created at 16:45:30 and was outside the window the tool could see.

| Proposal | In favour | Against | Abstain | Did not vote | Re-opened |
|---|---|---|---|---|---|
| #866 | 0 | 0 | 0 | 5 | 9 November |
| #853 | 0 | 0 | 0 | 5 | no |
| #577 | 0 | 0 | 0 | 5 | 10 November |
| #161 | 0 | 0 | 0 | 5 | no |
| #813 | 1 | 0 | 0 | 4 | 6 November |
| #453 | 1 | 0 | 0 | 4 | 9 November |
| #300 | 1 | 1 | 0 | 3 | no |
| #752 | 2 | 0 | 1 | 2 | no |
| #672 | 0 | 0 | 0 | 5 | **11 November**, 3h22m later |

#161 was outside the 400-proposal cap and so was missing from the 10 November
version of this table. #672 failed on 11 November, after it was published.

Three findings, in order of how much they change what you would do.

**Eight of the nine recorded no vote against at all.** One proposal in the
entire set, #300, drew a single objection. The others did not fail because
anybody disagreed. They failed because three of five eligible voters did not
vote, and under a threshold of 51% of allowed voters an absence counts as a
no. The Dev Fund's failure mode is not rejection. It is non-attendance.

**Five of the nine were re-opened, four of them within four days.** #813 the same day it
expired, #866 and #453 on 9 November, #577 on 10 November while this document
was being written. The same person who opened the first vote opened the
second. So a failed vote is a restarted clock, not a verdict.

**The labels make the first failure invisible.** `gitvote/passed` and
`gitvote/failed` describe a proposal's current state. When a second vote
opens, the label resets to `gitvote/open`. Count by label and the repository
reports four failures. Count by vote event and it reports nine. This tool
counted by label until 10 November and was wrong by five, in the direction
that made the process look more decisive than it is. The gap widens every
time a vote is re-opened, so the label count drifts further from the truth
on its own, with no edit to anything.

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

Opened 27 September. **46 days as of 12 November.** The 21-day clock has never
started, because nothing starts it automatically and the one person who starts
them has not. Six review requests are outstanding and not one has been
submitted. Between 9 and 11 November @hythloda opened seven votes. #860 was in
none of them.

## What this changes

1. The ask is not "will you champion this". It is "will you open a vote,
   and will you call it at a sitting while the window is open".
2. It is addressed to @hythloda, because 31 of 31 votes were hers to open.
   Asking @zeroknowledger on 4 November was aimed at the wrong role.
3. Passing needs three of five to actively vote yes. Absence is a no, so
   the work before a vote is with the eligible voters individually, not
   with the proposal text.
4. **A champion is neither necessary nor sufficient, measured.** Of the 31
   proposals that ever reached a vote, 24 carry no `champion-confirmed`
   label. 51 proposals carry that label and have never had a vote. So
   "find a champion" is not the mechanism either, and #860 not carrying it
   is not what is stopping it.

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
   vote and that human has been @hythloda 31 times out of 31.

## Caveat on the voter count

#863, concluded 21 October, carries 12 binding votes rather than 5. The
allowed-voter set has not been constant. The "three of five" arithmetic
holds for votes concluded in the last month and should be re-read from the
tool rather than assumed.
