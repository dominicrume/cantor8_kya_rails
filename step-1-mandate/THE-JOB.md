# JOB: step-1-mandate
IN:   the organisers' Mandate.daml starter (copy, keep their header credit)
DO:   extend it: counterparty allow-list; keep cap, expiry, revoke, propose/accept
OUT:  KyaMandate.daml that builds, tests passing: under-cap OK, over-cap FAILS,
      wrong counterparty FAILS, after-revoke FAILS
DONE: `daml test` green, and I can point at the exact line that refuses each attack.
NOT:  no receipt logic here. The ledger enforces; the chain observes.
