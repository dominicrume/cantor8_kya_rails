---
name: self-improving-loop
description: How this company turns its own failures into machinery instead of reminders. Use when a mistake has just happened, when a rule has been broken more than once, when deciding whether to write a note or build a gate, and when asked to improve how the work itself is done. Also the map of which sensor, gate and tool covers what.
---

# The self-improving loop

The operating claim: **a rule written four times and broken twice is a wish.** The
unit of improvement here is not a reminder, it is a gate that refuses.

## The five layers, and what actually fills them

| Layer | What it is here | State |
|---|---|---|
| Sensors | forum replies, reviewer corrections, `gh` API, `tools/vote_pipeline.py`, `tools/champions.py`, `tools/ecosystem_scan.py`, `docs/evidence/downloads.json` | exists, **pull only, nothing is scheduled** |
| Policy | `CLAUDE.md`, `THE-RULES.md`, `CONTEXT.md` routing table | strong, and long enough to be walked past |
| Tools | 22 files in `tools/`, stdlib only, each with a literal argv | strong |
| Quality gates | `tools/pre-commit`, `tests/fence_lint.py`, `tests/balance_lint.py`, `tests/no_real_addresses.py`, `tools/mutation_suite.py`, `tools/before_posting.py`, `tools/before_contributing.py` | strong where a gate exists, absent where only prose does |
| Learning | `SHORTCUTS.md` (append-only), `STATUS.md` corrections, every rule carrying its date and its failure | **entirely manual. This is the gap.** |

Be honest about the shape of that table. Four layers are machinery and the fifth
is a person remembering to write it down. The loop closes because Rume closes it,
which means it closes at human speed and stops when he is busy.

## The rule of escalation

Prose, then tool, then gate. Each step is taken only after the previous one has
failed **in the open**, with the date recorded.

1. **Prose** is for a thing that has gone wrong once. Write it where the decision
   gets made, not in a separate document, and write the failure beside the rule so
   a reader can tell whether it still applies.
2. **A tool** is for a thing that needs a judgement made in a fixed order.
   `before_contributing.py` asks four questions and writes the answers down so they
   can be read back cold. It cannot know the answers. It can refuse to let you
   skip them.
3. **A gate** is for a thing that has gone wrong twice. `tools/pre-commit` runs
   `balance_lint` before `fence_lint` because a killed mutation run left a mutated
   balances file committed and pushed, and the class had already cost two files in
   one night. The fix is the hook, not more care.

The tell that you are at the wrong step: you are about to write "be careful about
X" for the second time.

## Every gate carries a positive control

A check that cannot fail is indistinguishable from one that passes.

- `tools/vote_pipeline.py` reproduces a known vote (#942: 4 in favour, 1 absent, 4
  binding rows) and prints **no numbers at all** if it cannot.
- `tests/no_real_addresses.py` proves the validators and the tree walk can both
  say yes before it is trusted to say no.
- A scan of built release artefacts for secrets must prove it reads them.
- `tools/mutation_suite.py` is itself the positive control for the whole Daml
  suite: it breaks each fence on purpose and requires a named test to go red.

**A control easier than the case it stands for is not a control.**
`before_posting.py` first missed the failure it was built for, because its control
said "Simon Meier at Digital Asset" (two name words) while the sentence that went
wrong said "Leonid at Digital Asset". It names "Leonid" now.

## Writing the entry after a failure

Six parts, in this order, and the order is the point:

1. **The date.** Without it nobody can tell whether the rule still applies.
2. **What was done**, concretely, naming the command or the file.
3. **What it cost**, in the units it was actually spent in: a closed pull request
   under your own name, a leaked token, two weeks of a live contract address.
4. **Why the existing rule did not stop it.** This is the valuable part and the
   one most often skipped. The 23 October leak was not carelessness; the forbidden
   list was the wrong abstraction. The 31 October comment was not carelessness; the
   order was wrong, and the wrong order produces a correct result most of the time,
   which is precisely why it survives.
5. **The mechanism now in place**, by filename.
6. **What it still does not cover.** `fence_parity.py` holds four copies of the
   spending rules to each other by message and by order, and explicitly does not
   compare the predicates: two copies can say the same words and disagree about
   the boundary.

`SHORTCUTS.md` is append-only, and a repaid shortcut is marked REPAID with the
original left visible. A debt written down is paid on our schedule.

## Where the loop is open, named

Say these out loud rather than letting them read as finished:

- **The learning layer has no trigger.** Nothing notices that a rule was broken
  twice; a person does.
- **The sensors are pull only.** No scheduled sweep tells anyone that a reviewer
  replied, a vote was opened, or a sitting happened. Three sittings were
  reconstructed after the fact, and #866's window closed unnoticed.
- **Prose claims have no gate.** `balance_lint` catches only the patterns it has
  regexes for. On 9 November 2026 `SPEC.md:390` and `tools/dashboard.py:37` still
  said 16 conformance vectors against 20 in `tests/vectors.json`, because neither
  matches the one regex that guards the README's markdown-link form.
- **The destination check is partial.** `post_queue.py` reads back a Discourse
  topic and a GitHub pull request. Groups.io answering 402 and a new topic with no
  id yet are CANNOT CHECK, which is correct and is not coverage.

## Feedback contract

Report: which layer the failure was in; whether you wrote prose, a tool or a gate,
and why that step rather than the previous one; the positive control and the proof
it can fail; and the sentence saying what the new mechanism does not cover. If you
only wrote prose for something that has now happened twice, say so explicitly
rather than letting it pass as a fix.
