# Changelog

`knowyouragenticai-receipts`. Dates are the day the work landed on `main`, not
the day it was released — a version with no release date below has not been
published.

The format follows [Keep a Changelog](https://keepachangelog.com/); the version
numbers follow [semver](https://semver.org/), which here means a **major** bump
is reserved for a change that breaks a chain somebody already has. Receipts are
meant to outlive the code that wrote them, so that bar is high.

---

## [1.2.0] — 2026-10-22

### Added

- **`disclose` — hand over the refusals without handing over the book.** A
  stablecoin issuer can give a counterparty every refusal a control produced
  and none of the payments that went through. `disclose(chain)`,
  `refusals_only(chain)` and `check_disclosure(doc)`, with
  `what_this_reveals(doc)` stating in plain words what a reader learns and
  what they do not. Disclosure spec **1.3**.
- **`outcome_digest` — SPEC 6c, non-equivocation.** Each entry's position and
  outcome gets its own digest, same shape as a seal:
  `digest[i] = sha256(canonical({"n": n, "outcome": outcome}) + digest[i-1])`.
  Withhold a refusal, relabel it accepted, and the digest stops matching.
- **`assurance` — derived by the verifier, never read from a field.**
  `SELF_ATTESTED`, `ANCHORED`, `LEDGER_RECORDED`. A producer cannot write its
  own assurance level into a document and have a reader believe it.

### What this version does NOT claim

Named here because the opposite was claimed for four hours on 10 October,
before the heading was corrected.

**`outcome_digest` is not completeness.** It proves non-equivocation and
append-only ordering. A producer who never writes an entry computes the
digest over the shorter list and it verifies perfectly. Write-time omission
is unreachable by any commitment scheme, because the producer chooses what to
commit to.

arXiv:2609.32495 ("Hearsay", 26 September 2026) demonstrates this
independently: 28 omissions injected into deployed agent harnesses, caught in
full by an append-only log kept **outside** the harness, and **caught not at
all by a hash chain over the harness's own record**. That is this package with
no anchor, described exactly. The digest is worth having only once it is
pinned somewhere the producer does not control.

The ledger half of that answer lives in `step-0-refusal` in the repository and
is Daml, not Python. It does not ship in this package and never has.

### Fixed

- **`py.typed` promised types that `mypy --strict` would not accept.** The
  marker said the annotations were a contract; the annotations did not hold up
  under strict checking. Now they do, and CI checks it, so the promise is
  enforced rather than asserted.

### Unchanged on purpose

The canonical form and the seal. `canonical()` is still sorted keys with
`","` and `":"` separators, ASCII-escaped, and
`seal = sha256(canonical(body) + prev)`. **Receipts written by 1.0.0 verify
under 1.2.0 and always will.** A change here would be a major version,
because receipts are meant to outlive the code that wrote them.

---

## [1.1.0] — 2026-09-10

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
- **`Chain.save(path)` and `Chain.load(path)`.** `save` verifies before writing,
  so a file this library wrote is never one it would refuse to read back;
  `load` verifies before returning, so a tampered chain cannot be extended with
  every later receipt sealed onto a lie.
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

- **`guard` handles `async def`.** Calling an `async def` does not run it — it
  builds a coroutine — so the wrapper stamped `ACCEPTED` and spent the budget
  the moment the function was *called*. A caller who never awaited the result
  left a receipt saying a payment was authorised when nothing had happened.
  Refusals were unaffected, which made it worse: it only ever erred in the
  flattering direction, and over-reporting success is the exact failure this
  library exists to prevent. The async path now decides inside the coroutine,
  so nothing is recorded until somebody awaits it.

### Changed

- **`Chain.stamp` no longer re-verifies the whole chain on every append.** It
  did, which is O(n²): 28 seconds to write four thousand receipts, and an agent
  in a loop reaches four thousand. Verification is now amortised — every stamp
  still verifies everything below 64 receipts, and above that the full pass
  happens at doubling points while each append checks the new tail. Twenty
  thousand receipts now take 0.16s.

  The practical difference: a receipt edited **in place** on a long chain is
  caught within one doubling rather than on the very next append. `verify()`,
  `save()` and `load()` always check everything, so nothing unverified reaches
  disk or comes back off it.

- **`Policy` operations are atomic.** `check` → seal → `commit` now runs under a
  re-entrant lock. Two callers could each be inside the cap on their own reading
  and over it together; CPython's GIL made the window small enough that eight
  threads never reproduced it, which is luck rather than a guarantee.

- **`guard` reads `amount` and `payee` out of `**kwargs`.** A tool written as
  `def run(**kw)` — how most tool-calling frameworks shape a handler — used to
  raise `TypeError`, because the arguments were collected into a nested dict and
  the guard saw a function with neither.

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
