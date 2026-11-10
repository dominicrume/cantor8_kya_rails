---
name: before-it-leaves
description: The gate on everything that leaves this machine. Use before any forum post, reply, email, pull request, issue, review, comment, proposal or outreach message, and before handing drafted text to Rume. Covers the championing test, verify-before-not-after, nothing-posted-that-is-not-built, creative-collaborative-short, and the spoonfeed delivery rule.
---

# Before it leaves

Outward actions are the only irreversible ones here. Code can be rewritten. A
sentence in somebody else's repository, under your own name, cannot.

## The question that outranks the rest

> Would I still do this if they never replied, never funded it, and never knew my
> name?

If no, it is leverage wearing the costume of a contribution, and it fails even
when it works. This was written after three hours of mutation testing
`digital-asset/daml-finance`, 71 fences in a company's flagship library, so that
71 unrequested findings could be handed to an organisation whose signature the
Dev Fund requires. OpenZeppelin had asked for exactly that work. Digital Asset
had asked for nothing and the repository had been frozen for seventeen months.
The run was stopped and their working tree restored.

Concretely forbidden: uninvited work aimed at someone we need something from;
volume (five messages in an afternoon is a campaign, not five conversations);
chasing ("did you see this?" is a debt collector); publishing what we learned
about people whose help we want.

## Order, not care

Build, test, break it on purpose, run the full sweep, push, **then** write the
message. Verifying afterwards produces a correct message most of the time, which
is exactly why that order survives until the day it does not. On 31 October 2026
a comment went onto somebody else's funding proposal quoting their own sentence
and linking a document nine commits behind a tree in which three reviewers had
just corrected claims in that very file. It held up. That is luck, not a method.

    python3 tools/before_posting.py docs/drafts/reply-leonid-9114-b.md docs/drafts/sources/leonid-9114-13.txt

It refuses a draft whose quote is in no source, whose link names a file that is
missing, uncommitted or unpushed, and whose affiliation claim carries no URL read
today. For every linked file of ours it prints when that file last changed
against HEAD and how many commits have landed since. The tool cannot know whether
those commits changed what the file claims. You can, and you say so out loud.

## Somebody else's repository

    python3 tools/before_contributing.py digital-asset/dpm

A **mechanism is not a defect.** Proving code behaves a certain way is not proving
it is wrong, and a maintainer's review time is the scarcest thing in the exchange.

**The tell is in the draft.** If the body needs a paragraph beginning "what this
does not claim", or any sentence of the form "I have no report of a user hitting
this", that paragraph is not honesty decorating a good filing. It is the reason
not to file. Write the sentence, read it, close the branch.

The record: dpm #330 merged in six days with no questions. dpm #331, same author,
same `Co-authored-by` trailer, was closed the next day with "AI contribution,
does not appear to be a true concern". The maintainer was right. The label is
what a reviewer reaches for once he has decided the substance is thin, which means
thin substance is what spends the credit. Keep the trailer. Raise the bar.

## Nothing is posted that is not built

Every reply reports something finished, tested and pushed. Not a plan, not a
design, not a half-fix with the remainder described. A developer once asked in her
own words for "sample implementations" and got four paragraphs of documentation
quotes with no code in them. She asked for code. The answer was to write the
module, test it, mutation-test it, and then reply with something she could paste.

A post about work in progress invites a conversation. A post about finished work
invites a user.

## Creative, collaborative, short

**Creative** means solve the problem rather than describe it. When something
cannot be done the way it is being attempted, the answer is a different mechanism,
not a paragraph explaining the obstacle. Contract keys could not enforce
uniqueness, so the auditor went on the signatory line. One counter serialised
every attempt, so there are N counters now.

**Collaborative** means the other person is a colleague, not an audience. Credit
them by name and date. Build what they suggested before replying. Never follow a
correction with a lesson: somebody who hands you a fact has earned a report on
what you did with it, not a fact handed back as payment. Never write "in case this
is useful to you" when you mean "look what I know".

**Short** means about 100 words. A reply matches the length of what it answers.
Four words get four lines. A four-question post gets four answers.

Two external constraints that bind hard: the Dev Fund's own `AI_POLICY.md` says
submissions that are "overlong and padded" or "filled with bot-style prose" may be
closed without further discussion. And no em dashes, anywhere.

## Delivery to Rume

Never the clipboard. Never a terminal command. Print the text in the chat reply,
name the page, name the box, name the button, in that order. One page at a time.
He pastes what is printed, so every fenced block is either runnable exactly as it
stands or carries a plain label above it saying what it is. No placeholders in
angle brackets, ever, because zsh reads `<draft>` as a redirect.

## Feedback contract

Report: the gate command run and its exit state; every quote and the source file
it was found in; every link and whether it resolves; the word count; and the
destination page, box and button. If anything is unverified, say which and stop.
Nothing is recorded as sent until the destination has been read back.
