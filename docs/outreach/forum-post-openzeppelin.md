# Forum post: reply in OpenZeppelin's feedback thread

**Where:** https://forum.canton.network/t/feedback-welcome-openzeppelins-daml-development-stack-is-public-and-open-for-review/9059
**As:** a reply in that thread, not a new topic. It carries the invitation this
answers, and it already has an audience.

**Before posting, confirm:** the issue numbers below. Only `canton-contracts#43`
is recorded in this repo; the other two were opened later and are not verified
here.

---

I took up the invitation in this thread — *"Test it… Clone the repos… open an
issue with how it works for what you're building"* — and ran a mutation test
over the authorisation fences in three of the repositories.

**The question isn't whether the tests pass.** It's whether anything would
notice if a rule were removed. Those two diverge silently and in one direction:
a test written after a fence, asserting the behaviour the fence already
produces, passes whether or not the fence is still there.

**Method.** For each `assertMsg` and `ensure`, make the condition vacuous,
rebuild the DAR, run the suite, and require a *named* test to go red. A fence
whose removal leaves every test green is reported as uncovered.

| Repository | Package | Fences | Scripts | Covered | Uncovered |
|---|---|---:|---:|---:|---:|
| `canton-contracts` | `access-control-v1` | 7 | 17 | 4 | **3** |
| `canton-token-template` | `simple-token` | 32 | 42 | 8 | **24** |
| `canton-stablecoin` | `stablecoin` | 30 | 27 | 5 | **25** |
| | | **69** | **86** | **17** | **52** |

**These are not vulnerabilities.** Every fence is present and working. The
finding is that the suites would not notice if one were removed — which matters
at the next change, not today. `experiments/` also says plainly that it is not
production-ready; I still think the gap is worth naming because the top-level
README says those packages are tested in CI.

**The control that makes the number believable:** some fences come back covered
in every repository, each naming the script that dies —
`AccessControlV1Test.daml`, `Test/Negative.daml`, `Test/Cdp.daml`. If the
harness were failing to reach your suites, nothing would ever come back
covered.

**The ones I'd look at first**, ranked by what an uncovered fence would permit
rather than by anything the tool knows:

- `Oracle.daml:29` — `"New price must be positive"` on `PriceOracle_UpdatePrice`.
  Collateral ratios are computed from this price.
- `AccessControlV1.daml:289` — `eRoleAssigneeMismatch`. Your own message for it
  is *"grant does not name the caller (impersonation)"*.
- Four separate `expectedAdmin does not match factory admin` checks in
  `Rules.daml`, none covered.

**My tool was wrong three times before it was right**, and each version produced
confident false findings. Worth stating, because it's the reason to believe the
fourth version:

1. **It deleted the fence's line.** A fence that is the last statement in a `do`
   block can't be removed without breaking the block, so four of seven
   access-control fences came back "stopped compiling".
2. **It read `daml test`'s exit code as the build result.** `daml test` exits
   non-zero when a test goes *red* — the exact outcome being hunted. Four
   **covered** fences were reported as compile failures. That was one step from
   being filed here as findings.
3. **It mutated lines instead of statements.** You write assertions across two
   lines, so a single-line replacement produced `assertMsg "Input True`. Thirty
   of `simple-token`'s thirty-two fences came back "stopped compiling", and every
   one was my regex rather than your code.

A fourth was mine rather than the tool's: I hand-verified a finding with the
wrong indentation, which broke the build, left the previous DAR in place, and
gave me a confident 17/17 against code the mutation never reached. Every finding
is now checked for a **changed DAR hash**, not just a passing suite.

**Reproducing it** — stdlib Python, nothing to install:

```bash
git clone https://github.com/OpenZeppelin/canton-token-template
cd canton-token-template/simple-token && daml build && cd ..
python3 tools/daml_mutate.py --src simple-token --test simple-token-test
```

`canton-stablecoin` needs its dependency chain built first: `simple-token`, then
`stablecoin`, then test against `stablecoin-test`.

**The findings come out as a hash-chained record, not a report.** One entry per
fence, carrying the file, the line, the verdict, the rule that produced it and
the `daml` version, all inside the seal. Change one verdict from `UNCOVERED` to
`COVERED` and the chain breaks at that entry — including if I'm the one who
changes it. It checks on a static page with nothing installed:

- Method, controls and the full write-up:
  https://github.com/dominicrume/cantor8_kya_rails/blob/main/docs/findings-openzeppelin.md
- The records themselves:
  https://github.com/dominicrume/cantor8_kya_rails/tree/main/docs/findings
- Drop one here to check it: https://dominicrume.github.io/cantor8_kya_rails/

Two of the three rows above have now been reproduced from clean clones weeks
apart, and matched exactly.

Filed as
[canton-contracts#43](https://github.com/OpenZeppelin/canton-contracts/issues/43).
I'd genuinely rather be told that some of these are deliberately redundant, or
covered by a test my harness can't attribute, than be right about the number —
the tool can't see intent, and that's the limit of what it's claiming.

— Rume Dominic, Aston University
