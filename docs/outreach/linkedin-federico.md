# LinkedIn: the Federico fact

**Status:** not posted.

## The one rule for this post

Post what happened. Never what it implies.

**True, and verifiable by anyone who opens the thread:** a Canton Community
Tech Partner reviewed the design, found the flaw, and the fix shipped the next
day with his name on it.

**Not true, and he could correct it in public:** that he endorsed the project.

Say the first. Readers reach the second on their own, and a conclusion somebody
reaches is held harder than one they were handed.

## Post this

```
I published a design for recording what an AI agent was refused.

A Canton Community Tech Partner read it and told me it was wrong.

His point: the receipts were written by my own application. A hash chain
proves nothing was edited. It cannot prove nothing was left out. An
operator who omits a refusal produces a chain that verifies perfectly.

He was right, and it was the whole problem.

He also described the fix. Stop aborting the transaction. Commit either
way: if the rule passes, do the thing; if it fails, write a record and
move no money. Both paths commit. The refusal then has an id and a time
that came from the ledger, not from the operator.

I built it the next day. His name is on the pattern, in the contract.

He also named the limit it does not fix, and that is written in there
too. An attempt nobody submits still leaves nothing behind.

Thread: https://forum.canton.network/t/9114
Code: https://github.com/dominicrume/cantor8_kya_rails

Best review I have had. It cost him ten minutes and it changed the
architecture.
```

## Rules for posting it

- **Do not tag him.** If he wants to be part of it he will comment, and a
  comment he chose is worth ten tags. A tag he did not choose is a claim on
  his name.
- **Do not name his employer.** "A Canton Community Tech Partner" is his public
  forum title. His employer is a fact about him you were not given for this.
- **Do not add a call to action.** No "DM me", no "hiring", no "open to work".
  The post is worth something because it is not an advert. Put the availability
  somewhere else.
- **Link the thread.** The whole strength is that it is checkable. A story
  about a review nobody can read is just a story.

## Why post this at all

It is the only public artefact that shows how you take being wrong. Anybody can
show working code. Far fewer can show an expert telling them their design was
broken, and the fix shipping the next day with the credit attached.

That is the thing a champion, a client, or an assessor is actually trying to
find out about you, and it cannot be claimed. Only shown.
