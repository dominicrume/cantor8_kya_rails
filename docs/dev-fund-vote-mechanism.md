# How a Canton Dev Fund proposal actually reaches a vote

Measured 9 November 2026 with `python3 tools/vote_pipeline.py`, and extended
with a second case on 10 November. The tool reads
the live repository and refuses to print numbers if its own positive control
on proposal #942 fails. Re-run it before quoting any figure here.

For 43 days #860 was pushed with the question "who will champion this". That
was the wrong question. The mechanism is not a championing process. It is a
vote that one person opens by hand and a committee clears in a weekly
meeting, and #860 has never entered it.

## The rules, from `.github/.gitvote.yml`

| Setting | Value | What it means |
|---|---|---|
| `automation.enabled` | `false` | No vote is ever created automatically. Every one is opened by a person. |
| `duration` | `21d` | A vote that nobody calls within 21 days closes and fails. |
| `pass_threshold` | `51%` | Of **allowed voters**, not of votes cast. An absent voter is a no. |
| `allowed_voters.teams` | `tech-ops-voting` | One team. Recent votes show five eligible, so three binding "In favor" are needed. |
| `audit.enabled` | `true` | The history is public at gitvote.com/audit/canton-foundation/canton-dev-fund. |

## What the history says

Of 400 proposals read, **27 have ever reached a vote (6.8%)** and 14 have
concluded: 8 passed, 6 failed.

**Every one of those 27 votes was opened by @hythloda.** Not one was opened
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
| 2026-10-21 Wed 12:17 UTC | 10 | 13 min |
| 2026-10-28 Wed 12:40 UTC | 7 | 19 min |
| 2026-11-04 Wed 12:20 UTC | 20 | 73 min |

Three consecutive Wednesdays, gaps of 7 and 7 days, all starting around
12:20 UTC. On 4 November the committee cleared four proposals in 73 minutes.

An earlier reading of only two proposals suggested a fortnightly cadence.
The full dataset says weekly. That is why this is a tool and not a note.

**This is an observed pattern over three sittings, not a published
schedule.** The next sitting is probably Wednesday 11 November around 12:20
UTC. Nobody has confirmed that. Asking the Foundation for the actual
calendar is in ASK-THE-ORGANISERS.md.

## Why #866 died, and the warning in it

#866 had everything #860 is accused of lacking: a champion, two rounds of
revisions answering committee feedback, and four organisations publicly
backing it by name on the thread. Its vote opened and ran. Both the
28 October and 4 November sittings fell inside its 21-day window. It was
called at neither. It closed on 6 November with nobody having voted.

So **opening a vote is necessary and not sufficient.** The proposal has to
be called in the room while the clock is running.

@shaul-da then commented on 8 November, two days after close: "I'll miss the
next meeting so voting yes in advance." Even a supporter lost track of the
window.

## Where #860 stands

`python3 tools/vote_pipeline.py 860` prints:

    gitvote       NO VOTE HAS EVER BEEN OPENED

Opened 27 September. 43 days. The 21-day clock has never started, because
nothing starts it automatically and the one person who starts them has not.

## What this changes

1. The ask is not "will you champion this". It is "will you open a vote,
   and will you call it at a sitting while the window is open".
2. It is addressed to @hythloda, because 27 of 27 votes were hers to open.
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
   vote and that human has been @hythloda 27 times out of 27.

## Caveat on the voter count

#863, concluded 21 October, carries 12 binding votes rather than 5. The
allowed-voter set has not been constant. The "three of five" arithmetic
holds for votes concluded in the last month and should be re-read from the
tool rather than assumed.
