# New thread: the denominator

**Where:** forum.canton.network, category **App Development**
**Tags:** `daml`, `canton`

A post, not a reply, so a little length is earned. Not 900 words of it.

**Title:**

```
An auditor can only check a sample if they trust the denominator
```

**Not in it:** PR #860, the Dev Fund, the word champion. If a committee member
reads it and wants to talk, the work is on the page.

---

## THE POST

Six weeks ago I asked here how you prove an app did not do something.

Federico Rodriguez gave me the answer that mattered. A chain of receipts
written by my own app cannot prove I left one out. He was right, and no hash
fixes it, because I choose what to hash.

So I stopped trying to prove a negative. I published a number instead.

One contract per owner and actor. Every attempt consumes it and puts it back
with the count up by one. The auditor observes that contract, so they read the
count off the ledger, not off what I hand them.

Fifty attempts. Refusals at 3, 7 and 19. I show them two records. They know one
is missing and which one.

They still cannot see the 47 that were allowed. Not what, not to whom, not how
much. The count is theirs. The content is not. I think that middle position is
what regulated firms actually need, and a transparent ledger cannot offer it.

The work and the count commit in one transaction, so skipping the count means
skipping the work.

Two limits, before anyone finds them.

I wrote a contract key first, to force one journal per pair. Daml-LF 2.1
removed contract keys and the build refuses it. So a second journal is possible
and the auditor sees both. Detection, not prevention. **If anyone knows the
Daml 3 way to enforce uniqueness, I would like to hear it.**

And nothing forces an app to use the journal at all. The hole moves from any
attempt, invisibly, to a code path a reviewer can look for.

It has never run on DevNet. No credential. Twenty Daml scripts and a design
until then.

https://github.com/dominicrume/cantor8_kya_rails/tree/main/step-0-refusal

When a policy check stops something in your app today, what gets written down,
and who can read it without asking you?
