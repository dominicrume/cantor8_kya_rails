# KYA Receipt Chain, version 1.0

A wire format for **tamper-evident receipts of agent actions, including the
actions that were refused.**

Status: stable. Reference implementations: [`kya_chain.py`](step-2-agent/kya_chain.py)
(Python, stdlib only) and [`verifier.html`](step-3-verify/verifier.html)
(browser, no dependencies). Conformance vectors: [`tests/vectors.json`](tests/vectors.json).

This document is written so that a third implementation — Go, Rust, TypeScript,
Java — can be produced from the text alone and proved correct against the
vectors. If the text and the reference implementation disagree, **the vectors
are the authority.**

---

## 1. Why refusals are in scope

Most systems log what succeeded. A log answers *what happened*. It cannot
answer *what was attempted and stopped*, which is the question asked after an
incident and the question asked by an auditor.

An agent that is refused has still acted. This format records the attempt, the
outcome, and **the rule that decided it**, with equal weight whether the answer
was yes or no.

## 2. The receipt

A receipt is a JSON object. These fields are REQUIRED:

| Field | Type | Meaning |
| --- | --- | --- |
| `n` | integer | 1-based position in the chain. MUST increase by exactly 1. |
| `what` | string | human-readable description of the attempt |
| `amount` | string | decimal as a **string**, never a JSON number — see §4 |
| `currency` | string | ASCII currency or instrument code, e.g. `CC`, `USD` |
| `instrument` | string | what was actually moved, or a statement that nothing was |
| `payee` | string | the counterparty the action was directed at |
| `rule` | string | the rule that allowed or refused it, in the decider's own words |
| `outcome` | string | `ACCEPTED` or `REFUSED` |
| `approved_by` | string | the authority the action was taken under |
| `ledger` | string | **which system decided.** See §6. |
| `at` | string | UTC timestamp, `YYYY-MM-DDTHH:MM:SSZ` |
| `prev` | string | the previous receipt's `seal`, or `GENESIS` for the first |
| `seal` | string | lowercase hex sha256 — see §3 |

Implementations MAY add fields. Any added field is part of the sealed body and
therefore changes the seal, so an implementation that adds fields is no longer
chain-compatible with one that does not. Add fields only when you control both
ends.

## 3. The seal

```
body  = the receipt object with the "seal" key removed
seal  = sha256_hex( canonical(body) + prev )
```

`+` is string concatenation. `prev` is the previous receipt's `seal`, or the
literal ASCII string `GENESIS` for the first receipt in a chain. `sha256_hex`
is lowercase hexadecimal, 64 characters.

The seal is computed over the body **and** the previous seal. Changing any
field of receipt *k* invalidates receipt *k* and every receipt after it.

## 4. Canonical form

`canonical(obj)` is JSON with:

- keys sorted by Unicode code point, ascending, at every level of nesting
- no whitespace: the item separator is `,` and the key separator is `:`
- non-ASCII characters escaped as `\uXXXX` (lowercase hex)
- no trailing newline

Within a string, these escapes are required — they are RFC 8259's, and they are
written out here because a third implementation was produced from this document
and had to infer them:

| character | escape |
| --- | --- |
| `"` | `\"` |
| `\` | `\\` |
| newline, carriage return, tab | `\n`, `\r`, `\t` |
| backspace, form feed | `\b`, `\f` |
| any other code point below `0x20` | `\u00XX`, lowercase hex |
| any code point above `0x7E` | `\uXXXX`, lowercase hex; above the BMP, a surrogate pair |

Forward slash is **not** escaped. Code point above `0x7E` is a rejection case in
practice — see section 5 — but the escape is specified so that implementations
agree on what they would have produced.

In Python this is exactly:

```python
json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
```

JavaScript's `JSON.stringify` does **not** sort keys and does **not** escape
non-ASCII, so it MUST NOT be used directly. See §5.

### Why amounts are strings

`0.1 + 0.2` is not `0.3` in IEEE-754, and JSON number formatting differs
between languages: Python emits `1e-07`, JavaScript emits `1e-7`. A decimal
carried as a JSON number is not guaranteed to survive a round trip through two
languages with the same bytes. Carry it as a string and it always does.

## 5. ASCII is mandatory in hashed fields

**Every string in the sealed body MUST be ASCII (code points 0–127).**

This is not stylistic. Python escapes non-ASCII to `\uXXXX`; JavaScript's
`JSON.stringify` emits the raw character. Same receipt, different bytes,
different hash. A chain containing one currency symbol verifies in Python and
fails in the browser:

```
PY: {"amount":"40.0","n":1,"what":"Pay supplier \u20a6500"}  -> 89e828df...
JS: {"amount":"40.0","n":1,"what":"Pay supplier ₦500"}        -> 71e44b13...
```

(Those are seals — `sha256(canonical + "GENESIS")` — not hashes of the line
above them. The two lines used to be printed identically, which made an
illustration of "different bytes" show the same bytes.)

A conforming implementation MUST refuse to seal a receipt containing a
non-ASCII character in any field, and MUST report which field. Failing at the
point of sealing is required: a chain that is already sealed and unverifiable
cannot be repaired.

Currency **codes** (`CC`, `NGN`, `GBP`) go in the receipt. Currency **symbols**
(`₵`, `₦`, `£`) are rendered at display time and never hashed.

## 6. The `ledger` field

`ledger` names the system that decided the outcome. A verifier displays it, and
because it is inside the seal it cannot be changed after the fact.

Where an outcome was produced by a simulation rather than the real system, the
value MUST say so. The reference implementation uses
`MOCKED (mirrors KyaMandate.daml; real rail = --devnet)` against a simulator
and `DevNet (real Canton, package 6d13f9948206)` against the live ledger.

A receipt that does not name its decider is not a receipt. It is a claim.

## 7. Verification

```
prev = "GENESIS"
for each receipt r in order:
    if r.prev != prev:                       FAIL at r.n
    body = r without "seal"
    if sha256_hex(canonical(body) + prev) != r.seal:   FAIL at r.n
    prev = r.seal
PASS
```

A verifier MUST report the position of the **first** failing receipt. Every
receipt at or after that position is unverifiable, and a verifier SHOULD show
them as such — a tamper at position 2 of 6 breaks five receipts, not one.

Verification requires no network, no key material, and no trust in the
producer. This is the point: the reader recomputes rather than believing.

## 8. What this format does not do

Stated plainly, because a security format that overstates itself is worse than
none:

- **It is not signed.** It proves internal consistency, not origin. Anyone can
  produce a valid chain saying anything, and a forged one verifies green in
  every implementation here — that is a property of the format, not a bug in
  the verifiers.

  The reference application now binds it the way this paragraph has always
  recommended: the principal publishes the final seal and the receipt count as
  a `ChainAnchor` contract on Canton (`step-1-mandate/daml/KyaAnchor.daml`,
  `tests/devnet_anchor.py`). Forging a chain then also means forging a contract
  signed by a party whose key you do not have. **The count is published
  alongside the seal on purpose**: a chain truncated after receipt 3 still
  verifies, and its head is a real seal — the count is what catches it.

  This is a binding, not a signature: the format is unchanged, every seal is
  unchanged, and all 16 conformance vectors still hold. An unanchored chain is
  still a valid chain; it just carries no claim about where it came from.
- **It does not prove the rule was enforced.** `rule` is a string. The
  guarantee that a limit was actually applied comes from wherever the decision
  was made — in the reference application, assertions in a Daml choice body.
  This format records the decision; it does not make it.
- **It does not prevent deletion of the whole chain.** It makes *editing*
  detectable, not *discarding*. Publish the final seal somewhere you do not
  control if that matters.

## 9. Conformance

An implementation conforms if it reproduces every seal in
[`tests/vectors.json`](tests/vectors.json) and reaches the stated verdict on
each chain, including the failure positions and the ASCII rejections.

```bash
python3 tests/conformance.py      # reference, Python
node    tests/conformance.js      # reference, JavaScript
```

Adding an implementation in another language is the most useful contribution
you can make to this spec. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

Version 1.0. Changes that alter any seal require a new major version.
