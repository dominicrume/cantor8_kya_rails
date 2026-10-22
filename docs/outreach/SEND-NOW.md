# Everything to send, 22 October 2026

Seven messages. Written to be pasted, not edited. Order matters: Arpit first,
because his moment closes.

**One rule across all of them.** Nothing here describes work in progress.
Every claim is a thing that is built, tested and pushed, per the guardrail in
CLAUDE.md.

---

## 1. Arpit, Vacuumlabs. The one that changes your position.

**https://forum.canton.network/t/9084** → Reply

**Why now:** moritzkiefer-da reviewed PR #627 on 16 October and said it was
"extremely light on use cases" and "unclear what is ready code vs what users
implement". That is his problem this week. You are a named team with the use
case, and you have shipped code. He already cited your proposal unprompted.
He is one message from being your adopter and you from being his.

```
Arpit, an offer rather than a question.

I read the review on #627. If it is useful, I will go on the record as a
committed adopter of your Authorization, on the PR, with my name on it.

What I can state concretely: a spend-limited agent wallet that needs bounded,
revokable delegated execution. Yours is the piece I would adopt rather than
rebuild. I would name the checks I use on day one, what I integrate against,
and what I need from the interface. That is a named team with a real use
case, which is what the review said was missing.

I would ask for the same in return. You hit the evidence gap while building
and said so in public. A sentence to that effect on #860 would cost you
nothing and would mean a lot, because a problem confirmed by a named firm is
a different object to a problem described by the person solving it.

Neither of us is asking the other for money, and this is not a merge. Two
proposals in the same area pointing at each other are both easier to carry.

And one thing you know that I do not. You have had two Foundation people
engage on #627 and a formal review. Mine has had nothing in 35 days. How did
you get the first one to look?
```

---

## 2. PREDGE. They solved your problem for free.

**https://forum.canton.network/t/9114** → Reply

**Why this shape:** they wrote 100 words, no greeting, no sign-off, pure
content. Match it. Gratitude in a paragraph would be noise to this person.

```
Built it. One line, as you said.

The auditor is on the signatory line now and a second journal is impossible
to open without them. Three files in my repo said that could not be done
without contract keys. All three were wrong.

What I had missed is that it is free at runtime. A choice that recreates the
journal already carries its signatories' authority, so the auditor is only
needed to open one in the first place.

Your second idea I have not built. You named its cost yourself, everything
for one pair queueing behind a single contract. I went the other way, with a
guard party on the asset itself, which has no queue but needs a second
operator.

Have you run the queued version at any volume? That is the part I cannot
guess at.
```

---

## 3. pmjpawelec and Archana.

**https://forum.canton.network/t/9314** → Reply

**Why this shape:** he is a Community Tech Partner who wrote a generous
teaching answer and ended with "Happy to expand on this if something is still
unclear." He is a helper. Thank him properly, then add, then help Archana.
Do not correct him.

```
Przemek, that is the clearest answer to this I have seen on here, and the
consuming choice is the part most people miss.

Two things I ended up adding when I shipped this, in case they are useful.

A ceiling as well as a floor. Blocking an early run is the easy half. The one
that hurts is a run that lands a week late because the scheduler was down,
because a late interest payment nobody notices is far worse than one that
failed loudly.

And a count that runs out, so the schedule ends itself. A recurring payment
nobody remembers is how a treasury empties quietly.

Archana, one more thing for your three cases. When the scheduler fires at the
wrong time the transaction is thrown away, so nothing on the ledger says it
was ever tried. Next month, when someone asks whether the interest ran on the
1st, the only answer is a line in a log file.

Both templates and nine tests, MIT, no dependencies past the standard
library:
https://github.com/dominicrume/cantor8_kya_rails/tree/main/step-0-refusal
```

---

## 4. PR #860. The champion ask.

**https://github.com/canton-foundation/canton-dev-fund/pull/860** → comment

**Why:** 35 days, zero reviews, on no board. `waynecollier-da` is an assigned
reviewer here and has been commenting actively on #627 this month, so they are
working through proposals and have not opened yours. The last line is designed
to be hard to read and ignore.

```
Five days of outside review, and what changed because of it.

Vacuumlabs (PR #627) hit this gap building delegated automation and said in
public there is "no standard pattern out there to commit them on-chain":
https://forum.canton.network/t/9084

They also found a real flaw: if a policy check passes and something later in
the transaction reverts, the record goes with it. That is fixed. The record is
now written in its own transaction before the work, so an unresolved record is
itself the evidence that something was tried and did not finish.

A second reader corrected a limitation I had documented three times. I had
concluded that without contract keys you cannot prevent a second journal being
opened, only detect it. Putting the auditor on the signatory line prevents it,
because a create needs every signatory. Built and tested the same day.

Also since filing: an open attempt now discloses nothing about what was
attempted, and an asset carrying a guard party cannot move at all unless a
record is written. 157 Daml scripts, and every authorisation check is
mutation-tested, meaning deleting it turns a named test red.

This is still Needs Champion with no review in 35 days. It is filed under
RFP 27. If it is in the wrong place, or missing something a reviewer needs
before they can look at it, I would genuinely rather be told that than keep
waiting quietly.
```

---

## 5. The thread you never posted.

**https://forum.canton.network/c/app-development** → New Topic
Category **App Development**, tags `daml` and `canton`.

**Title:**

```
If your app writes its own audit trail, you do not have an audit trail
```

**Body:**

```
I spent six weeks building proof that an AI agent had been stopped from
spending money. Then I noticed the obvious thing. My app was writing the
proof, and my app is what is being checked.

An auditor asking "can I trust this?" was really being told "yes, as long as
the app felt like being honest."

Two people on this forum fixed it, and neither of them was me.

Vacuumlabs pointed out that if a check passes and something later in the same
transaction fails, the whole thing rolls back and takes the record with it.
They were right. So the record is written first now, in a transaction of its
own, before any work happens. If the work then fails, the record survives. An
unfinished record is the evidence.

PREDGE replied four days ago with a single line. I had written in three
separate files that you cannot stop somebody opening a second journal,
because I thought Daml 3 had no contract keys. Put the auditor on the signatory line
rather than the observer line, they said, because a create needs every
signatory. That was the whole answer. One line, and I had given up on it.

Where it stands now: an asset carrying a guard party on its signatory line
cannot move unless a record is written. Not discouraged. Refused by the
ledger.

The limit, before anybody finds it for me. If one person can sign as both the
guard and the spender, they walk straight around all of it. There is a test
that does exactly that and shows it working. So this is a real control when
the guard belongs to somebody who is not the spender, and a polite suggestion
when it does not.

Free, MIT, and the integration is one word on your signatory line:
https://github.com/dominicrume/cantor8_kya_rails/tree/main/step-0-refusal

157 tests. None of it has run on the real network, because I have never been
given a credential, so weigh it as a design until that changes.

Is anybody else working on this? Two people here moved my design further in a
paragraph than I managed in a week, and I would far rather be corrected again
than be the only one looking at it.
```

---

## 6. Slack, `#sig-security`.

**Your first post in the right room.** You posted in
`#sig-attestor-pools-daos-multisig` by mistake on 18 October. Leave that one
alone and do not repeat it.

**Why the finding goes first:** this is a room full of people who audit code
for a living. A result about somebody else's code is the only thing that earns
attention here.

```
Hello, first post. I build refusal and audit evidence in Daml. Vorem, third
place at Build on Canton in August.

Something from this room's area first. I mutation-tested the authorisation
fences in two OpenZeppelin Canton packages, deleting each condition in turn
and re-running their own suite. 49 of 62 could be made vacuous with the whole
suite still green. Pinned commits, and their newer package,
scoped-authorization-grant-v1, is clean. Happy to share the sealed report.

The work it came out of: in Daml a failed check aborts the transaction, so a
control that fired leaves no evidence it fired. I make the refusal commit as a
contract, disclosed to an auditor party named in advance, without disclosing
the actions that were allowed. One module, MIT, no dependencies past the
standard library.

Two pointers would help.

My Dev Fund proposal is under RFP 27 and has had no review in 35 days, so it
has never entered the queue. PR #860.

And I have never had a DevNet credential, so all 157 tests run offline only.
If anyone knows who issues those, a name would do.

One real question while I am here. the LF 2.1 target has no contract keys, and the ones that returned in LF 2.3 are non-unique. For
uniqueness I ended up putting a second party on the signatory line, since a
create needs every signatory. Is that what everyone else does, or is there a
better idiom I have missed?
```

---

## 7. Amanda Martin. Thirty seconds, and worth it.

**Reply to her 17 October email.** She is COO of the Canton Foundation, she
granted the channels, and nobody thanks operations people.

```
Amanda, both channels came through, thank you. I am in
#sig-regulatory-compliance and #sig-security now.

For what it is worth, the work has moved a long way in the week since the
dinner. Two people on the forum found real flaws in my design and both are
now fixed and tested.

No ask attached to this, just closing the loop.

Rume
```

---

## Not sending anything to

**Philip.** He has the CV and the DevNet ask already, both on Telegram.
**Jatin.** The X DM is out and the ball is his.
**The hackathon group.** One ask is out there.
**Federico.** The ball has been his since 18 October.

A person asked once remembers the ask. A person asked three times remembers
that you wanted things.
