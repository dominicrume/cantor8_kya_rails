# Mutation testing three OpenZeppelin Canton repositories

Run on 2026-09-07 with [`tools/daml_mutate.py`](../tools/daml_mutate.py), answering
the standing invitation in OpenZeppelin's
[forum thread](https://forum.canton.network/t/feedback-welcome-openzeppelin-s-daml-development-stack-is-public-and-open-for-review/9059):
*"Test it… Clone the repos… open an issue with how it works for what you're
building."*

The method: make each `assertMsg` condition or `ensure` clause vacuous, rebuild
the DAR, run the test suite, and require a **named** test to go red. A fence
whose removal leaves every test passing is reported as uncovered.

---

## Results

| Repository | Package | Fences | Scripts | Covered | **Uncovered** | Broke | Stale |
|---|---|---:|---:|---:|---:|---:|---:|
| `canton-contracts` | `access-control-v1` | 7 | 17 | 4 | **3** | 0 | 0 |
| `canton-token-template` | `simple-token` | 32 | 42 | 8 | **24** | 0 | 0 |
| `canton-stablecoin` | `stablecoin` | 30 | 27 | 5 | **25** | 0 | 0 |
| | | **69** | **86** | **17** | **52** | 0 | 0 |

All three are reported, one issue per repository — verified open with no reply
on 2026-09-08:
[canton-contracts#43](https://github.com/OpenZeppelin/canton-contracts/issues/43),
[canton-token-template#9](https://github.com/OpenZeppelin/canton-token-template/issues/9),
[canton-stablecoin#9](https://github.com/OpenZeppelin/canton-stablecoin/issues/9).

## The record, not the report

The table above is a claim in a Markdown file. Anyone with commit access to this
repository — including its author — can soften a row in it, and the file will
look exactly the same afterwards.

So the run also emits its findings as a sealed chain, one entry per fence, with
the file, the line, the verdict, the rule that produced it and the toolchain
version inside each seal:

- [`canton-contracts-access-control-v1.json`](findings/canton-contracts-access-control-v1.json)
  — 7 entries, head `93e75483…`
- [`canton-token-template-simple-token.json`](findings/canton-token-template-simple-token.json)
  — 32 entries, head `53c616fe…`
- [`canton-stablecoin-stablecoin.json`](findings/canton-stablecoin-stablecoin.json)
  — 30 entries, head `5d9c0a46…`

**All three rows of the table above have now been reproduced** from clean clones
weeks after the runs that produced them, and every column matched: 7/17/4/3,
32/42/8/24, 30/27/5/25. The table was typed by a person from the first run. The
records were not, and they are what you should check.

Drop that file on <https://dominicrume.github.io/cantor8_kya_rails/>. Nothing to
install, no account, and no need to trust this repository: change one verdict
from `UNCOVERED` to `COVERED` first, and the page names the entry it broke at.

That is the difference between an audit report and an audit record. Produced by
[`tools/assurance.py`](../tools/assurance.py); the property is tested in
[`tests/assurance_smoke.py`](../tests/assurance_smoke.py), and
`tests/mutation_suite.py` verifies that a version of the tool which relabels an
uncovered fence as covered turns that suite red.

## Why these numbers are trustworthy

**Some fences come back covered in every repository.** That is the control that
matters. If the harness were systematically failing to reach the test suite,
nothing would ever be reported as covered — and in all three runs a subset is,
each naming the specific script that dies:

- `canton-contracts` → `AccessControlV1Test.daml`
- `canton-token-template` → `Test/Negative.daml`
- `canton-stablecoin` → `Test/Cdp.daml`

Those projects have dedicated negative-test modules, and the harness correctly
identifies which fences those modules actually guard.

**`BROKE` and `STALE` are zero everywhere.** Earlier versions produced dozens of
each, and every one was a defect in the operator rather than a fact about the
code under test — see *What went wrong first* below.

## Verified by hand

Four findings were re-checked manually rather than trusted from the tool. For
each: neuter the fence, confirm `daml build` **exits zero**, confirm the DAR
hash **changes**, then run the suite.

| Fence | Build | DAR hash | Tests after |
|---|---|---|---|
| `AccessControlV1.daml:139` `eRoleAdminMismatch` | 0 | `611c35e1…` → `2c8722cd…` | 17 / 17 pass |
| `Rules.daml:38` "Transfer amount must be positive" | 0 | `3bd1f812…` → `99704c74…` | 42 / 42 pass |
| `Preapproval.daml:39` "Transfer amount must be positive" | 0 | changed | 42 / 42 pass |
| `Oracle.daml:29` "New price must be positive" | 0 | `08612de7…` → `6a57bcfd…` | 27 / 27 pass |

The DAR-hash step is not ceremony. A failed build leaves the previous DAR in
place, the suite then passes against code the mutation never reached, and the
result reads exactly like a finding. That happened once during this work and is
the reason the check exists.

## The ones worth a second look

Not ranked by the tool — ranked by what an uncovered fence would permit.

**`Oracle.daml:29` — `assertMsg "New price must be positive"`**
`PriceOracle_UpdatePrice` on a stablecoin. Collateral ratios are computed from
this price. Nothing fails if the guard is removed.

**`AccessControlV1.daml:289` — `eRoleAssigneeMismatch`**
The project's own message for it is *"grant does not name the caller
(impersonation)"*.

**`AccessControlV1.daml:139` — `eRoleAdminMismatch`**
Guards `RoleAdmin_RevokeRole`: what stops one admin revoking a grant issued by a
different admin.

**Four separate `expectedAdmin does not match factory admin` checks** in
`canton-token-template`'s `Rules.daml`, none covered.

## What this is not

**These are not vulnerabilities.** Every fence is present and working. The
finding is that the test suites would not notice if one were removed — which
matters when the next change is made, not today.

**`canton-contracts/experiments/` is explicitly not production-ready.** Its own
README says so: *"Early-stage Daml packages that are not ready for application
use… they have not gone through the review, interface, and upgrade decisions
that a released component must satisfy."* The top-level README does say they
*are* tested in CI, which is why the gap is worth naming.

**The tool cannot see intent.** A fence may be deliberately redundant, or
covered by a test the harness cannot attribute. That is why issue #43 ends by
inviting correction rather than asserting a defect.

## What went wrong first

Three defects, none of which this project's own repository could have surfaced —
they only appeared against code written by somebody else.

**Deleting the line.** The first operator removed a fence's line. A fence that
is the last statement in a `do` block cannot be removed without breaking the
block, so four of seven access-control fences returned "stopped compiling".
Fixed by making the *condition* vacuous instead.

**Reading the wrong exit code.** `build_and_test` returned `daml test`'s exit
code under the name `compiled` — and `daml test` exits non-zero when a test goes
**red**, which is the outcome being hunted. Four *covered* fences were reported
as compile failures. One step from being filed as findings.

**Mutating lines instead of statements.** OpenZeppelin write assertions across
two lines:

```haskell
assertMsg "Input holding instrumentId does not match transfer"
  (hv.instrumentId == expectedInstrumentId)
```

A single-line replacement produced `assertMsg "Input True`. Thirty of
`canton-token-template`'s thirty-two fences came back "stopped compiling", and
every one was the regex rather than their code. The operator now consumes the
whole statement by Daml's layout rule.

A fourth was mine rather than the tool's: verifying by hand with the wrong
indentation broke the build, left the old DAR in place, and produced a confident
17/17 against untouched code.

## Reproducing

```bash
git clone https://github.com/OpenZeppelin/canton-token-template
cd canton-token-template/simple-token && daml build && cd ..

python3 tools/daml_mutate.py --src simple-token --test simple-token-test
```

`canton-stablecoin` needs its dependency chain built first: `simple-token`, then
`stablecoin`, then test against `stablecoin-test`.
