#!/usr/bin/env python3
"""Generate tests/vectors.json from the reference implementation.

The vectors are the authority for the spec, so they are produced by the code
that the spec describes rather than typed by hand. Re-run after any deliberate
format change; a change that alters a seal is a new major version.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "step-2-agent"))
from kya_chain import canonical, seal, Chain

def body(**kw):
    return kw

cases = []

# 1. The smallest possible thing: one receipt against GENESIS.
b1 = body(n=1, what="first", amount="1.0", currency="CC", instrument="Amulet",
          payee="Alice", rule="allowed", outcome="ACCEPTED",
          approved_by="owner+agent", ledger="TESTVECTOR",
          at="2026-01-01T00:00:00Z", prev="GENESIS")
cases.append({
    "name": "genesis-single",
    "kind": "seal",
    "why": "the base case: prev is the literal string GENESIS",
    "body": b1, "prev": "GENESIS",
    "canonical": canonical(b1), "seal": seal(b1, "GENESIS"),
})

# 2. Key ordering must be by code point, not insertion order. Same object,
#    scrambled input order, must produce identical bytes.
scrambled = {k: b1[k] for k in reversed(list(b1.keys()))}
cases.append({
    "name": "key-order-independence",
    "kind": "seal",
    "why": "keys sorted by code point: input order must not affect the seal",
    "body": scrambled, "prev": "GENESIS",
    "canonical": canonical(scrambled), "seal": seal(scrambled, "GENESIS"),
})

# 3. A REFUSED receipt seals exactly like an accepted one. Refusals are
#    first-class; nothing about the format treats them differently.
b3 = dict(b1, n=2, what="over the cap", outcome="REFUSED",
          rule="charge would exceed the cap", prev=cases[0]["seal"])
cases.append({
    "name": "refusal-seals-identically",
    "kind": "seal",
    "why": "a refused attempt is a receipt, not an absence of one",
    "body": b3, "prev": cases[0]["seal"],
    "canonical": canonical(b3), "seal": seal(b3, cases[0]["seal"]),
})

# 4. Decimal-as-string. 0.1 + 0.2 is why.
b4 = dict(b1, amount="0.30000000000000004")
cases.append({
    "name": "amount-is-a-string",
    "kind": "seal",
    "why": "a float here would not survive a Python/JS round trip byte-identical",
    "body": b4, "prev": "GENESIS",
    "canonical": canonical(b4), "seal": seal(b4, "GENESIS"),
})

# 5. A real chain, produced by the reference Chain class.
#
#    NOTE: these party names are frozen. They do not match the demo's current
#    story, and that is correct -- the vector CONTENT is arbitrary, but its
#    BYTES are the contract. Renaming a payee here changes every seal below it,
#    which per SPEC.md section 9 is a new major version of the format and
#    breaks every implementation that already conforms to 1.0. Change these
#    only when you intend exactly that.
ch = Chain()
ch.stamp("Settle customer leg", 2.0, "VerifiedCustomer", "cap 5.0, spent 2.0",
         "ACCEPTED", "owner+agent", "TESTVECTOR")
ch.stamp("Settle liquidity leg", 1.5, "LiquidityPartner", "cap 5.0, spent 3.5",
         "ACCEPTED", "owner+agent", "TESTVECTOR")
ch.stamp("ATTACK overspend", 3.0, "VerifiedCustomer",
         "charge would exceed the cap", "REFUSED", "owner+agent", "TESTVECTOR")
ch.stamp("ATTACK unverified payee", 1.0, "UnverifiedWallet",
         "payee is not on the allow-list", "REFUSED", "owner+agent", "TESTVECTOR")
good = [dict(r) for r in ch.receipts]
for r in good:                      # fixed timestamp: vectors must be stable
    r["at"] = "2026-01-01T00:00:00Z"
prev = "GENESIS"
for r in good:                      # reseal against the fixed timestamp
    r["prev"] = prev
    b = {k: v for k, v in r.items() if k != "seal"}
    r["seal"] = seal(b, prev)
    prev = r["seal"]
cases.append({
    "name": "chain-of-four-verifies",
    "kind": "chain", "why": "two accepted, two refused, all four seals hold",
    "receipts": good, "verdict": "PASS",
})

# 6. Tamper receipt 2. Everything from 2 onward must break, 1 must survive.
tampered = [dict(r) for r in good]
tampered[1]["amount"] = "3500.0"
cases.append({
    "name": "tamper-cascades-from-two",
    "kind": "chain",
    "why": "editing one amount breaks that seal and every seal after it",
    "receipts": tampered, "verdict": "FAIL", "fail_at": 2,
})

# 7. Re-seal the tampered receipt so it is internally valid. The BROKEN LINK
#    to the next receipt's prev is what catches it. A forger who recomputes one
#    seal must recompute all of them.
resealed = [dict(r) for r in good]
resealed[1]["amount"] = "3500.0"
b = {k: v for k, v in resealed[1].items() if k != "seal"}
resealed[1]["seal"] = seal(b, resealed[1]["prev"])
cases.append({
    "name": "resealed-tamper-still-caught",
    "kind": "chain",
    "why": "receipt 2 now self-consistent, but receipt 3's prev no longer matches",
    "receipts": resealed, "verdict": "FAIL", "fail_at": 3,
})

# 7b. Escapes. A third implementation written from the spec alone had to infer
#     these from RFC 8259 because section 4 did not state them. It guessed
#     right; the next one might not. This vector removes the guess.
b7 = body(n=1, what='He said "change of account" then left',
          amount="1.0", currency="CC", instrument="Amulet",
          payee="Alice\tBob", rule="path C:\\ops\\float",
          outcome="ACCEPTED", approved_by="owner+agent", ledger="TESTVECTOR",
          at="2026-01-01T00:00:00Z", prev="GENESIS")
cases.append({
    "name": "escapes-quote-backslash-tab",
    "kind": "seal",
    "why": "quote, backslash and tab must escape identically in every language",
    "body": b7, "prev": "GENESIS",
    "canonical": canonical(b7), "seal": seal(b7, "GENESIS"),
})

# 7c. Empty strings. A field present but empty is not the same as absent, and
#     an implementation that drops empties would produce a different seal.
b7c = body(n=1, what="", amount="0.0", currency="", instrument="",
           payee="", rule="", outcome="REFUSED", approved_by="",
           ledger="TESTVECTOR", at="2026-01-01T00:00:00Z", prev="GENESIS")
cases.append({
    "name": "empty-strings-are-not-absent",
    "kind": "seal",
    "why": "an empty field still contributes its key and its quotes to the seal",
    "body": b7c, "prev": "GENESIS",
    "canonical": canonical(b7c), "seal": seal(b7c, "GENESIS"),
})

# 7d. A maximal field. Long values must not be truncated, chunked or
#     normalised by any implementation.
b7d = body(n=1, what="x" * 4096, amount="1.0", currency="CC",
           instrument="Amulet", payee="A", rule="r", outcome="ACCEPTED",
           approved_by="o", ledger="TESTVECTOR",
           at="2026-01-01T00:00:00Z", prev="GENESIS")
cases.append({
    "name": "maximal-field-4096-chars",
    "kind": "seal",
    "why": "no implementation may truncate or chunk a long field",
    "body": b7d, "prev": "GENESIS",
    "canonical": canonical(b7d), "seal": seal(b7d, "GENESIS"),
})

# 7e. A deep chain. Verification is linear and must not stack-overflow, and
#     the 200th seal must be reproducible from the 1st.
deep = Chain()
for i in range(200):
    deep.stamp("payout %d" % i, 0.01, "R", "within limits", "ACCEPTED",
               "o", "TESTVECTOR")
deepr = [dict(r) for r in deep.receipts]
prev = "GENESIS"
for r in deepr:
    r["at"] = "2026-01-01T00:00:00Z"
    r["prev"] = prev
    r["seal"] = seal({k: v for k, v in r.items() if k != "seal"}, prev)
    prev = r["seal"]
cases.append({
    "name": "deep-chain-200-receipts",
    "kind": "chain", "why": "verification is linear and must not blow the stack",
    "receipts": deepr, "verdict": "PASS",
})

# 7f. A prev that points at a real seal, but the WRONG one. Every seal is
#     individually valid; only the link is broken. An implementation that
#     checks seals without checking prev passes this and must not.
mis = [dict(r) for r in good]
mis[2]["prev"] = mis[0]["prev"]           # points back at GENESIS
mis[2]["seal"] = seal({k: v for k, v in mis[2].items() if k != "seal"},
                      mis[2]["prev"])
cases.append({
    "name": "misaligned-prev-link",
    "kind": "chain",
    "why": "receipt 3 is internally valid but links to the wrong predecessor",
    "receipts": mis, "verdict": "FAIL", "fail_at": 3,
})

# 8. Non-ASCII MUST be refused at sealing time, naming the field.
cases.append({
    "name": "reject-non-ascii-currency-symbol",
    "kind": "reject",
    "why": "Python escapes it, JSON.stringify does not: the chain would verify "
           "in Python and go red in the browser",
    "body": dict(b1, what="Pay supplier ₦500"),
    "offending_field": "what",
})
cases.append({
    "name": "reject-non-ascii-smart-quote",
    "kind": "reject",
    "why": "a curly apostrophe pasted from a document is the realistic case",
    "body": dict(b1, rule="the desk’s limit"),
    "offending_field": "rule",
})

# Two holes found by tests/conformance_any.py, which grades an implementation
# through a pipe and made it cheap to ask "which mistakes do the vectors NOT
# catch?". Both of these let a wrong implementation pass all fourteen.

# 1. Section 4 writes out the escape table for characters above 0x7E so that
#    implementations agree on what they WOULD have produced, even though such
#    a receipt is rejected before sealing. Nothing tested it, so an
#    implementation emitting raw UTF-8 -- which JavaScript's JSON.stringify
#    does by default, and Go's encoding/json does differently again -- passed.
#    A canonical-only case, because sealing this body is not a legal operation.
b_esc = body(n=1, what="Pay supplier \u20a6500 \u2014 the desk\u2019s limit",
             amount="1.0", currency="CC", instrument="Amulet", payee="Alice",
             rule="allowed", outcome="ACCEPTED", approved_by="owner+agent",
             ledger="TESTVECTOR", at="2026-01-01T00:00:00Z", prev="GENESIS")
cases.append({
    "name": "canonical-escapes-non-ascii",
    "kind": "canonical",
    "why": "a naira sign, an em dash and a curly apostrophe must each become "
           "\\uXXXX. This body would be REJECTED before sealing -- the case "
           "exists so implementations agree on the canonical form anyway",
    "body": b_esc,
    "canonical": canonical(b_esc),
})

# 2. misaligned-prev-link does not test what its name says. Its receipt 3 has a
#    wrong prev AND a seal that does not fit, so the seal check alone catches
#    it, and an implementation that never compares the prev FIELD passed.
#    Here receipt 3's seal is computed over the RUNNING prev while its prev
#    field lies, so only comparing that field catches it.
def _chain(rows):
    out, prev = [], "GENESIS"
    for i, (what, outcome, rule) in enumerate(rows, 1):
        r = body(n=i, what=what, amount="1.0", currency="CC", instrument="Amulet",
                 payee="Alice", rule=rule, outcome=outcome,
                 approved_by="owner+agent", ledger="TESTVECTOR",
                 at="2026-01-01T00:00:0%dZ" % i, prev=prev)
        r["seal"] = seal(r, prev)
        prev = r["seal"]
        out.append(r)
    return out

liar = _chain([("first", "ACCEPTED", "allowed"),
               ("second", "ACCEPTED", "allowed"),
               ("third", "REFUSED", "over the cap"),
               ("fourth", "ACCEPTED", "allowed")])
# Rewrite receipt 3's prev to a lie, then re-seal it over the TRUE running prev
# so the seal still fits. Receipt 4 keeps chaining from receipt 3's new seal,
# so the only thing wrong in the whole file is one prev field.
running_prev_at_3 = liar[1]["seal"]
liar[2]["prev"] = "GENESIS"
liar[2]["seal"] = seal({k: v for k, v in liar[2].items() if k != "seal"},
                       running_prev_at_3)
liar[3]["prev"] = liar[2]["seal"]
liar[3]["seal"] = seal({k: v for k, v in liar[3].items() if k != "seal"},
                       liar[2]["seal"])
cases.append({
    "name": "prev-field-lies-while-seal-fits",
    "kind": "chain",
    "why": "receipt 3's seal is computed over the true running prev, so the "
           "seal check passes; only comparing the prev FIELD catches it. "
           "SPEC.md section 7 requires both and nothing tested the second",
    "receipts": liar,
    "verdict": "FAIL", "fail_at": 3,
})

# ---------------------------------------------------------------- spec 1.1
# 17. `outcome` is an open vocabulary (SPEC 4a). An implementation that
#     hard-codes ACCEPTED and REFUSED calls a valid POLICY record tampered,
#     which is the one accusation this format must never make by accident.
b17 = body(n=1, what="policy in force", amount="100.00", currency="USD",
           instrument="policy", payee="acme",
           rule="cap=100.00 USD; allow=[acme]", outcome="POLICY",
           approved_by="the principal, before the agent ran",
           ledger="self-attested (no ledger)",
           at="2026-01-01T00:00:00Z", prev="GENESIS")
cases.append({
    "name": "unknown-outcome-is-not-tampering",
    "kind": "seal",
    "why": "outcome is an open vocabulary (SPEC 4a). A verifier that rejects "
           "POLICY -- or any value it has not seen -- calls a valid record "
           "tampered, which is the accusation this format must never make by "
           "accident. Seal it like any other field.",
    "body": b17, "prev": "GENESIS",
    "canonical": canonical(b17), "seal": seal(b17, "GENESIS"),
})

# ---------------------------------------------------------------- spec 1.2
# 18. The assurance level is DERIVED by the verifier, never read from the
#     document. Every field here claims an independent ledger decided it. No
#     ledger ever saw it. The seal is honest, so the chain holds, and the
#     level must still come out self-attested.
b18 = body(n=1, what="payout to a supplier", amount="10.00", currency="USD",
           instrument="settled on Canton DevNet, block 4417213", payee="acme",
           rule="an independent Canton validator authorised this under the "
                "mandate",
           outcome="ACCEPTED",
           approved_by="Canton DevNet consensus, not the applicant",
           ledger="Canton DevNet (real Canton) -- an independent party "
                  "decided this",
           at="2026-01-01T00:00:00Z", prev="GENESIS")
cases.append({
    "name": "claims-independence-but-is-self-attested",
    "kind": "seal",
    "why": "SPEC 6a. Every field in this receipt asserts that an independent "
           "ledger decided the outcome. No ledger ever saw it -- it was "
           "written by hand for this vector. The seal is correct, so the "
           "chain HOLDS, and a conforming verifier must still report "
           "assurance self-attested: the level is derived from what the "
           "verifier substantiated, never read from the document. A level a "
           "producer can write down is a level a producer can assert into "
           "being.",
    "body": b18, "prev": "GENESIS",
    "seal": seal(b18, "GENESIS"), "canonical": canonical(b18),
    "assurance": "self-attested",
})

# 19. A refusal exactly as it appears inside a SPEC 6b disclosure, chained
#     from the policy entry it broke, so an implementation that verifies this
#     vector can verify a disclosure's shown entries.
b19 = body(n=2, what="refund a customer", amount="999.00", currency="USD",
           instrument="policy-governed action", payee="acme",
           rule="would exceed the cap: 0 + 999.00 > 100.00 USD",
           outcome="REFUSED",
           approved_by="the mandate, checked before the call",
           ledger="self-attested (the operator's own process refused)",
           at="2026-01-01T00:00:01Z", prev=cases[-2]["seal"])
cases.append({
    "name": "disclosure-shown-entries-reseal",
    "kind": "seal",
    "why": "SPEC 6b. The body of an entry shown inside a disclosure must "
           "re-seal to the seal printed beside it, computed by the reader. "
           "This is that refusal's body and seal, taken from a chain whose "
           "first entry is the policy it broke. An implementation that can "
           "verify this vector can verify a disclosure's shown entries.",
    "body": b19, "prev": cases[-2]["seal"],
    "seal": seal(b19, cases[-2]["seal"]), "canonical": canonical(b19),
})

# ---------------------------------------------------------------- spec 1.3
# 20. `ledger_ref` is optional and present only where there is one, so an
#     implementation must canonicalise the keys it FINDS rather than a fixed
#     list. A hardcoded field order seals this differently and its chains
#     stop interoperating. Note the field establishes nothing on its own.
b20 = body(n=1, what="settle a merchant payment", amount="95000.00",
           payee="merchant-4471", currency="USD",
           instrument="policy-governed action",
           rule="charge would exceed the cap", outcome="REFUSED",
           approved_by="the mandate, checked before the call",
           ledger="Canton", at="2026-01-01T00:00:01Z", prev="GENESIS",
           ledger_ref="00a1b2c3d4e5f6a7b8c9d0e1f2::ChargeRefused")
cases.append({
    "name": "receipt-carrying-a-ledger-reference",
    "kind": "seal",
    "why": "SPEC 6a. `ledger_ref` is optional and appears only on receipts "
           "that have one, so an implementation must canonicalise whatever "
           "keys are present rather than a fixed list. An implementation "
           "with a hardcoded field order seals this differently and its "
           "chains will not interoperate. The field establishes nothing by "
           "itself: this vector is about bytes, and a verifier must still "
           "report self-attested.",
    "body": b20, "prev": "GENESIS",
    "seal": seal(b20, "GENESIS"), "canonical": canonical(b20),
})


out = {
    "spec": "KYA Receipt Chain",
    "spec_version": "1.3",
    "note": "Generated by tests/make_vectors.py. These vectors are the "
            "authority: where SPEC.md and a vector disagree, the vector "
            "wins. spec_version 1.1 adds vector 17: an outcome outside "
            "the two an implementation is likely to have hard-coded. No "
            "1.0 seal changed. spec_version 1.2 adds vector 18: a "
            "receipt whose every field claims an independent decider, "
            "which must still verify as self-attested. Vector 19 "
            "carries a refusal as it appears inside a SPEC 6b "
            "disclosure, so shown entries are checkable by any "
            "implementation. spec_version 1.3 adds vector 20: a receipt "
            "carrying the optional ledger_ref field, which is present "
            "only when there is one, so implementations must "
            "canonicalise the keys they find.",
    "cases": cases,
}
path = os.path.join(HERE, "vectors.json")
with open(path, "w") as f:
    json.dump(out, f, indent=2, ensure_ascii=True)
    f.write("\n")
print("wrote %s: %d cases (%s)" % (
    path, len(cases), ", ".join(sorted({c["kind"] for c in cases}))))
