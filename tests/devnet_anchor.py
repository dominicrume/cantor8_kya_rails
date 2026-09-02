#!/usr/bin/env python3
"""Publish a receipt chain's head on Canton, and check one against the ledger.

SPEC.md section 8, stated plainly since the day the format was written: the
chain "is not signed. It proves internal consistency, not origin. Anyone can
produce a valid chain saying anything." That is the last hole in the evidence
-- hand someone a wholly fabricated receipts.js and the verifier goes green,
because every seal in it really does follow from the one before.

Section 8 also names the fix: bind it to a ledger transaction. This does that.
The principal publishes the final seal and the receipt count as a ChainAnchor
on Canton. Forging a chain now also means forging a contract signed by a party
whose key you do not have.

    python3 tests/devnet_anchor.py            publish the current chain's head
    python3 tests/devnet_anchor.py --check    does the ledger agree with it?

What this does NOT prove, so nobody overstates it: that the receipts are TRUE.
A principal can anchor a chain of lies. What they cannot do is anchor one and
later swap it for a different one, or deny having published it.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "step-2-agent"))
RECEIPTS = os.path.join(ROOT, "step-3-verify", "receipts.js")


def chain_head():
    """(final seal, count, ledger label) from the receipts the demo wrote."""
    src = open(RECEIPTS).read()
    receipts = json.loads(src[src.index("["): src.rindex("]") + 1])
    if not receipts:
        return None, 0, ""
    return receipts[-1]["seal"], len(receipts), receipts[-1]["ledger"]


def template(dn):
    return "%s:KyaAnchor:ChainAnchor" % dn.ANCHOR_PKG


def publish(dn, seal, count, ledger):
    ok, r = dn._submit([{"CreateCommand": {
        "templateId": template(dn),
        # Daml Int64 crosses the JSON Ledger API as a STRING, not a number.
        # Sending 6 gets HTTP 500 "Expected ujson.Str (data: 6)", which does
        # not mention types, fields, or JSON. Same reason SPEC.md makes amounts
        # strings: a number that survives one encoder is not a number that
        # survives all of them.
        "createArguments": {"principal": dn.PARTY["owner"], "seal": seal,
                            "receipts": str(count), "ledger": ledger}}}],
        act_as=dn.PARTY["owner"])
    return ok, r


def anchors(dn, c8lab):
    """Every ChainAnchor the principal can see, newest first."""
    body = {"filter": {"filtersByParty": {dn.PARTY["owner"]: {"cumulative": [
                {"identifierFilter": {"TemplateFilter": {"value": {
                    "templateId": "#kya-rails-mandate:KyaAnchor:ChainAnchor",
                    "includeCreatedEventBlob": False}}}}]}}},
            "verbose": True, "activeAtOffset": c8lab.ledger_end(sub=dn.USER)}
    out = []
    for item in c8lab.call("/v2/state/active-contracts", body, sub=dn.USER):
        ev = item.get("contractEntry", {}).get("JsActiveContract", {}).get("createdEvent", {})
        if ev.get("createArgument"):
            out.append(ev["createArgument"])
    return out


def do_check(dn, c8lab, seal, count):
    found = anchors(dn, c8lab)
    print("  %d anchor(s) on the ledger" % len(found))
    match = [a for a in found
             if a.get("seal") == seal and int(a.get("receipts", 0)) == count]
    for a in found:
        mark = "MATCHES" if a in match else "       "
        print("    %s %s  %s receipts  %s"
              % (mark, a.get("seal", "")[:24] + "...", a.get("receipts"),
                 a.get("ledger", "")[:34]))
    print()
    if match:
        print("  This receipts.js is the chain the principal published.")
        return 0
    print("  NOT ANCHORED. This chain head is not on the ledger, so nothing")
    print("  ties it to anyone. It may still be genuine and simply unpublished")
    print("  -- but on its own it is only a self-consistent file.")
    return 1


def main():
    if not os.environ.get("C8_CLIENT_SECRET"):
        print("C8_CLIENT_SECRET is not set. Run tests/devnet_check.py first.")
        return 1
    seal, count, ledger = chain_head()
    if not seal:
        print("no receipts. Run step-2-agent/agent.py first.")
        return 1

    import devnet_ledger as dn
    import c8lab
    print("chain head %s..., %d receipts" % (seal[:24], count))
    print("  ledger label: %s" % ledger)
    print()

    if "--check" in sys.argv:
        return do_check(dn, c8lab, seal, count)

    ok, r = publish(dn, seal, count, ledger)
    if not ok:
        print("  refused: %s" % str(r)[:300])
        return 1
    print("  published on Canton, signed by %s" % dn.PARTY["owner"].split("::")[0])
    return do_check(dn, c8lab, seal, count)


if __name__ == "__main__":
    sys.exit(main())
