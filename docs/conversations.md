# Conversations with people who might use this

**Count: 0.**

That number is the point of this file. Everything else in this repository is a
thing we decided to build. This is the only page that records what somebody
outside it actually said, and while it reads zero, every design decision here
rests on a guess.

It is kept in the repo rather than a notebook because the repo is the thing we
look at every day, and a zero in a private note is a zero nobody has to explain.

## The rule

One row per real conversation with a person who runs, builds, or is accountable
for an agent that spends money. Dated, named, and **what they said in their own
words** — not what we concluded from it. A summary is where the useful part
goes to die.

A demo does not count. A star does not count. A download does not count. Someone
telling you what they do today about agent spend counts.

| date | who | where | what they said, in their words | what it changed |
|---|---|---|---|---|
| | | | | |

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

> **What do you do today if you need to show someone that your agent *didn't*
> do something it wasn't allowed to do?**

Then stop talking. If the answer is "nothing" or "I'd grep the logs", ask what
happens when the person asking is a customer, an auditor, or a regulator.

Three people describing our problem in their own words means there is a
business here. Zero means we have been building for ourselves, which is the
finding — and a cheaper one to get now than in a quarter.
