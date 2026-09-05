# Contributing

The most useful thing you can do here is **implement the receipt seal in
another language and prove it matches.**

Read [SPEC.md](SPEC.md). It is written so that a working implementation can be
produced from the text alone. It is about **twenty lines** for the format itself in most
languages — see [`impl/pipe/reference.py`](impl/pipe/reference.py), which is the
whole thing.

**You do not have to write a test harness.** That used to be the tax: the Go
runner is 115 lines, nearly as much work as the format, all of it paid before
you could find out whether you were right. Instead, read one JSON object per
line from stdin and write one per line to stdout:

```
{"op":"canonical","body":{...}}          ->  {"out":"<the canonical string>"}
{"op":"seal","body":{...},"prev":"..."}  ->  {"out":"<64 lowercase hex>"}
{"op":"verify","receipts":[...]}         ->  {"out":<0, or the n that failed>}
{"op":"reject","body":{...}}             ->  {"out":"<field>"} or {"out":null}
```

Anything you have not written yet: answer `{"skip":true}`. It is reported, not
counted as a pass.

```bash
python3 tests/conformance_any.py -- ./your-implementation
```

That grades you against all 16 vectors in
[`tests/vectors.json`](tests/vectors.json) and tells you which case disagreed
and what it wanted. When it says CONFORMANT, open a pull request.

If it does not, open an issue with the case that failed and the bytes you
produced — a disagreement between two implementations is the most valuable bug
this project can receive, because it means the spec is ambiguous, and that has
already happened twice.

## Run the checks

```bash
python3 tests/conformance.py     # reference implementation, Python
node    tests/conformance.js     # reference implementation, JavaScript
cd impl/go && go run .           # third implementation, written from the spec
python3 tests/conformance_any.py -- python3 impl/pipe/reference.py
cd step-1-mandate/test && daml test   # the on-ledger fences, 89 scripts
```

All of these run in CI on every pull request.

## Good first contributions

- **A fourth implementation** — Rust, TypeScript, Java, C#. Put it in
  `impl/<language>/`. No runner needed: speak the pipe protocol above and
  `tests/conformance_any.py` grades it.
  [`impl/go/`](impl/go/) is the worked example: written from SPEC.md alone,
  and it earned its place by finding a real gap — the spec did not state the
  JSON escapes for quote, backslash and control characters, so the author had
  to infer them from RFC 8259. Section 4 says them now, and
  `escapes-quote-backslash-tab` is the vector that removes the guess. That is
  what a new implementation is for.
- **A vector we do not have.** This is worth as much as an implementation.
  Two of the sixteen exist because someone asked *which wrong implementations
  still pass?* and found that two did: one emitting raw UTF-8 rather than
  `\uXXXX`, and one that checked every seal but never compared the `prev`
  field. Both passed all fourteen vectors that existed at the time; there are sixteen now, and the two extra are those cases. If you can think of a case
  where two honest implementations might diverge, that case belongs in the
  file — add it to `tests/make_vectors.py`, which generates them.
- **An MCP server** so a language model can hold a mandate directly. The
  interesting part is that the model *feels* the refusal.
- **A calendar-aligned period option.** The current window is rolling: the
  first charge after a window elapses opens a new one. Some businesses want
  "per calendar day" instead. That is genuinely harder — timezones, and a
  start time that must advance without an unbounded loop — and it needs the
  same mutation coverage as every other fence.

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
