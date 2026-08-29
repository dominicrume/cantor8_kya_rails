# CONTEXT.md (Layer 2, stage 2: what do I do?)

## Job

Run the shopping agent against the mandate and stamp one sealed receipt per attempt, accepted or refused, into a tamper-evident chain.

## Inputs

| File | Why |
| --- | --- |
| ../step-1-mandate/KyaMandate.daml | the rules this stage's MockLedger mirrors line for line (labelled MOCKED) |
| ../THE-RULES.md | no real funds, stdlib only |

## Process

agent.py plans five attempts (two within the rules, three attacks: over-cap, stranger payee, post-revoke). kya_chain.py canonicalises each receipt body with json.dumps sort_keys and compact separators, seals it with sha256 over canonical body plus previous seal, first seal chained to GENESIS. Amounts are stored as strings so Python and JS hash the same bytes.

## Output

Printed PLAN, STATEMENT and NUMBERS FOR JUDGES on stdout, and receipts.js written into ../step-3-verify/ for stage 3. THE-JOB.md holds the fuller narrative.
