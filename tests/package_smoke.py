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
import importlib.util, json, os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "step-2-agent"))
sys.path.insert(0, os.path.join(ROOT, "pkg", "src"))

import kya_chain as repo
import knowyouragenticai_receipts as pkg

fails = []


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


print("KYA Rails - the package and the repository agree")

vectors = json.load(open(os.path.join(ROOT, "tests", "vectors.json")))
shipped = json.load(open(os.path.join(ROOT, "pkg", "src", "knowyouragenticai_receipts",
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

# --- the ten defects found by attacking it before publishing ---------------
# Each of these was real. They are asserted here so a refactor cannot quietly
# put any of them back.
print()
print("  the ten, locked down:")

for bad, label in ([["a string"], "a list of strings"],
                   [[None], "a list of nulls"],
                   [[42], "a list of numbers"],
                   [[{"not": "a receipt"}], "an object that is not a receipt"]):
    try:
        ok, where = pkg.verify(bad)
        check(ok is False and isinstance(where, int),
              "verify() answers instead of raising on %s" % label)
    except Exception as e:
        check(False, "verify() raised %s on %s" % (type(e).__name__, label))

chain = pkg.Chain()
for i in range(2):
    chain.stamp(what="x", amount="1.0", payee="a", rule="r", outcome="ACCEPTED",
                approved_by="p", ledger="l")
chain.receipts[0]["amount"] = "9999.0"
try:
    chain.stamp(what="y", amount="1.0", payee="a", rule="r", outcome="ACCEPTED",
                approved_by="p", ledger="l")
    check(False, "stamp() refuses to extend a broken chain")
except pkg.BrokenChain:
    check(True, "stamp() refuses to extend a broken chain")

try:
    pkg.Chain().stamp(what="x", amount=1 / 3, payee="a", rule="r",
                      outcome="ACCEPTED", approved_by="p", ledger="l")
    check(False, "stamp() refuses a float amount")
except TypeError:
    check(True, "stamp() refuses a float amount")

check(pkg.verify([{"prev": "GENESIS", "seal": "x"}]) == (False, 1),
      "verify() gives a position even when the receipt has no n")

for probe, label in (({"what": {"note": "Pay \u20a6500"}}, "inside a dict"),
                     ({"what": ["Pay \u20a6500"]}, "inside a list")):
    try:
        pkg.assert_ascii(probe)
        check(False, "non-ASCII %s is rejected" % label)
    except pkg.NonAsciiInReceipt:
        check(True, "non-ASCII %s is rejected" % label)

live = pkg.Chain()
live.stamp(what="x", amount="1.0", payee="a", rule="r", outcome="ACCEPTED",
           approved_by="p", ledger="l")
check("verified" in repr(live) and "1 receipts" in repr(live),
      "repr() shows the count and that it verifies")
live.receipts[0]["amount"] = "2.0"
check("BROKEN" in repr(live), "and says BROKEN when it is")

import subprocess
# Run the CLI from a directory that is NOT the repository, so an accidental
# relative-path success cannot be mistaken for the installed package working.
ELSEWHERE = tempfile.mkdtemp()
env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "pkg", "src"),
           PYTHONDONTWRITEBYTECODE="1")
r = subprocess.run([sys.executable, "-m", "knowyouragenticai_receipts", "verify",
                    os.path.join(ROOT, "step-3-verify", "receipts.js")],
                   capture_output=True, text=True, cwd=ELSEWHERE, env=env)
check(r.returncode == 0 and "every seal holds" in r.stdout,
      "the CLI verifies a real receipts file")
# Whitespace-normalised: the CLI wraps its output, so a phrase that spans the
# wrap is not in stdout as one string.
check("does not prove where the file came from" in " ".join(r.stdout.split()),
      "and says what a passing check does NOT prove")

import json as _json
forged = _json.loads(open(os.path.join(ROOT, "step-3-verify", "receipts.js")).read()
                     .split("[", 1)[1].rsplit("]", 1)[0].join("[]"))
forged[1]["amount"] = "9999.0"
tmp = os.path.join(ELSEWHERE, "broken.json")
open(tmp, "w").write(_json.dumps(forged))
r = subprocess.run([sys.executable, "-m", "knowyouragenticai_receipts", "verify", tmp],
                   capture_output=True, text=True, cwd=ELSEWHERE, env=env)
check(r.returncode == 1 and "BROKEN at receipt" in r.stdout,
      "the CLI exits 1 and names the receipt on a tampered file")

check(os.path.exists(os.path.join(ROOT, "pkg", "src", "knowyouragenticai_receipts", "py.typed")),
      "py.typed ships so the package type-checks for dependents")
check(os.path.exists(os.path.join(ROOT, "pkg", "CHANGELOG.md")), "there is a CHANGELOG")

print()
if fails:
    print("PACKAGE SMOKE FAILED - %d:" % len(fails))
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("the published format and the repository's are the same format.")
