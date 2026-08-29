# Shortcut log. A written shortcut is a debt paid on our schedule.
| date | shortcut | why | repay by |
|---|---|---|---|
| 2026-08-29 | MockLedger mirrors Daml assertions in Python for offline demo | venue network unknown | venue: swap to c8lab DevNet calls |
| 2026-08-29 | Charge records value, does not move Canton Coin yet | starter behaviour | venue: wire c8lab.py transfer into Charge flow |
| 2026-08-29 | Cut LocalNet/Docker entirely | redundant: MockLedger covers offline, venue DevNet covers real ledger; risk budget goes to judged surfaces | only if offline real-ledger ever needed, post-event |

2026-08-29 | Demo pacing set to 5s a message (MSG_MS), Slow/Fast toggle | two-minute slot: a judge reads a chat bubble in about five seconds, and a demo that outruns the eye proves nothing. Story runs ~67s, leaving ~53s to talk | halve MSG_MS if the slot shrinks

2026-08-29 | REPAID: MockLedger is now the offline default, not the only rail. `agent.py --devnet` runs the real KyaMandate on Canton DevNet and DevNet itself returns every refusal. Both rails share one charge() interface, so no spending rule moved into Python.
2026-08-29 | STILL OPEN: Charge records value, does not move Canton Coin. The 5 CC sits in kya-agent-1 untouched. Labelled on every receipt as "Amulet (recorded, not transferred)" rather than implied. Repay by wiring c8lab.transfer into the Charge flow; needs act-as on the receiver to accept the offer.
