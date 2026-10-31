# Status: what is proven, what is mocked, what is pending

*Last measured 2026-10-31. Regenerate the numbers with `python3 tools/dashboard.py`,
and the champion figures with `python3 tools/champions.py`.*

This file exists because the team that won the Cantor8 hackathon had one and
this repository did not. Theirs separated proven from mocked from pending at a
glance, and a judge with four minutes could see the shape of the thing without
reading code. That is worth more than another test.

Read it top to bottom. The weakest claims are at the bottom on purpose.

---

## PROVEN — measured, reproducible, and checkable by a stranger

**2026-10-31.** The draft survived its first two reviews, and both of them
cost it a claim. Georgi Radev (Community Tech Partner) found on 27 October that
a guardian on the signatory line does not gate a choice the owner controls, so
the Specification gained a second conformance requirement and
`testAnOwnerControlledChoiceStillBypassesTheJournal`, which performs the bypass
and is checked by deleting the choice. Nothing had caught it because the test
wallet carried no choices at all, and that minimality was doing work the design
was being credited with. Leonid found on 30 October that the Motivation claimed
a refusal reaches no monitor at all, which is true only of one decided in the
submitter's own interpretation; confirmation-stage rejections are stored as
mediator verdicts and published by Splice Scan on `/v0/events` since Splice
0.4.21. The premise now cites Canton's Transaction Lifecycle reference rather
than asserting itself. Checked against `scan.yaml` and `LocalRejectError.scala`
rather than taken on trust, and `tools/refusal_detector.py` carried the same
over-broad sentence and is corrected too.

**2026-10-30.** The CIP draft was introduced to cip-discuss as message #909:
<https://lists.sync.global/g/cip-discuss/topic/cip_tbd_a_ledger_record_for/122004432>.
`step-0-refusal` is now built and tested in CI, which it never was before, so
62 of the then 165 scripts stopped running only on a laptop. `tools/champions.py`
replaces a remembered number with a measured one and fails loudly when it
cannot find a champion it already knows about. `docs/rfp-27-overlap.md`
assesses all three RFP 27 proposals, this one included, with the interest
declared in its first line.

| What | Evidence | How to check it yourself |
|---|---|---|
| The spending rules are enforced in Daml, not in Python | 32 fences across 5 contracts | `python3 tests/fence_lint.py` |
| Every fence is load-bearing | 82 mutations, each requires a **named** test to go red | `python3 tests/mutation_suite.py` |
| The ledger behaves under attack | 168 Daml test scripts across two packages, 65 and 103 | `daml test --all` in `step-1-mandate/test` |
| A refusal commits as a contract and moves no money | `TryCharge` / `ChargeRefused` in `KyaMandate.daml` | `testRefusalIsOnLedgerAndNothingMoved` |
| The format is implemented three times and they agree | 20 conformance vectors, Python + JavaScript + Go | `python3 tests/conformance.py`, `node tests/conformance.js`, `cd impl/go && go run .` |
| A disclosure cannot have an entry removed | SPEC 6b | `python3 tests/disclosure_smoke.py` |
| A withheld refusal cannot be relabelled accepted | SPEC 6c outcome digest | `python3 tests/completeness_smoke.py` |
| **A second journal cannot be opened behind the auditor's back** | the auditor is a SIGNATORY, not an observer, so a create needs their authority. No contract keys required | `testASecondJournalIsPrevented` |
| An auditor can name a **withheld** refusal from the ledger alone | `AttemptJournal` count plus `missingRefusals`, 14 scripts |
| **A record survives the work reverting** | Two-phase `Attempt`: opened in its own transaction, consumed by the work. An attempt left open is the evidence. 15 scripts | `daml test --files daml/AttemptTest.daml` in `step-0-refusal/test` |
| A resolution cannot lie about what the attempt was | **salted** sha256 commitment, length-prefixed | `testTheResolutionCannotLieAboutTheAttempt` |
| An open attempt does not leak what was attempted | the salt is held off-ledger, so the digest hides as well as binds | `testTheCommitmentHidesAndNotJustBinds` |
| **Destroying the evidence requires the guardian** | the guardian is a signatory of every `Attempt`, so owner and actor together cannot archive one. Every legitimate ending also mints a `Resolution` marker | `testArchivingAnAttemptLeavesANumberedHole` |
| **An asset cannot move outside the journal** | the guardian is a signatory of the asset, and its authority exists only inside an attempt resolution. Enforced by Daml's authorization model, not by convention | `testTheAssetCannotMoveOutsideTheJournal` |
| **One journal serialises every attempt; N shards do not** | `testOneJournalSerialisesAndTwoShardsDoNot` holds the original contract id and uses it twice: one journal refuses, two shards allow both | `daml test --files daml/ShardedTest.daml` |
| Sharding costs none of the four properties | completeness, nameable refusals, single-journal uniqueness and the guard each keep a test | same file |
| A hidden shard is caught | `JournalSet` declares the count, `missingShards` names the gap | `testAHiddenShardIsCaught` |
| A scheduled action cannot run early, late or twice | `DueOnce` and `DueEvery`, with the ledger enforcing the window rather than the scheduler. 9 scripts | `daml test --files daml/ScheduledTest.daml` in `step-0-refusal/test` |
| The limit of that enforcement is stated and tested | a submitter holding BOTH actor and guardian authority bypasses it. This is a control under segregation of duties and a convention without it | `testSubmittingAsTheGuardianDefeatsIt` | `daml test --files daml/JournalTest.daml` in `step-0-refusal/test` |
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
| **The Dev Fund proposal has no champion** | Measured on 2026-10-30 across all 602 proposals: five people have ever volunteered to champion one in the newest 160, and #860 is not among them. #866 got "Happy to champion this." from Yiannis Varelas on 9 October and a vote called seven days later. #788 has `beezybarg`. Two of the three proposals under RFP 27 have one and this does not | Nobody has been asked. `python3 tools/champions.py` |
| **#860 declares six RFPs** | Its labels are rfp-11, rfp-12, rfp-22, rfp-26, rfp-27 and regulatory-compliance. #866 declares one primary and one secondary, and names its champion in the document's own header. A proposal that answers six calls reads as a proposal that answers none | A decision about scope, not a code change |
| **The CIP's own `Type` contradicts its abstract** | The header says `Type: Standards Track`, and the abstract says it "changes no protocol behaviour, requires no new Ledger API service, and needs no participant configuration". One of those is wrong and a CIP editor will see it before a sponsor does | An answer from cip-discuss or an editor. Asked nowhere yet |
| **Two reviewers are owed a reply** | Georgi Radev answered a direct question on 27 October and has had nothing back for four days. Leonid corrected the Motivation on 30 October. Both corrections are built and pushed in `a94f0d7`, so both replies can now report finished work rather than a plan | Nothing. The text is drafted |
| **cip-discuss message #909 describes a draft that has changed** | The list was shown a draft on 29 October that now has a second conformance requirement and a narrowed Motivation. A reader who checks the file against the message finds a mismatch | Nothing technical |
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
  contract keys exist from LF 2.3 but are non-unique, and it cannot see an attempt that bypassed
  it. `testAnUnjournalledAttemptIsStillInvisible` holds that line.
