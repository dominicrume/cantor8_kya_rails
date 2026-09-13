# Conversations with people who might use this

**Count: 2.**

That number is the point of this file. Everything else in this repository is a
thing we decided to build. This is the only page that records what somebody
outside it actually said. It read zero for the first thirteen days.

It is kept in the repo rather than a notebook because the repo is the thing we
look at every day, and a zero in a private note is a zero nobody has to explain.

It also read **1** for two days while it was **2**, because nobody went and
looked at the thread. Both replies below arrived on 11 September and both sat
unanswered while the work they were about was being done. A file that records
conversations is worth nothing if the conversations are not read.

## The rule

One row per real conversation with a person who runs, builds, or is accountable
for an agent that spends money. Dated, named, and **what they said in their own
words** — not what we concluded from it. A summary is where the useful part
goes to die.

A demo does not count. A star does not count. A download does not count. Someone
telling you what they do today about agent spend counts.

| date | who | where | what they said, in their words | what it changed |
|---|---|---|---|---|
| 2026-09-11 | Mr_Tuddles, Pearl Digital (P3 contracts, agentic registry) | forum.canton.network/t/9059, reply to post #9 | "Yes, we support deterministic settlement by agents. what do you have in mind?" | First reply to the one-sentence question, four hours after it was asked. |
| 2026-09-11 | Mr_Tuddles, same thread, later | forum.canton.network/t/9059/12 | "Might be easier for you to just tell us what you are building. We are a stablecoin issuer; our stables are deployed on testnets with agentic payments." Plus: investigating porting to Canton natively, contracts based on their GitLab repo. | **This is the row that counts under the rule at the top of this file**: a fact about what he does, not an opinion about our idea. Stables live on testnets with agentic payments TODAY. He also declined our question twice and asked us to say plainly what we are building, which is a fair request we had not met: both our messages led with the mechanism. Unanswered for two days while we rebuilt the thing he was asking about. |
| 2026-09-11 | Federico_Rodriguez | forum.canton.network/t/9114/2, on our own topic | "you are still trusting the application to create the receipts and include every attempt. The hash chain makes existing receipts tamper-evident, but it doesn't prove that a receipt wasn't omitted... An alternative worth considering would be to make the refusal itself a valid Canton transaction. For example, wrap the operation in a choice that checks the policy and either performs the action or creates a `RejectedAttempt` audit record. The transaction commits in both cases, but the underlying action only happens when allowed." | A stranger read the design, found the hole, and specified the fix. On **11 September**. `TryCharge` and `ChargeRefused` were built on **12 September** and are that design, down to the shape: one choice, both paths commit, only the allowed one moves money. He also named the limit that survives it, correctly, and it is the one written into KyaMandate.daml and SPEC 6a. He has not told us what he does, so by the rule above this is not a customer conversation; it is something rarer, which is somebody outside the project being right about it before we were. Unanswered for two days. |

## Who to ask first

Already interested in this exact area, and reachable — from the OpenZeppelin
feedback thread (`forum.canton.network/t/9059`):

| who | why them |
|---|---|
| **Pepe_Blasco** | OpenZeppelin, opened the thread, replies substantively. Has our findings. |
| **woof-software** | Went deep on lending and open design questions; got a detailed reply from Pepe. |
| **Mr_Tuddles** | Shipping stablecoins and an *agentic registry* on Canton — the closest thing to a live user in the thread. |
| **zhe_bd** | Asked about licensing — reads the fine print, which is the person who cares whether a record holds. |
| **Erlan** | Interested in reusable building blocks for the ecosystem. |

And outside crypto entirely, because the problem is not chain-specific: anyone
whose agent can spend, refund, message customers, or call a paid API.

## The question to ask

Not "would you use this". People are polite, and a yes costs them nothing.

> **Has anyone ever asked you to prove your system *didn't* do something?**

Then stop talking.

If they say yes, ask what they showed. If they say no, ask who would ask first.

The question above went through a worse draft, and the reason it was worse is
worth keeping: it explained our idea back to them before asking anything. Every
clause of setup is a clause the other person has to agree with before they can
answer, and a question nobody can answer in one breath is a question that gets
a polite reply instead of a true one.

Rules for the next one:

- One sentence. One question mark.
- No words they would have to be inside this project to understand.
- Nothing about what we built. They can ask.
- Their answer should be a fact about their week, not an opinion about our idea.

Three people describing our problem in their own words means there is a
business here. Zero means we have been building for ourselves, which is the
finding — and a cheaper one to get now than in a quarter.
