# Contributing

The most useful thing you can do here is **implement the receipt seal in
another language and prove it matches.**

Read [SPEC.md](SPEC.md). It is written so that a working implementation can be
produced from the text alone. Then check yourself against
[`tests/vectors.json`](tests/vectors.json) — 9 cases covering the base seal, key
ordering, refusals, decimal handling, two kinds of tamper, and the two non-ASCII
rejections.

If your implementation reproduces all 9, open a pull request. If it does not,
open an issue with the case that failed and the bytes you produced — a
disagreement between two implementations is the most valuable bug this project
can receive, because it means the spec is ambiguous.

## Run the checks

```bash
python3 tests/conformance.py     # reference implementation, Python
node    tests/conformance.js     # reference implementation, JavaScript
cd step-1-mandate && daml test   # the on-ledger fences, 10 scripts
```

All three run in CI on every pull request.

## Good first contributions

- **A third implementation** — Go, Rust, TypeScript, Java. Put it in
  `impl/<language>/` with a runner that consumes `tests/vectors.json`.
- **A vector we do not have.** Empty strings, very long fields, a chain of one
  thousand receipts, a `prev` that points at the wrong earlier seal. If you can
  think of a case where two honest implementations might diverge, that case
  belongs in the file.
- **An MCP server** so a language model can hold a mandate directly. The
  interesting part is that the model *feels* the refusal.
- **Per-period limits in the Daml** — spend no more than X per day, on top of
  the total cap. Note the warning in the challenge brief: this turns into date
  arithmetic quickly, so bring tests.

## House rules

These are not style preferences. They are the reasons the code is trustworthy.

1. **Spending rules live in Daml, never in Python.** A cap checked in
   application code is the agent checking itself. If a rule can be enforced in
   the choice body, that is where it goes.
2. **Python is stdlib only.** No pip installs. The demo must run on a laptop
   with no network.
3. **Canonicalisation stays byte-identical across implementations.** Any change
   that alters a seal is a new major version of the spec, and every
   implementation and vector changes together.
4. **Anything simulated is labelled**, in the code and inside the sealed
   receipt. A receipt that does not name its decider is a claim, not a receipt.
5. **A failure to reach the ledger is never recorded as a refusal.** If we could
   not ask, nothing is written. This one has bitten us; see commit `05f3f48`.

## Why the commit messages are long

They explain the failure a change prevents, not just what changed. `git log` is
the design record for this repo — if you are wondering why something is shaped
the way it is, look there before asking.
