# New thread: the auditor reading the denominator

**Where:** forum.canton.network, category **App Development**
**Tags:** `daml`, `canton`
**Why a new thread and not a reply:** the September thread was a question. This
is a result, and it answers a question somebody else asked and nobody replied
to. A thread titled as a question gets read by people who have that question.

## What this is doing, in order

1. It answers Vacuumlabs' public question from 27 August, which has sat
   **51 days with 58 views and zero replies**. They asked who needs delegated
   automation. Answering a named firm in public is worth more than any pitch,
   and it is also the honest reason to post.
2. It credits Federico, who specified the fix for free, and reports what his
   objection cost to close and what is still open.
3. It names the Daml 3 limitation that shaped the design, which is the kind of
   detail that tells a reader the thing was built and not described.
4. It asks nothing. No champion, no review, no stars. If a Tech and Ops member
   reads it and wants to talk, the work is on the page.

**Do not** mention PR #860, the Dev Fund, or a champion in this post. That is
the whole discipline. A post that helps and asks for nothing is the only kind
that earns the reply you actually want.

## The title

> An auditor can only check a sample if they can trust the denominator

## THE POST

Six weeks ago I asked here how you prove an application did not do something.
Federico Rodriguez answered with the objection that mattered, and I want to
report back on what closing it actually took, because the interesting part is
the half that is still open.

His point was that a hash chain of receipts written by the application cannot
prove a receipt was omitted. He was right, and no hash chain fixes it. The
producer chooses what to commit to, so a producer who never writes the entry
computes the digest over the shorter list and it verifies perfectly.

So I stopped trying to prove a negative about records.

The thing an auditor actually needs is not a complete set of records. It is a
number they did not get from you. Publish the count and the problem inverts:

```
attempts = 50, refusals at positions [3, 7, 19]
records handed over = 2
-> one refusal is missing, and it is position 3, 7 or 19
```

One contract per owner and actor, consumed and recreated by every attempt,
holding the count and the refused positions. The auditor is an observer of that
contract, so they read the number off the ledger rather than off a disclosure I
assembled for them.

The application exercises it in the same transaction as its real work. Daml
commits a transaction whole or not at all, and that is the entire load-bearing
fact here: the work and the increment cannot come apart. Skipping the increment
means skipping the work.

What the auditor still cannot see is the 47 attempts that were allowed. Not
what they were, not to whom, not for how much. The count is disclosed, the
content is not. I think that middle position is the one regulated firms
actually need, and it is the one a transparent ledger cannot offer: disclose
the numerator too and nobody can use it.

Two things about it are limits rather than features, and I would rather write
them here than have someone find them.

**There is no contract key.** I wrote one first. Daml-LF 2.1 removed contract
keys and `daml build` refuses the clause outright, so there is no way to make
the ledger reject a second journal for the same pair. What it does instead is
show the auditor, who observes every journal naming them. Two live journals for
one pair is the finding, and an operator who opens one has created the evidence
against themselves. Detection, not prevention. If somebody knows the idiomatic
Daml 3 replacement for key-enforced uniqueness, I would genuinely like to hear
it.

**The module cannot force an application to route through it.** An application
with a second, unjournalled path to the same asset has a hole and nothing it
imports can see that. What changes is where the hole has to be: from any
attempt, invisibly, to a code path a reviewer can go and look for. There is a
test asserting that limit, so the claim cannot quietly grow past the code.

### Why I built this instead of something else

Vacuumlabs asked here on 27 August whether any team needs delegated automation,
and nobody answered. I do, and this is the part I needed.

Their design runs bounded actions with on-chain checks: run count, cooldown,
expiration, a revokable authorization. Now consider the moment a check says no.
The transaction aborts. Nothing commits. The run their authorization correctly
stopped leaves no trace on the ledger at all.

The control worked, and there is no evidence it worked. The only record is a
line in the operator's own log, written by the operator, about the operator.
That is the artefact a regulated client ends up handing an auditor when asked
to show the automation was actually bounded.

That is the half I build, and it composes with theirs rather than competing:
one module, no dependencies past the standard library.

https://github.com/dominicrume/cantor8_kya_rails/tree/main/step-0-refusal

Twenty test scripts. MIT. Take it, fork it, or copy the twenty lines.

### What I cannot claim

It has never run on DevNet. I have never had a credential, so everything above
is proven in Daml Script and is a design until it runs on a real ledger. If
that matters to you, weigh it accordingly.

And Federico was not the first person to the completeness idea. CAP-SRP
published the invariant in February. Worth knowing if you ever point anyone at
this.

### The question

For those of you running automation on behalf of a client: **when a policy
check stops a run today, what gets written down, and who can read it without
asking you?**

That is the whole thing I am trying to find out, and I would rather hear that
the answer is "nothing, and nobody minds" than keep building on a guess.
