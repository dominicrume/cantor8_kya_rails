#!/usr/bin/env python3
"""Prove the Python implementation conforms to SPEC.md.

Run: python3 tests/conformance.py
Exit 0 on full conformance, 1 otherwise. Used by CI.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "step-2-agent"))
from kya_chain import canonical, seal, assert_ascii, NonAsciiInReceipt

V = json.load(open(os.path.join(HERE, "vectors.json")))
fails = []


def check(ok, case, detail):
    if not ok:
        fails.append("%s: %s" % (case["name"], detail))
    print("  %s %-34s %s" % ("PASS" if ok else "FAIL", case["name"], case["kind"]))


def verify(receipts):
    """Returns 0 if the chain holds, else the 1-based position that failed."""
    prev = "GENESIS"
    for r in receipts:
        if r["prev"] != prev:
            return r["n"]
        body = {k: v for k, v in r.items() if k != "seal"}
        if seal(body, prev) != r["seal"]:
            return r["n"]
        prev = r["seal"]
    return 0


print("KYA Receipt Chain %s - Python conformance" % V["spec_version"])
for c in V["cases"]:
    if c["kind"] == "seal":
        got_c = canonical(c["body"])
        if got_c != c["canonical"]:
            check(False, c, "canonical mismatch: want %s got %s" % (c["canonical"], got_c))
        else:
            got_s = seal(c["body"], c["prev"])
            check(got_s == c["seal"], c, "seal want %s got %s" % (c["seal"], got_s))
    elif c["kind"] == "chain":
        got = verify(c["receipts"])
        want = 0 if c["verdict"] == "PASS" else c["fail_at"]
        check(got == want, c, "expected fail_at=%s, got %s" % (want, got))
    elif c["kind"] == "reject":
        try:
            assert_ascii(c["body"])
            check(False, c, "non-ASCII was accepted; it must be refused")
        except NonAsciiInReceipt as e:
            check(c["offending_field"] in str(e), c,
                  "refused, but did not name field %r" % c["offending_field"])
    else:
        check(False, c, "unknown case kind %r" % c["kind"])

print()
if fails:
    print("NOT CONFORMANT - %d failure(s):" % len(fails))
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("CONFORMANT: %d/%d cases" % (len(V["cases"]), len(V["cases"])))
