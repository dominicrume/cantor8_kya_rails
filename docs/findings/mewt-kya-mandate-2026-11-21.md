# Mewt run on our own mandate contract, 21 November 2026

A third party's mutation tester, run on our own code. We did not write Mewt.

| | |
|---|---|
| Tool | [Mewt](https://github.com/trailofbits/mewt) 4.0.0 by Trail of Bits, AGPL-3.0, release `v4.0.0` |
| Obtained | the macOS arm64 release tarball; sha256 `e0ee0fb8eadeade3be22c582e1fcc188865e5a26b7889e1ebd9532099a873f6f` matched the file published with the release. That shows the download is intact, not who built it |
| Target | `step-1-mandate/daml/KyaMandate.daml`, on a **copy**, never the working tree |
| Mutations | `CPS,CPR,SPS,COS,LOS,BL`: controller swap and removal, signatory swap, comparison and logical operators, boolean literals. 109 mutants |
| Test command | `daml build` then `daml test` in `step-1-mandate/test`, 300 second limit |

## Results

| Run | Tests | Caught | Not caught |
|---|---|---|---|
| 1 | 130 scripts, before this work | 87 | **22** |
| 2 | 140 scripts, with `KyaBoundaryTest.daml` | 107 | **2** |
| after | one test strengthened | see below | 1 |

Run 2's two survivors were `COS 12` and `COS 86`. A full third campaign was **not** re-run.
`COS 86` was a gap in the new test (an amount small enough to fit either way), so the test
was strengthened and the mutant was then **applied by hand to a copy**: the strengthened
test goes red. `COS 12` was applied the same way and every test still passes.

`COS 12` (`cap > 0.0` to `cap /= 0.0`) is an **equivalent mutant**: `spent >= 0.0 && spent <= cap`
already forces `cap >= 0`, so no test can tell the two apart. It is the one honest survivor.

## What the 22 were

Real, in product-defining logic, and none of them found by our own guard-deletion review:

- **Authority.** Removing the spender from `Adjust`'s controllers (`CPR 104`). The agent
  consents to its own leash; nothing pinned that the owner alone cannot move the cap.
- **A guard.** `amount > 0.0` loosened to `/= 0.0` (`COS 42`): a negative charge with something
  already spent would lower the spent total.
- **Edges.** The instant of expiry (`COS 38`, `COS 75`), `Adjust` to exactly what is spent
  (`COS 70`), the period limit exactly reached (`COS 91`, `COS 93`).
- **The period window.** A period limit with no window length never resets (`BL 2`, `BL 4`,
  `BL 5`), and the rollover comparison on all three code paths (`COS 55`, `COS 61` to `65`,
  `COS 86` to `90`).

## How this differs from our own review

Our review (`tools/assurance.py`) deletes each `ensure` and `assertMsg` and requires a **named**
test to go red. Mewt changes operators and authority lists instead and has no delete-the-check
mutation. Each found things the other cannot: after the review reported 50 of 50 covered,
Mewt still found 22 survivors. They are complements. See also `docs/findings-openzeppelin.md`.

## Reproduce

Download the release and check the sha256 above, then run it on a copy of `step-1-mandate`
with the options in the table. It took 38 minutes for run 1.
