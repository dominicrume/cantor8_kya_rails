# New forum topic: what a ledger does not record

**Where:** https://forum.canton.network/new-topic
**Category:** App Development. That is where 9114 went, and it is the one that
got a substantive reply from a Canton engineer.
**Tags:** `daml`, `canton`
**Status:** not posted.

## The judgment call, said out loud

You asked for a post showing what the Franklin Templeton piece missed. I have
not written that post, and here is why, so you can overrule me knowing the
trade.

Naming a Head of Digital Assets at a large asset manager and saying she is
wrong is a bad trade at our size. It reads as a small project picking a fight
with a large one. The people who could champion us are in that world, not
against it. And we have just sent two short, plain replies that set a register
worth keeping.

**The argument is the asset. The target is not.** The claim in that article is
the standard formulation, not her invention, so the post below takes the claim
apart and names nobody. Anyone who has read the article will recognise it. That
is enough, and it costs nothing.

The long version with the citations already exists at
`docs/what-an-agent-was-stopped-from-doing.md`. That one is for a champion to
read, not for a forum.

## Why a question and not a statement

Both replies that worked were short and ended in a question. 9114 opened with
one and drew a Canton engineer who reviewed the architecture unprompted. A post
that only asserts invites agreement or silence. A post that asks invites the
person who knows better, and that person is who we want in the room.

Paste this.

**Title:**

```
On Canton, what evidence survives when an agent is blocked?
```

**Body:**

```
Auditability keeps being given as a reason to put agents on a ledger. Every
decision recorded, recallable later.

A ledger records what happened. It does not record what was prevented.

In Daml a failed assertMsg aborts the transaction. So a blocked payment
leaves nothing behind. What settled is on the ledger. What was stopped
sits only in your own logs, written by you, about you.

That is the wrong half to be vouching for. EU AI Act Article 12 and DORA
both ask you to evidence that a control operated. A control that operates
produces refusals.

So I stopped aborting. The choice now commits either way. If the rule
passes it pays. If it fails it writes a rejection record and moves no
money. The contract id and the time come from the ledger. An auditor
named in the mandate observes those records. Nobody else does. That is
the part a transparent chain cannot do.

MIT, and the code is in the thread I posted last week.

For anyone running agents on Canton: where do your blocked attempts live
today?
```
