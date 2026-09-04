#!/usr/bin/env python3
"""The published package and the repository must not drift apart.

pkg/ ships the receipt format to PyPI. step-2-agent/kya_chain.py is the same
format inside this repository. Two copies of one algorithm is how you end up
with two answers, and here the two answers would be two different hashes for
the same receipt -- a chain that verifies for whoever installed the package and
goes red for whoever cloned the repo.

They are separate files on purpose: the repository installs nothing
(THE-RULES.md), so it cannot import its own package. This is the check that
makes that safe. It runs both implementations over every vector and requires
byte-identical output, not merely both-conformant output -- two implementations
can each pass the vectors and still disagree on an input no vector covers.

Run: python3 tests/package_smoke.py
"""
import importlib.util, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "step-2-agent"))
sys.path.insert(0, os.path.join(ROOT, "pkg", "src"))

import kya_chain as repo
import kya_receipt_chain as pkg

fails = []


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


print("KYA Rails - the package and the repository agree")

vectors = json.load(open(os.path.join(ROOT, "tests", "vectors.json")))
shipped = json.load(open(os.path.join(ROOT, "pkg", "src", "kya_receipt_chain",
                                      "vectors.json")))
check(shipped == vectors, "the vectors shipped in the package are the repository's")

# Byte-identical, not merely both-conformant. Two implementations can each
# pass every vector and still disagree on an input no vector covers.
bodies = [c["body"] for c in vectors["cases"] if "body" in c]
for c in vectors["cases"]:
    bodies.extend({k: v for k, v in r.items() if k != "seal"}
                  for r in c.get("receipts", []))
mismatch = [b for b in bodies if repo.canonical(b) != pkg.canonical(b)]
check(not mismatch, "canonical() agrees on all %d bodies in the vectors" % len(bodies))

seal_bad = [b for b in bodies
            if repo.seal(b, "GENESIS") != pkg.seal(b, "GENESIS")]
check(not seal_bad, "seal() agrees on all %d bodies" % len(bodies))

# Inputs no vector covers, where two honest implementations could still differ.
edges = [
    {}, {"a": ""}, {"z": "1", "a": "2"}, {"n": 0}, {"amount": "1.0"},
    {"amount": "1.00"}, {"x": "a/b"}, {"x": "tab\there"}, {"x": 'quote"'},
    {"x": "back\\slash"}, {"nested": {"b": 1, "a": 2}}, {"list": [3, 1, 2]},
    {"big": "x" * 5000}, {"true": True, "null": None},
]
edge_bad = [e for e in edges if repo.canonical(e) != pkg.canonical(e)]
check(not edge_bad, "canonical() agrees on %d edge inputs no vector covers" % len(edges))

# The rejection rule has to match too, or one of them seals what the other refuses.
for probe in ({"what": "Pay ₦500"}, {"rule": "the desk’s limit"},
              {"ok": "plain ascii"}, {"é": "key is non-ascii"}):
    r_raised = p_raised = None
    try:
        repo.assert_ascii(probe)
    except Exception as e:
        r_raised = type(e).__name__
    try:
        pkg.assert_ascii(probe)
    except Exception as e:
        p_raised = type(e).__name__
    check(r_raised == p_raised,
          "both %s %r" % ("reject" if r_raised else "accept", list(probe)[0]))

check(pkg.__version__ == "1.0.0", "the package version is set")

print()
if fails:
    print("PACKAGE SMOKE FAILED - %d:" % len(fails))
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("the published format and the repository's are the same format.")
