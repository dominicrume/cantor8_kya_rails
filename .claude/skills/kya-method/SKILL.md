---
name: kya-method
description: The engineering doctrine of Know Your AgenticAI. Use when writing, reviewing or extending any enforcement code, test or specification in this repository, or when asked to make a claim about behaviour hold up. Turns a promise into a fence, a fence into a mutation, and a mutation into a named test. Promise it. Attack it. Inspect it. Prove it.
---

# The Know Your AgenticAI Method

Four moves, in order. Skipping one is the defect.

**Promise it.** Write the sentence a stranger would check. One claim, no hedging.
**Attack it.** Try to make the sentence false before anybody else does.
**Inspect it.** Find the one line that stops the attack. That line is a fence.
**Prove it.** Break the fence on purpose. If no test goes red, the fence is decoration.

## What a fence is

A fence is the line of code that refuses. In this repository fences live in Daml,
in the choice body, never in Python. `tests/fence_lint.py` counts them;
`tests/mutation.py` holds the manifest; `tools/mutation_suite.py` mutates each one
and requires a **named** test to fail. A fence with no named test is an unproven
claim wearing the costume of a feature.

Run, do not recall:

    python3 tests/fence_lint.py
    python3 tools/mutation_suite.py
    python3 tools/dashboard.py

## The three rules that produce the shape

1. **Enforcement goes where the authority is.** Spending rules are in
   `step-1-mandate/KyaMandate.daml`. Python only tries. An application that
   contains the rule can be edited by whoever runs the application.
2. **A refusal is a contract, not an exception.** An exception aborts during
   interpretation, reaches no other node, and leaves the auditor with a numerator
   and no denominator. A created contract is an ordinary event every adapter
   already carries. This is the whole thesis of `step-0-refusal`.
3. **The authority that must not be bypassed goes on the signatory line.**
   Observer is a view. Signatory is a requirement. The auditor is a signatory of
   the journal, which is why a second journal cannot be opened behind their back
   without contract keys.

## Attacking well

Good attacks in this codebase were found by asking four questions, in this order:

- Can the same party hold both roles? (`testSubmittingAsTheGuardianDefeatsIt`)
- Can the work happen without touching the thing that records it?
  (`testAnUnjournalledAttemptIsStillInvisible`)
- Can the record be destroyed, or a hole left unnumbered?
  (`testArchivingAnAttemptLeavesANumberedHole`)
- Does the minimal test fixture do work the design is being credited with?
  Georgi Radev found exactly this on 27 October 2026: the test wallet carried no
  choices, so an owner-controlled choice bypassing the journal had never been
  tried. The fix was `testAnOwnerControlledChoiceStillBypassesTheJournal`, and
  the test is itself checked by deleting the choice.

The fourth question is the expensive one. A suite can be green because the
fixture is too small to pose the question.

## The limit goes beside the claim

Every property in this repository ships with the sentence saying where it stops,
and that sentence has a test too. `testSubmittingAsTheGuardianDefeatsIt` proves
the bypass exists. `docs/what-this-proves.md` is more persuasive than any feature
list because it is the part nobody fakes.

If you cannot write the limit, you have not finished inspecting.

## Feedback contract

After using this skill, report back, in this order:

1. The sentence you promised, verbatim.
2. The attack you ran and what it did.
3. The file and line of the fence.
4. The command that goes red when the fence is broken, and its named test.
5. The limit: what this does **not** prove, in one sentence.
6. Anything you could not check, and what would be needed to check it.

Report a number only with the command that produced it on this machine, this run.
