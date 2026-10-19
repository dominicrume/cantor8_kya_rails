# Status: what is proven, what is mocked, what is pending

*Last measured 2026-10-17. Regenerate the numbers with `python3 tools/dashboard.py`.*

This file exists because the team that won the Cantor8 hackathon had one and
this repository did not. Theirs separated proven from mocked from pending at a
glance, and a judge with four minutes could see the shape of the thing without
reading code. That is worth more than another test.

Read it top to bottom. The weakest claims are at the bottom on purpose.

---

## PROVEN — measured, reproducible, and checkable by a stranger

| What | Evidence | How to check it yourself |
|---|---|---|
| The spending rules are enforced in Daml, not in Python | 32 fences across 5 contracts | `python3 tests/fence_lint.py` |
| Every fence is load-bearing | 82 mutations, each requires a **named** test to go red | `python3 tests/mutation_suite.py` |
| The ledger behaves under attack | 125 Daml test scripts across two packages | `daml test --all` in `step-1-mandate/test` |
| A refusal commits as a contract and moves no money | `TryCharge` / `ChargeRefused` in `KyaMandate.daml` | `testRefusalIsOnLedgerAndNothingMoved` |
| The format is implemented three times and they agree | 20 conformance vectors, Python + JavaScript + Go | `python3 tests/conformance.py`, `node tests/conformance.js`, `cd impl/go && go run .` |
| A disclosure cannot have an entry removed | SPEC 6b | `python3 tests/disclosure_smoke.py` |
| A withheld refusal cannot be relabelled accepted | SPEC 6c outcome digest | `python3 tests/completeness_smoke.py` |
| An auditor can name a **withheld** refusal from the ledger alone | `AttemptJournal` count plus `missingRefusals`, 14 scripts | `daml test --files daml/JournalTest.daml` in `step-0-refusal/test` |
| The whole suite is green | 43/43 | `python3 tools/dashboard.py` |
| Two OpenZeppelin Canton packages have untested fences | **49 of 62**, at pinned commits `c96456f` and `fbc6392` | `docs/findings-openzeppelin.md`, sealed records in `docs/findings/` |
| OpenZeppelin's newer code is clean | `scoped-authorization-grant-v1`: 1 fence, 45 scripts, covered | same tool, SDK 3.5.8 via dpm |
| Three pull requests merged into a repository we do not own | Canton Developer Hub #156, #160, #168 | GitHub |

## MOCKED — labelled as such in code and in any demo

| What | Why | What would remove the label |
|---|---|---|
| `MockLedger` in `step-2-agent` | Lets the demo run offline with no credential | Nothing. It is the offline rail on purpose, and `tests/fence_parity.py` holds it to the Daml |
| The example disclosure `docs/examples/settlement-refusals.json` | Invented figures, stated in the file and in the forum post that shared it | Nothing. A demo file with real customer data would be worse |
| The float table in the README | A **recorded** measurement from the 2026-08-31 DevNet run, not a live read | `python3 tests/devnet_topup.py` with a credential |

## PENDING — the honest gaps, worst first

| Gap | Why it matters | Blocked on |
|---|---|---|
| **Never run on a real ledger.** `TryCharge` has never executed on DevNet | Every claim about on-ledger refusal is a design, not a fact. Both hackathon winners had real-ledger numbers and this does not | `C8_CLIENT_SECRET`. Asked 2026-08-31 in toolkit PR #10, and again on Telegram. The command is written and dry-run tested: `tools/prove_refusal_on_devnet.py` |
| **Nobody outside has produced a chain** | 0 stars, 0 forks, 0 outside implementations. 84 real downloads a month excluding mirrors | Distribution, not engineering |
| **The Dev Fund proposal has no champion** | `PR #860` reads `Needs Champion`. The repo's review process says a proposal does not enter review without one. Two rivals under the same RFP have champions and went to a vote on 2026-10-16 | A Tech and Ops Committee member |
| **The proposal is filed in the wrong folder** | It declares RFP 27 alignment but sits in `/proposals/`, which the repo's own README reserves for work that does *not* respond to an RFP. The rival that got a vote filed under `/rfps/` | A one-file move on the PR branch |
| **`outcomes` is not anchored anywhere** | SPEC 6c says plainly that the digest proves nothing until it is pinned to an origin the producer does not control | A ledger, which needs the credential |
| **No revenue.** Nothing has been invoiced or received | | |

## NOT CLAIMED

Three sentences that are **not** made anywhere in this repository, because they
would not survive being checked:

- *"Nobody else records what an agent was refused."* `khalydmaina/sentry` writes
  `RejectedTransfer` to Canton in Daml, with reasons and a ledger timestamp.
  See `docs/prior-art.md`.
- *"The EU AI Act requires this."* Annex III does not cover payments or
  treasury. The hook is FINRA 3110 and 4511 with SEC 17a-4, and even that
  creates no new rule.
- *"This proves the refusals are all of them."* The receipt chain proves
  non-equivocation and append-only ordering only. Write-time omission is
  unreachable by any commitment scheme, because the producer chooses what to
  commit to. SPEC 6c says so in its own heading.
  `Journal.daml` reaches it **on the ledger and only on the path it covers**: an
  auditor observing `AttemptJournal` reads the attempt count directly and can
  name a withheld position. It cannot prevent a second journal, because
  Daml-LF 2.1 has no contract keys, and it cannot see an attempt that bypassed
  it. `testAnUnjournalledAttemptIsStillInvisible` holds that line.
