# Thirteen Checks scoreboard, run before demo
1 Written rules: PASS (THE-RULES.md, read by agent at boot)
2 Plan before code: PASS (job cards committed before code)
3 Small pieces: PASS (three stages)
4 Route not reflex: PASS (agent prints its plan before acting)
5 Done defined: PASS (each job card has DONE)
6 Only what it needs: PASS (NOT list held)
7 Contain the fire: PASS (one charge() interface; MockLedger and DevNetLedger are interchangeable, proven by running both)
8 Show your working: PASS (the receipts ARE the product, and each one names the ledger that made it, inside the seal)
9 Fences that hold: PASS in `daml test`, and as of 13 November 2026 one of them
  is also refused by a real Canton ledger (`tools/prove_refusal_on_sandbox.py`,
  a local sandbox, not DevNet).
  CORRECTED 13 November 2026. This line read "all four refused by real Canton
  DevNet". It was signed 29 August and went unrevised through 267 commits, while
  SHORTCUTS.md recorded on 12 September that the real rail "has never been run
  against DevNet". This whole document is 76 days stale and should be re-signed
  or retired rather than trusted.
10 Check your own work: PASS (verify() recomputes every seal)
11 Say where you learned it: PASS (each receipt cites its mandate rule)
12 Ship through a gate: GROWING (demo checklist manual, gate script post-event)
13 Learn from last time: MISSING, signed: acceptable for a one-day build. R.D. 2026-08-29
