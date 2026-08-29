# CONTEXT.md (Layer 2, stage 1: what do I do?)

## Job

Define the spending mandate as a Daml contract so the cap and the allow-list are enforced by the ledger, not by application code. A cap checked in Python is a suggestion; a cap in a choice body is a rule.

## Inputs

| File | Why |
| --- | --- |
| ../THE-RULES.md | the promises this contract must keep |
| ~/hackathon-toolkit/daml-starter/Mandate.daml | the organisers' starter, read only, never edited |

## Process

Extend the starter pattern: KyaMandateProposal (propose and accept, so both parties sign) and KyaMandate with Charge, Adjust, Revoke. Charge must assert the cap and the allow-list inside the choice body.

## Output

KyaMandate.daml, compiled at the venue with daml build. THE-JOB.md holds the fuller narrative.
