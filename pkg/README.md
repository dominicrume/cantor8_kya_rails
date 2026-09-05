# knowyouragenticai-receipts

**Let an AI agent pay, and prove what it couldn't.**

A tamper-evident record of every payment attempt — including the refusals — for
agent-operated wallets. Built for Canton Network; works anywhere. Zero
dependencies.

---

If you let software spend money on your behalf, someone will eventually ask you
a question your logs cannot answer: **"what did it try to do that you stopped?"**

Ordinary logs record what succeeded. That is the wrong half. The half that
matters to an auditor, a regulator, or the person whose money it was, is the
attempt that was refused — and whether anyone could have quietly removed it
afterwards.

This keeps both. Every attempt gets an entry, allowed or refused, and each entry
is sealed to the one before it. Change any entry and every seal after it breaks.

```bash
pip install knowyouragenticai-receipts
```

```python
from knowyouragenticai_receipts import Chain

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
python -m knowyouragenticai_receipts
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
