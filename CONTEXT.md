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

## Order of execution

Stage 1 defines the rules. Stage 2 obeys them and produces receipts.js. Stage 3 consumes receipts.js and proves the chain to a human. Output of one stage is the input of the next; the filesystem is the pipeline.

## Shared constraints (apply in every stage)

Python is stdlib only. Canonicalisation must stay byte-identical in Python and JS. Amounts are strings. Anything mocked is labelled MOCKED. Never modify the organisers' toolkit at ~/hackathon-toolkit. The AI suggests, the human decides.
