# JOB: step-2-agent
IN:   a mandate (mock at home, DevNet at venue), a scripted customer conversation
DO:   agent plans its route, attempts charges: two legal, one over-cap,
      one to a stranger, one after revoke. Every attempt -> stamped, sealed receipt.
OUT:  receipts.js for the verifier, and a printed statement a human can read
DONE: python3 agent.py runs clean offline; chain verifies; refusals recorded as receipts.
NOT:  no spending rules in this code. It TRIES; the ledger (or its mirror) decides.
