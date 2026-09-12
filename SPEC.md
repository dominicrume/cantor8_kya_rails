# KYA Receipt Chain, version 1.3

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
| `outcome` | string | what was decided. `ACCEPTED` / `REFUSED` for an action; other values are permitted — see §4a |
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


### 4a. `outcome` is an open vocabulary, and a verifier MUST NOT reject one it does not know

`ACCEPTED` and `REFUSED` are the values for an action that was attempted. They
are not the only legal values, and this table used to imply they were.

A chain may open by stating the rules it was produced under — one entry,
`outcome` `POLICY`, carrying the cap and the allow-list as text — so that
"the agent did not overspend" can be checked against what "over" meant. The
same format carries audit findings, where an entry is `COVERED`,
`UNCOVERED` or `NOT TESTABLE`.

Therefore:

- A producer MAY use any ASCII `outcome`. It is sealed like every other field.
- A verifier MUST verify **seals**, not vocabulary. An unknown `outcome` is not
  a broken chain and MUST NOT be reported as one. Saying "tampered" about a
  record that is merely newer than your implementation is a false accusation,
  and §3's rule against that applies here too.
- A verifier MAY display an unknown `outcome` verbatim, and SHOULD NOT colour
  it as a failure. `POLICY` is neither a pass nor a failure; painting it red
  tells the reader something was refused when nothing was.

This is a clarification, not a format change: no seal computed under the old
wording differs under this one.

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

**`ledger` is the producer's own words, and a verifier MUST treat it as such.**
It is display text: sealed, therefore unchangeable after the fact, and entirely
unsubstantiated. A producer may write `Canton DevNet, an independent validator
refused this` into a chain that no ledger ever saw, and every seal will still
verify — because the seal covers the bytes, not the truth of them. What a
verifier is allowed to conclude from that string is governed by §6a, and the
answer is: nothing.

## 6a. Assurance level — derived, never declared

A chain that holds tells you nothing was edited. It does not tell you who
decided, and those are answered in the strongest word the format has —
"verified" — unless they are told apart. This section tells them apart.

**The level is computed by the verifier from what it has substantiated. It is
never read from a field.** That distinction is the whole mechanism: a level a
producer could write down is a level a producer could assert into being, and
the format would then record an over-claim instead of preventing it.

| Level | What the verifier has established |
| --- | --- |
| `self-attested` | The seals hold. Nothing about origin. The party who wrote this record is the party it is about. |
| `anchored` | The above, **and** the reader has independently confirmed the head seal and receipt count against an origin the producer does not control (§8). |
| `ledger-recorded` | Both of the above, **and** the reader has found every refusal in the chain recorded on that ledger, with the rule and the time the receipt claims. |

`ledger-recorded` exists because of an asymmetry the first two levels hide. An
accepted payment is corroborated by the thing it did: the money moved, and the
ledger says so. A refusal is corroborated by nothing, because the usual way to
enforce a rule is to abort the transaction, and an aborted transaction leaves
no trace. So in a chain of ten entries, the accepted ones are checkable against
the world and the refused ones are the producer writing about themselves —
which is exactly backwards, since the refusals are the half anybody asks for.

Closing it takes a change at the enforcement layer, not in this format: the
refusal has to be a transaction that SUCCEEDS and records what was refused,
instead of one that aborts. The reference implementation does this in
`KyaMandate.TryCharge`, which writes a `ChargeRefused` contract and moves no
money. A receipt for such a refusal MAY carry `ledger_ref`, the identifier of
that record.

`ledger_ref` is written by the producer and therefore establishes nothing by
itself. It is an address, not evidence. What it changes is that the producer's
claim is now falsifiable: the record is there with that rule at that time, or
it is not. Only the reader who went and looked may raise the level.

Rules:

- A verifier **MUST** report `self-attested` by default, including when
  `ledger`, `approved_by`, `instrument` or any other field says otherwise.
- A verifier **MUST NOT** report `anchored` on the strength of anything inside
  the document. The confirmation has to come from outside it, supplied by the
  reader.
- A verifier **MUST NOT** report `ledger-recorded` on the strength of
  `ledger_ref` being present, however many entries carry one. A verifier that
  cannot reach the ledger **SHOULD** say so beside the verdict and name the
  references it did not check, rather than let a passing seal check imply it
  did.
- A verifier **MUST NOT** report a level it did not establish, and **MUST NOT**
  offer a level the reader could mistake for one it did establish.
- A conforming verifier **SHOULD** show the level beside the verdict, because
  "holds" without it is the ambiguity this section exists to remove.

There is deliberately no `ledger-enforced` level, and `ledger-recorded` is not
a quiet version of one. It says a reader found these refusals written down on a
ledger. Whether the fence would have stopped the payment had the record not
been written is a fact about code, not about records, and no commitment scheme
reaches it — the same limit that stops a proof of solvency establishing that
the assets exist. A receipt records a decision; it does not make one.

The gap that remains at every level, stated so nobody sells past it: an attempt
that was never submitted leaves nothing behind either. `ledger-recorded` makes
a refusal that happened impossible to invent, delete, backdate or reorder. It
does not make a refusal that never reached the ledger appear.

## 6b. Disclosure: handing over part of a chain

A chain is all or nothing. Slicing entries out of it produces a file that
fails verification, because every seal covers the one before it. Handing over
the whole chain discloses everything in it, which for a regulated producer is
the reason they cannot hand it over at all.

A **disclosure** is a document carrying every entry's `n`, `outcome`, `prev`
and `seal`, and the full body of only some of them.

- `n`, `outcome`, `prev` and `seal` **MUST NOT** be withheld for any entry. If
  an entry could be hidden entirely, "here are my three refusals" would be
  indistinguishable from a chain that had thirty.
- A withheld entry **MUST** carry `"withheld": true` in place of its body, so
  that absence is a statement rather than a gap.
- A document **SHOULD** declare in `disclosing` the rule it applied. A
  verifier **MUST** check the document against its own declared rule: one
  claiming to show every refusal that also withholds one is refused.

A verifier establishes that nothing was removed, that positions run 1..n with
every `prev` matching the seal before it, and that each shown body re-seals to
the seal printed beside it.

It does **not** establish a withheld entry's outcome. The body is absent, so
the label cannot be recomputed. The declared rule is what makes it checkable
in the ordinary case, and nothing else does.

**Withholding a body does not withhold its contents.** A refusal reading
`would exceed the cap: 10.00 + 999.00 > 100.00` states the running total, and
the 10.00 is an accepted payment withheld two entries above. This cannot be
redacted, because editing a shown body breaks its seal. A producer SHOULD be
shown what a disclosure gives away before sending it.

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

Version **1.3**. Changes that alter any seal require a new MAJOR version; none of 1.1, 1.2 or 1.3 alters one.

1.0 -> 1.1 added §4a, which states that `outcome` is an open vocabulary and that a verifier must check seals rather than vocabulary. Every 1.0 seal is unchanged and every 1.0 chain still verifies, so this is a minor version: it tells a 1.0 implementer that they may see values they do not recognise, and that rejecting one would be a false accusation rather than a finding.


1.2 -> 1.3 added the `ledger-recorded` level to §6a, and the optional `ledger_ref` field a receipt may carry to name the ledger record of a refusal. This exists because of a hole the first two levels hid: an accepted payment is corroborated by the money moving, and a refusal enforced by an aborting assertion is corroborated by nothing, so the half of the chain anyone actually asks for was the half backed only by the producer's word. Closing it is a change at the enforcement layer, not in this format, and the format's part is to carry an address and refuse to treat it as evidence. Vector 20 makes the field binding: it appears only on receipts that have one, so an implementation with a fixed field list seals it differently. Every 1.0, 1.1 and 1.2 seal is unchanged, and a chain with no ledger references is byte-identical to what 1.2 produced.

1.1 -> 1.2 added §6a: the assurance level is derived by the verifier from what it substantiated, never read from a field, and there is deliberately no `ledger-enforced` level. Vector 18 makes it binding -- a receipt whose every field claims an independent decider, sealed correctly, that must still verify as `self-attested`. Every 1.0 and 1.1 seal is unchanged.