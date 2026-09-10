# Changelog

`knowyouragenticai-receipts`. Dates are the day the work landed on `main`, not
the day it was released — a version with no release date below has not been
published.

The format follows [Keep a Changelog](https://keepachangelog.com/); the version
numbers follow [semver](https://semver.org/), which here means a **major** bump
is reserved for a change that breaks a chain somebody already has. Receipts are
meant to outlive the code that wrote them, so that bar is high.

---

## [1.1.0] — unreleased

### Added

- **`Policy` — the rules an agent ran under, sealed into the chain that records
  them.** `Policy(cap=..., currency=..., allow=[...])` and `policy.open()` make
  the policy the first receipt, carrying the cap, allow-list, period and expiry
  as readable text. Every later entry hashes it through `prev`.
- **`guard` and `attempt` — enforcement, not annotation.** A decorator around
  any callable: the policy is checked, the receipt is written, and only then is
  the function called. On a refusal it raises `Refused` and the wrapped function
  **does not run**.
- **`Refused`**, carrying the rule that caused it, so a caller can show the real
  reason rather than inventing one.
- **Conformance vector 17, `unknown-outcome-is-not-tampering`** — an entry whose
  `outcome` is not `ACCEPTED` or `REFUSED`, so the rule below is enforced rather
  than asserted. Python, JavaScript and Go all pass 17/17.

### Fixed

- **The central claim was not true.** A receipt reading `REFUSED — over the cap`
  proved the agent was stopped but not what the cap *was*: an operator who set
  it to a million produced a record indistinguishable from one who set it to
  five. Sealing the policy is what makes "the agent did not overspend"
  checkable, and until this release it was not.
- **The spec contradicted our own records.** `SPEC.md` enumerated `outcome` as
  `ACCEPTED` or `REFUSED` while shipped records already carried `POLICY`,
  `COVERED`, `UNCOVERED` and `NOT TESTABLE`. Anyone implementing strictly from
  that line and rejecting unknown values would have called a valid record
  tampered — the one accusation this format must never make by accident.

### Clarified — not a format change

- **`SPEC.md` §4a: `outcome` is an open vocabulary.** Producers MAY use any
  ASCII value. Verifiers MUST verify **seals, not vocabulary**, MUST NOT report
  an unknown outcome as a broken chain, and SHOULD NOT colour it as a failure.
  No seal computed under the old wording differs under the new one.

### Compatibility

Additive only. `Chain`, `canonical`, `seal`, `verify` and `assert_ascii` are
unchanged, every 1.0.0 chain still verifies, and every 1.0.0 program still runs.
A policy-sealed chain is an ordinary chain whose first entry happens to be a
policy — 1.0.0 verifies it correctly without knowing what it is.

---

## [1.0.0] — 2026-09-06

First public release.

### Added

- `canonical`, `seal`, `verify`, `assert_ascii` and `Chain`: the receipt format
  and its hash chain. Sorted keys, `","`/`":"` separators, non-ASCII escaped,
  `sha256(canonical(receipt without seal) + prev)`.
- `NonAsciiInReceipt` and `BrokenChain`, so the two ways a chain goes wrong are
  distinguishable by type rather than by reading a message.
- 16 conformance vectors shipped inside the package, runnable offline with
  `python -m knowyouragenticai_receipts selftest`.
- `verify` and `example` subcommands.

### Notes

MIT. **Zero dependencies**, stdlib only — a format meant to be re-implemented
should not oblige anyone to adopt a dependency tree to check it.

[1.1.0]: https://github.com/dominicrume/cantor8_kya_rails
[1.0.0]: https://pypi.org/project/knowyouragenticai-receipts/1.0.0/
