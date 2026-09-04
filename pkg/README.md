# kya-receipt-chain

**A tamper-evident receipt chain that records refusals, not only successes.**
Zero dependencies.

Most audit logs record what happened. The artefact anyone checking your system
actually asks for is the opposite: **what was attempted and stopped.** A log
that only contains successes cannot answer "did you try to pay someone you
shouldn't have?" — and it is written by the party being checked, so it can be
edited afterwards.

This is a small format that fixes the second problem and makes the first one
natural. Every entry is sealed to the one before it, so editing any receipt
breaks every seal after it.

```bash
pip install kya-receipt-chain
```

```python
from kya_receipt_chain import Chain

chain = Chain()
chain.stamp(what="payout to supplier", amount="10.0", payee="Chidi",
            rule="inside the cap", outcome="ACCEPTED",
            approved_by="principal", ledger="production")
chain.stamp(what="payout to an unknown account", amount="5.0", payee="Stranger",
            rule="payee is not on the allow-list", outcome="REFUSED",
            approved_by="principal", ledger="production")

chain.verify()      # (True, 0)
chain.head          # the one value that stands for the whole chain
```

Change any field of any receipt and:

```python
chain.receipts[0]["amount"] = "9999.0"
chain.verify()      # (False, 1)  -- and every seal after it is broken too
```

## Prove this build implements the specification

The conformance vectors ship inside the package, so this works offline:

```bash
python -m kya_receipt_chain
# CONFORMANT: 16/16 cases. This build implements the specification.
```

## The format, in full

`seal = sha256(canonical(body) + prev)`, where `canonical` is JSON with keys
sorted by code point at every level, `,` and `:` as separators with no spaces,
and non-ASCII escaped to `\uXXXX`. `prev` is the previous receipt's seal, or the
literal string `GENESIS`.

That is the whole thing. It is about twenty lines in any language, and
[the specification](https://github.com/dominicrume/cantor8_kya_rails/blob/main/SPEC.md)
is one page. There are implementations in Python, JavaScript and Go, and a
grader that will tell you in one command whether yours is right:

```bash
python3 tests/conformance_any.py -- ./your-implementation
```

**A new implementation is the most valuable contribution this format can
receive.** Two of the sixteen vectors exist because someone asked which *wrong*
implementations still passed — and two did: one emitting raw UTF-8 where the
spec requires `\uXXXX`, and one that checked every seal but never compared the
`prev` link.

## What this does not do

A format that oversells itself is worse than none, so:

- **It is not signed.** It proves internal consistency, not origin. Anyone can
  produce a valid chain saying anything, and a forged one verifies. Bind the
  final seal to something you do not control if origin matters — the reference
  application publishes it as a contract on a Canton ledger.
- **It does not prove a rule was enforced.** `rule` is a string. The guarantee
  comes from wherever the decision was actually made.
- **It makes editing detectable, not deletion.** Publish the head somewhere else
  if discarding the whole chain matters.

## Why amounts are strings

A float that survives one language's JSON encoder is not a float that survives
all of them. The seal computed over `"1.0"` is not the seal computed over `"1"`,
and a chain that verifies only on the machine that wrote it is not a chain.

## Why no dependencies

The whole format is `json` and `hashlib`. A dependency here would be a
dependency in everyone's audit trail.

---

MIT. Built as part of [KYA Rails](https://github.com/dominicrume/cantor8_kya_rails),
a spend-limited wallet for AI agents on Canton.
