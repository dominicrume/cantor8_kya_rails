# Changelog

Dates are the day the version was published. The format itself is versioned
separately in [SPEC.md](../SPEC.md); a change that alters any seal is a new
*specification* major version, not merely a package one.

## 1.0.0 — unreleased

First release.

Thirteen things were found and fixed by attacking the package before publishing
rather than after. Recorded here rather than quietly cleaned up, because
several are the kind of defect this project exists to argue against.

### Correctness

- **`verify()` no longer raises on malformed input.** It used to die with
  `AttributeError` on a list of strings or nulls — which is exactly the input
  it exists to handle, since the whole point is checking a file someone else
  gave you. Malformed input is now a verdict, never an exception.
- **`Chain.stamp()` refuses to extend a chain that does not verify**
  (`BrokenChain`). Previously you could tamper with history and keep appending;
  each new entry looked correct on its own while resting on something that was
  not.
- **`amount` must be a string.** Passing `1/3` was accepted and silently stored
  as `"0.3333333333333333"`. Amounts are strings precisely so that a number
  cannot be re-formatted differently by different JSON encoders, and the
  argument now enforces what the documentation always claimed.
- **The ASCII rule sees nested values.** `{"what": "Pay ₦500"}` was rejected
  and `{"what": {"note": "Pay ₦500"}}` was not. Nothing sealed wrongly — every
  implementation escapes nested strings consistently — but the check did not do
  what its own name said.
- **`verify()` always returns a usable position.** A receipt missing its `n`
  used to come back as `(False, None)`; it now falls back to the receipt's
  1-based place in the list, so an entry too damaged to carry a number can
  still be located.

### Interface

- **`python -m knowyouragenticai_receipts verify <file>`** — check a chain without
  writing any code. Reads bare JSON or a `const RECEIPTS = [...]` assignment,
  and says plainly that a passing check proves nothing was *edited*, not where
  the file came from. Exit 0 holds, 1 broken, 2 unreadable.
- **`python -m knowyouragenticai_receipts selftest`** — unchanged behaviour, now an
  explicit subcommand rather than the only thing the module did.
- **Type hints throughout, and a `py.typed` marker**, so the package type-checks
  for anyone depending on it.
- **`repr(chain)`** now reads `<Chain 6 receipts, head 54767e02..., verified>`
  and says `BROKEN at 3` when it is.

### Adoption

Four things found by using the package as a newcomer rather than as its author.

- **`currency` is required.** It defaulted to `"CC"` — Canton Coin — so anyone
  recording dollars sealed them as Canton Coin, permanently and silently. A
  currency nobody chose is worse than an argument nobody wanted to type.
- **`allowed()` and `refused()`.** Recording one payment took seven required
  arguments in vocabulary a newcomer does not have yet. Who authorised the
  payments and which rail they ran on describe the desk, not the payment, so
  they are set once on the `Chain`.
- **A wrongly-shaped file is no longer called tampered.** `{"receipts": [...]}`
  and `{"exported_at": ..., "data": [...]}` used to come back as `BROKEN at
  receipt 1`. They are now found and checked. A file that genuinely is not a
  chain says so, and never says BROKEN — that word is an accusation that
  someone edited this, and it must not be made falsely. Exit codes: 0 holds,
  1 broken, 2 not a chain.
- **`python -m knowyouragenticai_receipts example`** — the whole idea in one runnable command: an agent with a
  spending limit, four attempts, two stopped, then the record tampered with and
  caught.

### Verified

- 16 conformance vectors, in Python, JavaScript and Go.
- `requires-python = ">=3.8"` is now exercised by a CI matrix rather than
  asserted. It was previously an untested claim in published metadata.
