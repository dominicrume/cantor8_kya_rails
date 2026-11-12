# CONTEXT.md (Layer 1: where do I go?)

This workspace follows the Interpretable Context Methodology (ICM), arXiv 2603.16021: folder structure as agent architecture. One stage, one job. Plain text as the interface. Every output is an edit surface.

## Routing table

| If the task is about | Go to | The contract there |
| --- | --- | --- |
| Spending rules on the ledger (cap, allow-list, revoke) | step-1-mandate/ | CONTEXT.md then KyaMandate.daml |
| The agent that tries to spend, and the sealed receipt chain | step-2-agent/ | CONTEXT.md then agent.py and kya_chain.py |
| The offline verifier the judges touch | step-3-verify/ | CONTEXT.md then verifier.html |
| What we promise and never do | THE-RULES.md | read before any change |
| Why the system is shaped this way | ARCHITECTURE.md | reference only |
| Debts we consciously took | SHORTCUTS.md | append, never delete |
| Honest self-score against the challenge | scoreboard/THIRTEEN-CHECKS.md | update after any change |
| Any judgement about doctrine, claims, outreach, secrets, Canton facts or the ecosystem | DOMAIN.md | the skill it routes you to in `.claude/skills/` |

## Order of execution

Stage 1 defines the rules. Stage 2 obeys them and produces receipts.js. Stage 3 consumes receipts.js and proves the chain to a human. Output of one stage is the input of the next; the filesystem is the pipeline.

## Where a real Canton ledger comes from, and why this was blocked for 74 days

Added 13 November 2026, after the single biggest hole in this project turned
out to have no blocker at all.

`STATUS.md` said `TryCharge` has never executed on a real ledger, and named
the blocker as `C8_CLIENT_SECRET`, asked of Cantor8 on 31 August 2026 and
never answered. That named another organisation as the reason for 74 days.

The organisers' own toolkit, `~/hackathon-toolkit/README.md` line 10, says:

> "LocalNet, a whole Canton network in Docker on your laptop. The default."

It mints its own Canton Coin. It signs its own tokens with HS256. It works
offline. It needs permission from nobody. The real cost, per
`~/hackathon-toolkit/SETUP.md`, is Docker Desktop with 16 GB of memory and
about 6 GB of images.

So the reason was never a missing credential. The reason was that nobody had
started Docker.

Measured 13 November 2026: the Docker CLI is installed, the daemon is not
running, and nothing answers on LocalNet's port 2975. Doable, and not done.
This repository contains no compose file of its own; the LocalNet compose
files ship in the Splice release bundle, not here and not in the toolkit.

The re-reading happened because Jatin Pandya, Developer Relations Manager at
the Canton Foundation, linked the LocalNet guide on forum topic 9475 on
11 November 2026.

**The honesty limit, which travels with every result LocalNet produces.**
LocalNet proves that Canton's own engine enforces the fences, because it is
real Canton running real Daml. It does NOT prove behaviour on a shared network
with other participants, other validators or other people's traffic. It is
your laptop. It is not DevNet, it is not TestNet, and it is emphatically not
MainNet. A LocalNet result is written up as "Canton refused this" and never as
"this ran on the Canton network".

## Shared constraints (apply in every stage)

Python is stdlib only. Canonicalisation must stay byte-identical in Python and JS. Amounts are strings. Anything mocked is labelled MOCKED. Never modify the organisers' toolkit at ~/hackathon-toolkit. The AI suggests, the human decides.
