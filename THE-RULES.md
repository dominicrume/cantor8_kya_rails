# KYA RAILS. THE RULES.
Build for Cantor8 "Build on Canton" Hackathon, challenge D1: a spend-limited wallet for an AI agent.
Built with the KYA Method: Promise it. Attack it. Inspect it. Prove it.

## The promise
An AI agent may spend money ONLY under a written mandate: a cap, an allow-list
of counterparties, an expiry. Every action the agent takes, including the ones
the ledger REFUSES, produces a sealed receipt a human can read and anyone can verify.

## Must always
- Enforce cap, allow-list and expiry IN DAML, in the choice body. Never only in Python.
- Record every attempt as a receipt: what, when, which rule allowed or refused it.
- Seal each receipt over the previous seal. Chain must verify end to end.
- Say what is mocked, out loud, in the demo. Overclaiming loses; honesty scores.

## Must never
- No production keys, no real funds, no Vorem wallets. Testnet and LocalNet only.
- No secrets in this repo. Ever.
- Never modify the organisers' toolkit; it is a dependency, not our code.
- No claim without a number behind it.

## The NOT list
- step-1-mandate does not read the chain library or the UI.
- step-2-agent does not contain business rules; rules live in Daml. The agent only tries.
- step-3-verify does not talk to the ledger; it reads receipts.js only.

## Stage map
step-1-mandate: the Daml contract, caps and allow-list enforced on ledger.
step-2-agent:   the agent, the charge attempts, the receipt chain writer.
step-3-verify:  the chat demo + verifier page + tamper test.

## The numbers we bring to judging
- charges under cap: accepted on ledger
- charge over cap: REFUSED on ledger (show the Daml line)
- charge to non-allow-listed party: REFUSED on ledger
- charge after revoke: REFUSED on ledger
- receipts in chain: N, chain verifies: true, tamper detected: true
