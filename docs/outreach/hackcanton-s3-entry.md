# HackCanton Season 3, solo entry

**Register:** https://appsfactory.cc/hackathons
**Grand Final:** 14 October 2026. **Prize pool: up to $50,000.**
**Solo entries allowed.** Season 2 paid $10K cash + $25.2K NaaS credits + 100K CC.

**Check the submission deadline the moment you land on the page.** That is the
one fact I could not read, because the registration page renders in JavaScript.

---

## Project name

**Know Your AgenticAI**

Subtitle if a field asks for one:

> The evidence layer that sits under a Canton application.

---

## One line

```
On Canton a blocked action leaves nothing behind. I built the record that
survives it, and a regulator can check it without trusting the operator.
```

## Two sentences, if the form wants a short description

```
In Daml a failed assertMsg aborts the transaction, so an action a rule
stopped leaves no trace on the ledger at all. What settled is corroborated
by the ledger; what was refused exists only in the operator's own logs,
written by the operator, about the operator.

This makes the refusal a transaction that commits: same rules, but a
rejection record instead of an abort, no money moved, and an auditor named
in advance who reads it while nobody else can.
```

## The longer description

```
THE PROBLEM

A supervisor asks a firm to show what its system blocked last quarter. The
firm can show every action that went through. It cannot show one that was
stopped.

That gap is structural, not sloppy. In Daml a failed assertMsg aborts the
whole transaction, so a refused action leaves nothing on the ledger.

EU AI Act Article 12 and DORA both ask a firm to evidence that a control
OPERATED. A control that operates produces refusals. If refusals leave
nothing behind, the control cannot be evidenced.

WHAT I BUILT

1. canton-refusal-record, a Daml package with no dependencies beyond
   daml-prim and daml-stdlib. The choice commits either way: if the rule
   passes it acts, if it fails it writes a record and moves no money. The
   contract id and the ledger time are not the operator's to write.

2. A named auditor observes those records and nobody else does. This is the
   part a transparent chain cannot do: on a ledger, not public, and the
   party entitled to read it was named before any of the attempts happened.

3. A disclosure format that hands over the refusals WITHOUT the accepted
   transactions, where nothing can be removed from what the reader is shown.

4. A browser verifier. Drop the file on a page. No wallet, no install, no
   network.

WHAT IS ALREADY DONE, BEFORE THIS HACKATHON

111 Daml test scripts across two packages. 42 test suites. 82 mutations,
each of which breaks something real and requires a NAMED test to go red.
32 spending fences, each proven load-bearing by deleting it. A written
specification with 20 conformance vectors, implemented three times
independently in Python, JavaScript and Go, all agreeing. A package live on
PyPI. Three pull requests merged into the official Canton Developer Hub.
Eight fixes contributed to the Cantor8 hackathon toolkit. A Development
Fund proposal open under RFP 27.

WHAT IT DOES NOT DO

An attempt that was never submitted leaves nothing behind. This makes a
refusal that HAPPENED impossible to invent, delete, backdate or reorder. It
does not make one that never reached the ledger appear, and no ledger
artefact can.

CREDIT

The on-ledger pattern was named RejectedAttempt by Federico_Rodriguez, a
Canton Community Tech Partner, on forum.canton.network/t/9114. He read the
design, found that application-written receipts cannot prove completeness,
and specified the fix. It shipped the next day and he is credited in the
source.
```

## Links to give them

```
Code:      https://github.com/dominicrume/cantor8_kya_rails
Verifier:  https://dominicrume.github.io/cantor8_kya_rails/
Try it:    https://dominicrume.github.io/cantor8_kya_rails/examples/settlement-refusals.json
Package:   https://pypi.org/project/knowyouragenticai-receipts/
Proposal:  https://github.com/canton-foundation/canton-dev-fund/pull/860
Spec:      https://github.com/dominicrume/cantor8_kya_rails/blob/main/SPEC.md
```

## If there is a demo slot

Sixty seconds, and do not explain the architecture.

1. "A regulator asks a bank what it blocked. The bank can't show them." (10s)
2. Open the verifier. Drop the file. (15s)
3. "Three refusals in full. Three payments it is not being shown, still
   sealed so nothing can be removed." (15s)
4. Delete a refusal in a text editor. Drop it again. It fails. (15s)
5. "Nothing installed. No wallet. No network." (5s)

The file failing after an edit is the moment. Do not talk over it.

## The one thing to say that nobody else will

Most entrants will show something built in five weeks. Say plainly that this
was not: it has been built and rebuilt since 29 August, a Community Tech
Partner found a hole in it, and it was rebuilt again. Then say what it still
cannot do.

Being the only person in the room who names their own limits is the whole
differentiator. It is also true.
