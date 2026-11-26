# Changelog

`knowyouragenticai-receipts`. Dates are the day the work landed on `main`, not
the day it was released — a version with no release date below has not been
published.

The format follows [Keep a Changelog](https://keepachangelog.com/); the version
numbers follow [semver](https://semver.org/), which here means a **major** bump
is reserved for a change that breaks a chain somebody already has. Receipts are
meant to outlive the code that wrote them, so that bar is high.

---

## [Unreleased]

### Added

- **Witness (SPEC 6g).** A pin kept on the chain's own disk is only as safe as that disk. A witness
  is a separate process, run as another user or on another machine, that records each pin with its
  own clock and a MAC (a keyed hash) from a key the agent never holds, and refuses a second,
  different seal at a count it has already recorded. `kya_stamp` takes an optional `witness_url`,
  asks the witness BEFORE writing, fails closed if it cannot be reached, and reports a write the
  witness did not record as NOT witnessed; `kya_verify` takes `witness_url` and `witness_key_file`
  and reports `witness_check`, saying whether the MACs were checked. Run one with
  `python3 -m knowyouragenticai_receipts.witness serve`. The MAC is symmetric, so this is not a
  transparency log such as Sigstore Rekor: only a holder of the key can check it, and nobody
  outside has more than the witness operator's word. Python only, no conformance vector,
  tested on localhost only. `tests/witness_smoke.py`.

- **Pins (SPEC 6f).** A hash chain cannot tell a chain from a fresh valid one: delete the file,
  start again, and it verifies. `head_pin()` and `check_pins()` now give the count and final seal
  to keep elsewhere, and catch truncation, delete-and-restart and replacement with another valid
  chain. `kya_stamp` takes an optional `pin_file` (an append-only log), refuses to extend a chain
  that no longer matches it, and appends a pin after each write; `kya_verify` takes the same
  and reports `pin_check`. A pin never raises the assurance level, and one kept on the same disk
  is only as safe as that disk. Python only, no conformance vector yet. `tests/pin_smoke.py`.

- **`outcome_digest(receipts)` — one hash over every entry's position and
  outcome, in order.** SPEC 6c.

  SPEC 6b proved nothing could be removed from a disclosure. It did not prove
  nothing could be hidden inside one. A withheld entry declares its outcome,
  but its body is gone, so nothing contradicts the declaration: `disclosing`
  catches a withheld entry that admits it was refused, and never one
  relabelled `ACCEPTED`. That is the only question an auditor asks about a
  population of exceptions, and a hash chain cannot answer it, because the
  seal of a withheld entry covers a body the reader never sees.

  `disclose()` now emits an `outcomes` field and bumps the disclosure `spec`
  to `1.3`. `check_disclosure()` recomputes it from the entry-level outcomes
  and refuses a document where the two disagree.

  **Alone it proves nothing**, and the function's own docstring says so: the
  producer writes the document and could recompute the digest over the same
  lie. Its value is that it makes *non-equivocation* anchorable. One value,
  pinned to an origin the producer does not control, now covers every entry's
  outcome as well as the chain's integrity. It still cannot prove an attempt
  was recorded at all. Nothing can.

  Optional on both sides. A disclosure carrying no `outcomes` verifies
  exactly as before, because refusing one would break every file already
  handed out, over a claim that file never made.

  Mirrored byte-for-byte in `verifier.html`. `tests/completeness_smoke.py`
  lifts the JavaScript out of that file rather than transcribing it, so a
  drift between the two implementations fails the build.

### Fixed

- **`check_disclosure()` now compares each shown body's own `n` and `prev` to
  the entry that carries it.** Found on 14 November 2026. A forger could delete
  an entry, renumber the envelope and re-seal each shown body, and the document
  verified with a refusal missing, because the body's own position and link
  were never compared. They are now, and `verifier.html` does the same.
  A forger who also rewrites every body and re-seals still passes: a seal is
  not a signature, and only a head held outside the document shows that an
  entry was removed. SPEC 6b now says so. **Not released.** PyPI still has
  1.2.0 without this fix, and nothing here approves a release.

---

## [1.4.0] — 2026-11-23

### Added

- **`agent_ref` (SPEC 6e, spec 1.4).** A receipt may now carry `agent_ref`, a pointer at the
  identity an agent acted under: a DID, an Agent Passport id, an OAuth client id. It is optional,
  present only when set, at most 256 ASCII characters, and **establishes nothing**: it is an
  address, not evidence, and a verifier must still report `self-attested`. It exists so identity
  systems can point at a chain without this format competing with them. Conformance vector 21
  makes it binding; Python, JavaScript and Go agree, 21 of 21. No existing seal changed, and a
  chain with no `agent_ref` is byte-identical to 1.3.
- **MCP server speaks the stateless protocol (2026-07-28), alongside the old handshake.** Requests carry the caller in `_meta`, `server/discover` is implemented, a request missing a required `_meta` field is `-32602`, an unsupported version is `-32022` with the list that is supported, and nothing is remembered from one request to the next. A non-object request gets `-32600` instead of crashing the server.
- **`kya_stamp` takes `agent_ref`,** defaulting to `mcp-client:name/version` from the request's `_meta` when omitted, labelled as a client label and not an identity.


## [1.3.1] — 2026-11-21

### Fixed (VeritaPort Independent Review Hardening)

- **Fail-Closed on Tampered Files (`kya_stamp`):** Attempting to stamp onto an existing receipt file that fails verification now aborts immediately with an error and **never overwrites** the file. Preserves tamper evidence on disk instead of replacing the history with a 1-receipt chain.
- **Atomic File Writing:** All disk writes in `handle_stamp`, `Chain.save()`, and `handle_disclose` now write to a temporary file (`.tmp.<pid>`) and atomically replace the destination via `os.replace()`, preventing partial or corrupted files.
- **Default Persistence Path:** `kya_stamp` now defaults `save_path` to `kya-receipts.json` in the current working directory if omitted, preventing silent in-memory loss across server restarts.
- **Accurate Verification Claims (`kya_verify`):** Tool description and response message updated to explicitly state that standalone verification proves no entries were edited, and that proving no tail truncation or rebuilt histories requires comparing against an external anchor.
- **Safe Overwrite Protection (`kya_disclose`):** Refuses to overwrite an existing file unless `overwrite=True` is explicitly passed.
- **Explicit Currency/Unit Requirement:** Removed silent `"USD"` fallback in `kya_stamp`. `currency` is now required and accepts non-financial units (e.g., `QUERY`, `EVENT`, `N/A`).

---

## [1.3.0] — 2026-11-21

### Added

- **Native Model Context Protocol (`mcp`) Server.** Built-in standard library
  JSON-RPC 2.0 server over stdio for AI assistants (Claude Desktop, Claude Code,
  Cursor). Zero external dependencies. Available via `knowyouragenticai_receipts.mcp`.
  Exposes tools:
  - `kya_stamp`: Append an action/refusal attempt to the receipt chain, sealing onto the previous SHA-256 seal.
  - `kya_verify`: Verify receipt chain integrity from a file or JSON array.
  - `kya_disclose`: Generate selective disclosure for audits (revealing refusals while withholding accepted transactions).
  - `kya_status`: Inspect the current session chain status and head hash.
- **CLI MCP Launcher.** Run directly via `python -m knowyouragenticai_receipts mcp`
  or via the new console script `kya-receipts-mcp`.

---

## [1.2.0] — released to PyPI 2026-10-22

*Written 2026-09-13 and released on 2026-10-22. This heading said
2026-09-13 until 2026-11-10, which is the date the entry was drafted, not
the date anyone could install it. Thirty-nine days apart. A changelog date
is read as "when could I have had this", so it is the upload date, taken
from PyPI itself rather than from the commit that wrote the entry.*

New features, no seal changes. Every 1.0.0 and 1.1.0 chain verifies
byte-for-byte unchanged, which is why this is a minor and not a major: receipts
are meant to outlive the code that wrote them, and that bar is high.

### Added

- **`disclose()` and `check_disclosure()` — hand over the refusals without the
  book.** SPEC §6b. Slicing refusals out of a chain by hand produces a file
  that fails verification, because every seal covers the one before it; handing
  over the whole chain discloses every accepted payment, which for a regulated
  issuer is the reason they could not use it. A disclosure keeps every entry's
  position, outcome, link and seal, and carries the body only for the entries
  being shown. Nothing can be removed from it undetected, and it declares in
  its own text what it is showing, which is what makes a withheld entry's
  outcome checkable at all. `refusals_only()` is the default rule and is
  exported, so a caller can pass their own without guessing what the default
  did; it shows everything whose outcome is not ACCEPTED, which includes the
  sealed policy, because "would exceed the cap" is half a sentence without the
  cap beside it.
- **`what_this_reveals()` — what your own disclosure gives away.** Warns the
  producer, before they send, when a refusal they are showing quotes a withheld
  value. It also catches the leak that is not any single value: a cap refusal
  reading `180000.00 + 95000.00 > 250000.00` states the running total, and that
  total is the withheld payments added up.
- **`assurance()` and the levels `SELF_ATTESTED`, `ANCHORED`,
  `LEDGER_RECORDED`.** SPEC §6a. The level is computed by the verifier from
  what it substantiated and is never read from a field, because a level a
  producer can write down is a level a producer can assert into being. There is
  deliberately no `ledger-enforced` level.
- **`ledger_ref`, an optional receipt field.** Names the ledger record of a
  refusal, so a reader can check it against something the producer did not
  write. It is an address, not evidence: naming one raises no level by itself.
  Present only on receipts that have one, so no existing chain's seal changes.
- **`GENESIS` and `PolicyError` are named in the public API**, which they
  already were in `__all__` and were never written down here.

### Changed

- Nothing that alters a seal. Every 1.0.0 and 1.1.0 chain verifies unchanged,
  and the conformance vectors for them are byte-identical.

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
