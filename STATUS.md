# Status: what is proven, what is mocked, what is pending

*Last measured 2026-11-10. Regenerate the numbers with `python3 tools/dashboard.py`,
the champion figures with `python3 tools/champions.py`, the vote state with
`python3 tools/vote_pipeline.py`, and the download figures with
`python3 tools/downloads.py`.*

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
| The ledger behaves under attack | 171 Daml test scripts across two packages, 68 and 103 | `daml test --all` in `step-1-mandate/test` |
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
| The suite is green locally AND in CI | 43/43 locally, and run `42808582420` on 10 November is the first all-green public build since 3 November. Before it, **the build was RED from 4 to 10 November** and nothing noticed: `complexity_lint` failed on eleven functions, and the Python 3.8 and 3.9 jobs failed because `ubuntu-latest` moved to 26.04 and has no build for either. The failure emails arrived and went unread. `tools/pre-commit` ran two of the three lints CI runs, so every commit passed locally and broke on push | `python3 tools/dashboard.py` locally, and the Actions tab for the truth |
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
| **Nobody outside has produced a chain** | 0 stars, 0 forks, 0 outside contributors, 0 outside issues, and no reply on any of the three OpenZeppelin issues in 64 days. Downloads are **488 all time excluding mirrors** (1,602 with), measured with `python3 tools/downloads.py`. The 30-day figure is deliberately not written here: it is a rolling window, it was 226 on 10 November and 205 on 12 November with nobody editing anything, so any prose carrying it is wrong within days. Run the tool. The previous figure here, 84 a month, was written 2026-10-17, was never produced by any tool, and was wrong by a factor of nearly three **against us**: the only cache in the tree counted mirrors and was 47 days old. Downloads are a distribution fact and not an adoption one; nobody outside has produced a chain either way | Distribution, not engineering |
| **No vote has ever been opened on #860** | Re-measured 12 November with `python3 tools/vote_pipeline.py 860`, which prints NO VOTE HAS EVER BEEN OPENED. `.github/.gitvote.yml` sets `automation.enabled: false`, so nothing starts a vote on its own, and all 31 votes in the repository's history were opened by the same person, @hythloda. Passing takes 51% of allowed voters rather than of votes cast, so three of five must actively vote yes and an absence counts as a no. 31 of 616 proposals have ever reached a vote at all, 5.0%. Nine votes have failed and **eight of the nine recorded no vote against**, so proposals die of absence. Five of the nine were re-opened, four within four days, so a failure is a restarted clock. Counting by label reports four, because a re-opened vote has its label reset. The 10 November version of this row said 29 of 400 and seven failures; 400 was a cap the tool mistook for a count. Full working in `docs/dev-fund-vote-mechanism.md` | Nothing. The ask has been aimed at championing for 46 days and never at opening a vote. A champion is also not the gate: 24 of the 31 proposals that got a vote carry no `champion-confirmed` label, and 51 that carry it never got one |
| **#860 has had no reviewer in 43 days** | Corrected 31 October, and this is the row that was aimed at the wrong gate. The fund's own `Development Fund Proposal Review Process.md` says a proposal "moves to 'In Review' once it has been assigned to a champion **or reviewer**", that SIG members "may use the proposal tracking board to self assign proposals they want to review directly", and that "Participation in SIGs is **not limited to Foundation members**". A reviewer is enough to move it out of the queue. Asked for in a comment on 31 October. Edward Newman (Digital Asset, @nycnewman) has reviewed 13 Dev Fund proposals including #788 under the same RFP and #262 OpenZeppelin's stack, and sits in the Security column of the Tech & Ops roster | Nobody had asked for a reviewer, because this file said only a champion would do |
| **The Dev Fund proposal has no champion** | Measured on 2026-10-30 across all 602 proposals: five people have ever volunteered to champion one in the newest 160, and #860 is not among them. #866 got "Happy to champion this." from Yiannis Varelas on 9 October and a vote called seven days later. #788 has `beezybarg`. Two of the three proposals under RFP 27 have one and this does not. **Measured again 9 November, and the lesson inverts.** #866's champion and vote ran their course: the vote closed 6 November having FAILED 0 in favour, 0 against, 0 abstain, 5 did not vote. Both the 28 October and 4 November sittings fell inside its 21-day window and it was called at neither. A champion is necessary and not sufficient | Nobody has been asked. `python3 tools/champions.py`, and `python3 tools/vote_pipeline.py` for the vote itself |
| **#860 carries six RFP labels and declares one** | Corrected 31 October: the proposal's line 8 declares RFP 27 only. The labels rfp-11, rfp-12, rfp-22, rfp-26, rfp-27 and regulatory-compliance were applied by the SIG auto-labeller matching keywords in the body, not by the author. An earlier version of this row said the proposal declared six, which was wrong and was never checked against the file. Narrowing was requested in a comment on 31 October; only a maintainer can change a label. #866 declares one primary and one secondary, and names its champion in the document's own header. A proposal that answers six calls reads as a proposal that answers none | A decision about scope, not a code change |
| **dpm #331 was closed as not a true concern** | Opened 30 October, closed 31 October by Brian Healey with "AI contribution -- does not appear to be a true concern". He was right. The pull request's own body said "I have no report of a user hitting this", which was the reason not to file it rather than a caveat on filing it. The 0600 mechanism is real and the three tests hold; the defect was not. #330, same author, same Co-authored-by trailer, merged six days earlier, because something there was going silently wrong | Nothing. The rule is in CLAUDE.md and the lesson is that a proven mechanism is not a defect |
| **The journal counts refusals, not attacks** | Written down 31 October 2026 after the Binance theft of 29 October, about USD 6.3bn, which early reporting attributes to one engineer's compromised laptop. A guarded asset survives a single stolen key, because the control is a conjunction and three tests show it. The evidence does not survive: an attacker never opens an attempt, so the ledger refuses during interpretation and the counter stays at zero. `testAnAttackerWithOneStolenKeyLeavesNoCount` makes five attempts and shows the auditor seeing nothing | A different mechanism, and not this one. The participant's own rejection log sees it; the mediator's verdicts do not, because an authorization failure never becomes a confirmation request |
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
