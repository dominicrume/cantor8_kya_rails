# Forum post: our own topic

**Where:** https://forum.canton.network/ — App Development category, tags
`discuss` and `feedback`. A NEW topic, not a reply.

**When:** a day or two after the OpenZeppelin reply (post #8, 2026-09-08).
Two posts in one afternoon reads as promotion.

**Links verified 2026-09-08:** all four resolve 200; PyPI 1.0.0, MIT, no
dependencies.

**Title:** Proving an agent *didn't* overspend — a receipt format anyone can check

---

I've been building a spend-limited agent wallet on Canton, and the part that
turned out to matter isn't the spending — it's the refusals.

Every attempt the agent makes, allowed or refused, becomes one hash-chained
receipt: what was tried, what the ledger decided, and which rule decided it. The
limits are `assertMsg` fences in the Daml, not checks in application code — so a
refusal is the ledger's, not my app's claim about itself.

The useful part is what you can hand someone afterwards. Drop the chain on a
page and it verifies with nothing installed, no account, no node. Edit one
receipt and every seal after it breaks.

- Check a chain: https://dominicrume.github.io/cantor8_kya_rails/
- Spec + 16 conformance vectors: https://github.com/dominicrume/cantor8_kya_rails/blob/main/SPEC.md
- `pip install knowyouragenticai-receipts` — MIT, zero dependencies

Three independent implementations (Python, JS, Go) agree byte-for-byte on the
canonicalisation, and two of the vectors exist because I asked which *wrong*
implementations still passed — two did.

Genuinely want to know: is "prove the agent didn't do X" something others need,
or is it just my problem?

---

## Why it is written this way

It leads with the **refusal**, not the wallet. Nobody needs another wallet, and
proving a negative about an agent is the part nobody else in this forum is
claiming.

It does not name the project in the first line, so it does not read as an
announcement.

It ends with a real question. A topic with no question gets five views and no
replies — which is what happened to Halborn's audit case study in Outreach, and
they are an established firm. The reply is the point; the post is only the
thing that earns one.
