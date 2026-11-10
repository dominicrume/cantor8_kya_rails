---
name: claim-discipline
description: How this company decides what is true and what may be said. Use before writing any number, any status row, any README line, any proposal sentence, or any recommendation about direction. Covers measure-not-remember, the three-state honesty table, how to kill an overclaim, and the drift trap where a number is frozen in prose.
---

# Claim discipline

The asset here is not the code. It is that a stranger can check every sentence.
One unchecked number costs more than ten unbuilt features, because it puts every
other sentence back in doubt.

## Four rules, each written after a failure

**Decide from the data, not from the story.** Before recommending a direction, go
and measure it, and say which numbers you read. The hackathon comparison was
expected to show the winners built more. It showed 1st place last committed 29
August with 34 commits, 2nd place 29 August with 21, and this repository 16
October with over 100. They stopped on the day and won on presentation. Every
plan built on the assumption would have been wrong.

**A number nobody has plotted is a rumour.** The same rule caught three live
overclaims in one week: "nobody else keeps the refusal half" (`khalydmaina/sentry`
does), "the EU AI Act requires this" (Annex III does not cover payments or
treasury), and "241 downloads a month" (84 once mirrors are excluded, and that
figure was already printed on a CV). If a claim cannot be checked by a stranger
in one command, it does not go in a document, a proposal, or a sentence said out
loud.

**Never a better yesterday.** A measurement that was true last month is not
evidence today. A claim that was defensible before a competitor shipped is not
defensible after. When something is found to be wrong it is corrected in the
open with the reason written down, and the correction is the work, not an
interruption to it. Nothing is quietly tidied to look better than it was.

**A record the actor writes about itself is not evidence, including ours.**
Anything recording what we did reads the destination before writing the line.
`tools/post_queue.py` once wrote "posted" on a keystroke and recorded two forum
replies that were never on the forum. It verifies now, and where a destination
cannot be checked it says CANNOT CHECK rather than looking like a pass.

## No execution without a measurement

Measure the thing you are about to act on, then act. The command before the
keystroke, the fetch before the quote, the lint before the commit, and reading
the result before reporting it.

This is the ordering rule applied to your own hands rather than to a draft.
`before_posting.py` already enforces it for messages. It has no equivalent for
the dozen smaller acts a session is made of: clicking a button, quoting a file
of ours, reporting that a command worked.

Eight instances were counted in one session on 10 November 2026, including
telling the owner to press a button his account could not press, reporting a
commit that did not exist because nothing was staged, and publishing a public
page that no lint covered and that failed three accessibility checks the moment
one did. Full list in CLAUDE.md with the rule.

Every one looked correct when it happened. Acting first works most of the time.
That is why it survives.

## Three states, never two

`STATUS.md` is the model and it is kept current, not written once:

- **PROVEN**: measured, reproducible, and checkable by a stranger. Every row
  carries the command.
- **MOCKED**: labelled in code and in any demo, with what would remove the label.
- **PENDING**: the honest gaps, worst first, each naming what it is blocked on.

Plus a fourth section that does more work than the other three: **NOT CLAIMED**,
the sentences deliberately not made because they would not survive being checked.

A check that cannot run must never look like one that passed.

## The drift trap

A number written into prose rots in place, because the commit that changes the
number does not touch the file that quotes it. `tests/balance_lint.py` exists for
this: it re-reads the live value and fails the commit when prose disagrees.

It only catches the patterns it has regexes for. **Live example, found 9 November
2026:** `tests/vectors.json` holds 20 cases, `README.md` says 20 because the lint
checks that exact markdown-link form, and `SPEC.md:390` plus `tools/dashboard.py:37`
still say 16 because neither matches the regex. Four vectors were added across
three commits and no line quoting the number was in those commits.

So: prefer naming the measuring command over freezing the number. Where a number
must appear in prose, add its pattern to `balance_lint` in the same commit.

## Killing an overclaim

1. Write the sentence down exactly as it currently stands.
2. Name the one command or URL a stranger would use to check it.
3. Run it. Record what came back.
4. If it does not hold, correct it where it was said, with the date and the
   reason, and leave the original visible. `SHORTCUTS.md` is append-only.
5. Ask whether the softer version is still worth saying. Often it is stronger.

## Feedback contract

Report: the claim, the command that checked it, the output, and the verdict in one
word (HOLDS, CORRECTED, CANNOT CHECK). On CANNOT CHECK, name what is missing.
Never substitute a plausible number for an unavailable one.
