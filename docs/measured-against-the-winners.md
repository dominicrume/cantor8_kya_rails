# Measured against the people who beat us

*Measured 17 October 2026 from their repositories, not from memory or from what
they said on the day. Re-measure before quoting any of it.*

Cantor8 "Build on Canton", London, 29 August 2026. This project placed 3rd as
**Vorem**. 1st was **Team Mandate**, 2nd was **Lattice Scan**.

The assumption going in was that they built more. **They did not.**

## Activity

| | last commit | commits |
|---|---|---:|
| 1st place, `aswin-giridhar/canton8-hackathon-2026` | **29 August** | 34 |
| 2nd place, `workonthestreets/lattice-scan` | **29 August** | 21 |
| `khalydmaina/sentry` (HackCanton S3, same idea) | 29 September | 36 |
| **this repository** | **16 October** | **100+** |

Both winning teams stopped on hackathon day. They built a twelve-hour project
and presented it better. The gap was never depth.

## 1st place: what they had that we did not

| | them | us |
|---|---|---|
| Real Canton Coin moving through the mandate | **yes**, `token-standard/` | **no** |
| Deployed clickable demo | Vercel, "press Space to step through the attacks" | verifier on GitHub Pages, works offline |
| Pitch deck | Canva, linked at the top of the README | built later, **not in the repo** |
| `STATUS.md`, proven / mocked / pending | **yes** | **now yes** |
| `ASK-DAVIDE.md`, questions for the organiser | **yes** | **now `ASK-THE-ORGANISERS.md`** |
| DevNet bug report, shareable with organisers | yes | 4 toolkit PRs, 8 issues |
| Team | four, split workstreams | one |
| Daml tests | **2** | **111** |

## 2nd place: what they had that we did not

| | them | us |
|---|---|---|
| **Real DevNet numbers** | 109,778 contracts in 11.5s; self-check 0 missing, 0 phantom | **none** |
| **Independent cross-check** | `scripts/oracle.mjs`, their balances against the public Scan API, 11 of 12 matching to 10 decimal places | **nothing cross-checks us** |
| PDF summary committed in the repo | `docs/Lattice-Scan-Summary.pdf` | **no** |
| Script that regenerates the README's numbers | `scripts/measure.mjs` | `tools/evidence_pack.py` |
| Chaos test | `scripts/killtest.sh`, kill -9 and resume | `tests/mutation_guard_smoke.py` |
| Tests against the deployed instance | `test/live.test.mjs` | `tests/devnet_check.py`, never run |
| Offline tests needing no credentials | 76 | 43 suites, 156 Daml scripts, 82 mutations |
| Stated limits | "Honest boundary" section | `SHORTCUTS.md`, `STATUS.md` |

## The three real gaps

Not ten. Three.

1. **Real-ledger numbers.** Both winners had them. We have none, because we have
   never had a credential. This is the one that decided the hackathon.
2. **An independent cross-check.** Lattice Scan checked themselves against a
   public oracle and published the one party that disagreed, reconciled to the
   decimal. Nothing checks us but us.
3. **A PDF in the repo.** Both had their deck committed where a judge could
   find it without being shown.

Everything else we are ahead on, and in testing we are ahead by a wide margin.

## What `sentry` has that matters more than any of it

`khalydmaina/sentry` implements the same core idea in public Daml:
`RejectedTransfer` with `reasons`, `RejectionPath` and `rejectedAt`, committing
instead of aborting. Created 19 September, ten days after our forum post.

**So "nobody else records what an agent was refused" is dead.** It is in
`docs/prior-art.md` and in the NOT CLAIMED section of `STATUS.md`.

What sentry does **not** have, and this is the whole remaining claim:

```daml
observer agent          -- sentry: the refused agent sees its own record
observer optional [] (\a -> [a]) auditor   -- ours: a third party, named in advance
```

Theirs is an application's own wallet log. Ours discloses to a party chosen
before any attempt happened, and withholds the actions that were allowed. RFP 27
asks, in its own words, for *"how privacy, access controls, and selective
disclosure will be handled"*.

That is a narrower claim than we were making. It is the one that survives.

## How to use this file

Re-measure before every pitch, proposal or conversation. A table that is not
re-run is a memory, and the rule in `CLAUDE.md` is that a number nobody has
plotted is a rumour.
