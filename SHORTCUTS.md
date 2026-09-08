# Shortcut log. A written shortcut is a debt paid on our schedule.
| date | shortcut | why | repay by |
|---|---|---|---|
| 2026-08-29 | MockLedger mirrors Daml assertions in Python for offline demo | venue network unknown | venue: swap to c8lab DevNet calls |
| 2026-08-29 | Charge records value, does not move Canton Coin yet | starter behaviour | venue: wire c8lab.py transfer into Charge flow |
| 2026-08-29 | Cut LocalNet/Docker entirely | redundant: MockLedger covers offline, venue DevNet covers real ledger; risk budget goes to judged surfaces | only if offline real-ledger ever needed, post-event |

2026-08-29 | Demo pacing set to 5s a message (MSG_MS), Slow/Fast toggle | two-minute slot: a judge reads a chat bubble in about five seconds, and a demo that outruns the eye proves nothing. Story runs ~67s, leaving ~53s to talk | halve MSG_MS if the slot shrinks

2026-08-29 | REPAID: MockLedger is now the offline default, not the only rail. `agent.py --devnet` runs the real KyaMandate on Canton DevNet and DevNet itself returns every refusal. Both rails share one charge() interface, so no spending rule moved into Python.
2026-08-31 | REPAID: Charge now settles. `--devnet --move-coin` authorises on the mandate and then transfers real Amulet; balances verified 5.0 -> agent 1.4, customer 2.1, partner 1.5, total conserved, unverified account 0.0. Original entry below. | 2026-08-29 | Charge records value, does not move Canton Coin. The 5 CC sits in kya-agent-1 untouched. Labelled on every receipt as "Amulet (recorded, not transferred)" rather than implied. Repay by wiring c8lab.transfer into the Charge flow; needs act-as on the receiver to accept the offer.

2026-08-31 | REPAID: per-period limits, mutation coverage on every fence, threat model, upgrade path, and the four vectors M1 promised. The Daml package was also split so test scaffolding no longer ships in the deployed DAR — a test-only record had made a cosmetic rename into an on-ledger breaking change.

2026-09-08 | The float table in the README is a RECORDED measurement, not a live read. `docs/devnet-balances.json` holds the balances from the 2026-08-31 `--move-coin` run, and `tests/balance_lint.py` re-adds them on every build — so the arithmetic is checked, but nothing re-reads the ledger to confirm those are still the holdings. | `C8_CLIENT_SECRET` is not in this shell, so DevNet cannot be queried. Recording the figures and checking the sums is honest; claiming they are current would not be. | re-measure with `python3 tests/devnet_topup.py` when the secret is back, and have balance_lint compare the file against the live ACS rather than only against itself. Same visit as redeploying 1.1.1.

2026-09-08 | REPAID: `tests/devnet_check.py` gated `--move-coin` on `NEEDED = 3.5`, left over from payouts of 2.0 and 1.5 that have been 0.2 and 0.1 for weeks. It told an operator holding 1.4 CC that a 0.3 CC run was unaffordable and recommended the weaker demo — in the exact balance state this project is in. Never written down as a shortcut, which is why it survived: it was a number describing another file, kept in this one. It now reads agent.py's payout list, and `balance_lint` fails if a literal creeps back.

2026-09-08 | Two of the three OpenZeppelin findings records are not built yet. `docs/findings/` holds `access-control-v1` (7 fences, sealed and verifiable); `canton-token-template` (32) and `canton-stablecoin` (30) are a full build-and-test per fence and were still running. The findings doc and the README name only the record that exists. | an hour of machine time, not a decision | run `tools/assurance.py` against both and commit the records beside the first.
