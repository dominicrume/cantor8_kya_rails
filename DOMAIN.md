# DOMAIN.md. What this company knows, and where it is kept.

Know Your AgenticAI builds the evidence layer for automated actors that spend
money: an enforceable limit on the ledger, and a record of every action including
the ones the ledger **refused**. Owner: Rume Dominic (O'Rume Dominic Uririe).

This file is Layer 0. `CONTEXT.md` routes by stage; this routes by **what kind of
judgement you are about to make**. The knowledge itself lives in
`.claude/skills/`, where Claude and any subagent can load it.

| About to | Load | Core assertion |
|---|---|---|
| Write or review enforcement code, a test, a spec | `kya-method` | Promise it. Attack it. Inspect it. Prove it. A fence with no named test is decoration |
| Write a number, a status row, a README line, a recommendation | `claim-discipline` | A number nobody has plotted is a rumour. Three states, never two |
| Post, reply, email, open a PR, hand Rume text to send | `before-it-leaves` | Verify before it leaves, not after. Nothing posted that is not built |
| Run anything authenticated, or release | `secret-hygiene` | A secret in means tainted out |
| Reason about Daml, refusals, privacy, contention, upgrades | `canton-evidence-layer` | The ledger names parties, not operators. A refusal is a contract, not an exception |
| Ask anyone for anything, or plan around a yes | `ecosystem-mechanics` | Find the mechanism before arguing the merits |
| Fix how the work itself is done, after a mistake | `self-improving-loop` | A rule written four times and broken twice is a wish. Prose, then tool, then gate |

## The one rule above the others

> Would I still do this if they never replied, never funded it, and never knew my
> name?

If no, it is leverage wearing the costume of a contribution, and it fails even
when it works. `THE-RULES.md` carries the full text and the failure it was written
after.

## What is load-bearing and what is not

The **durable** assets are the doctrine in these skills, the specification, the
conformance vectors, the Daml, and the sealed records. The **ephemeral** assets
are the dashboards, the HTML pages, the drafts and the scripts that render them:
regenerate them from the doctrine rather than maintaining them.

Numbers are deliberately not frozen in this file. Each skill names the command
that measures what it claims, because the commit that changes a number does not
touch the file that quotes it. `tests/balance_lint.py` exists for exactly that
failure and catches only the patterns it has regexes for.

## Project boundaries, which are real

- The **OTC desk** moved out on 12 September 2026 to its own repository. No
  payment screen, webhook or wallet address comes back here. What stayed is the
  evidence layer. The desk's Daml modules stayed too, and must, because Canton's
  upgrade check refuses a version that drops a data type its predecessor had.
- The **AI code auditor** (`ai-code-quality-auditor`) is a separate project and
  the owner's MSc dissertation tool. Work on one is never a reason to release the
  other, and a version number belonging to one is never bumped for the other.
- The organisers' toolkit at `~/hackathon-toolkit` is read and called, never
  edited.

## The honest state

`STATUS.md` separates proven from mocked from pending, worst first, and is kept
current rather than written once. Two things on it bind every plan: **`TryCharge`
has never executed on a real ledger**, so every claim about on-ledger refusal is a
design and not a fact; and **nothing has been invoiced or received**.
