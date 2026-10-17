# Follow-up to Federico, forum 9114

**Thread:** https://forum.canton.network/t/how-do-you-prove-your-app-didnt-do-something/9114
**Last post:** ours, 13 September. **34 days of silence. 112 views, 3 posts, 2 of them ours.**

Federico Rodriguez (Community Tech Partner, Moonsong Labs) made two points on
11 September and both were right:

1. The receipts are produced by the application, so you are trusting the
   application to include every attempt. A hash chain makes existing receipts
   tamper-evident. It does not prove one was omitted.
2. Make the refusal a valid Canton transaction. A choice that either performs
   the action or creates a `RejectedAttempt` record. Both commit.

We shipped point 2 the next day. Point 1 we acknowledged and left open.

**The reason to post again is that point 1 moved.** Not solved. Moved, measurably,
with a new spec section and a passing test that proves the part that is still
broken. Posting a half-fix and naming the remaining hole is worth more here than
posting nothing for another month.

**Do not** ask him for anything. Not a champion, not a review, not a reply.
Give him the update he earned and let it sit.

---

## THE POST

Federico, an update on your first point, five weeks on.

You said the chain cannot prove a receipt was omitted. That was the real hole
and I left it open.

Part of it is now closed and I want to be exact about which part.

A disclosure can hand over refusals and withhold the payments. The weakness was
not a removed entry, which the links already catch. It was a kept entry,
relabelled. Withhold a refusal, mark it accepted, and nothing contradicted you,
because a withheld body cannot be recomputed.

So every entry's position and outcome now has its own digest, same shape as a
seal. Change one label and it stops matching. Spec section 6c.

Here is the part that matters more. Alone it proves nothing. I write the
document and I could compute the digest over the same lie. Its value is that it
makes one anchorable value cover every outcome rather than just the chain. Pin
it somewhere I do not control, or it is decoration. The spec says that in those
words, and there is a passing test asserting that a producer who recomputes the
digest over a lie still verifies.

Then I went after the half you would have asked about next, because the digest
genuinely cannot reach it. An attempt that is never written leaves nothing, and
no commitment scheme gets there, since the producer chooses what to commit to.

So I stopped trying to prove a negative about records and published a number
instead. One contract per owner and actor, consumed and recreated by every
attempt, holding the count and the positions that were refused. The auditor
observes that contract, so they read the count off the ledger and not off a
disclosure I assembled. Fifty attempts, refusals at 3, 7 and 19, two records
handed over, and the auditor names the missing position without ever seeing its
contents.

The application exercises it in the same transaction as the real work. Daml
commits whole or not at all, so the work and the increment cannot come apart.
That is the thing you described, arrived at from the other side: omitting the
record and performing the action are now the same transaction.

Two limits, because you will find them anyway.

I wrote a contract key first, to force one journal per pair. Daml-LF 2.1
removed keys and the build refuses the clause, so uniqueness is detected rather
than prevented: a second journal appears in the auditor's own contract set,
unprompted. If you know the idiomatic Daml 3 replacement for key-enforced
uniqueness, I would like to hear it.

And the module cannot force an application to route through it. A second,
unjournalled path to the same asset is still a hole. What moved is where the
hole has to be, from any attempt invisibly to a code path a reviewer can look
for. There is a test asserting that limit so the claim cannot grow past the
code.

Still no ledger connection, so all of it is Daml Script and a design until it
runs on DevNet.

Two other things, since you spent real time on this.

I ran the same thinking at somebody else's code. Two OpenZeppelin Canton
packages, every authorisation condition deleted in turn. 49 of 62 could be made
vacuous with the whole suite still green. Their newer package is clean, and that
is in the report too.

And you were not the first to the completeness idea. CAP-SRP published the
invariant in February. Worth knowing if you ever point someone at this.

https://github.com/dominicrume/cantor8_kya_rails/blob/main/SPEC.md
