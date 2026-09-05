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
# Nested probes included on purpose. This list used to be top-level only, so
# when pkg/ learned to see nested values and the repo did not, the check that
# exists to catch exactly that divergence could not see it.
for probe in ({"what": "Pay ₦500"}, {"rule": "the desk’s limit"},
              {"ok": "plain ascii"}, {"é": "key is non-ascii"},
              {"what": {"note": "Pay ₦500"}}, {"what": ["Pay ₦500"]},
              {"deep": {"a": {"b": "the desk’s limit"}}}):
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
                currency="USD", approved_by="p", ledger="l")
chain.receipts[0]["amount"] = "9999.0"
try:
    chain.stamp(what="y", amount="1.0", payee="a", rule="r", outcome="ACCEPTED",
                currency="USD", approved_by="p", ledger="l")
    check(False, "stamp() refuses to extend a broken chain")
except pkg.BrokenChain:
    check(True, "stamp() refuses to extend a broken chain")

try:
    pkg.Chain().stamp(what="x", amount=1 / 3, currency="USD", payee="a",
                      rule="r", outcome="ACCEPTED", approved_by="p", ledger="l")
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
live.stamp(what="x", amount="1.0", currency="USD", payee="a", rule="r",
           outcome="ACCEPTED", approved_by="p", ledger="l")
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

# --- the four adoption fixes ------------------------------------------------
print()
print("  adoption:")

try:
    pkg.Chain().stamp(what="x", amount="1.0", payee="a", rule="r",
                      outcome="ACCEPTED", approved_by="p", ledger="l")
    check(False, "currency is required, not silently defaulted to Canton Coin")
except TypeError:
    check(True, "currency is required, not silently defaulted to Canton Coin")

simple = pkg.Chain(approved_by="finance", ledger="stripe")
simple.allowed(what="invoice 41", amount="250.00", currency="USD",
               payee="Acme", rule="under the cap")
simple.refused(what="invoice 42", amount="9000.00", currency="USD",
               payee="Unknown", rule="not on the allow-list")
check([r["outcome"] for r in simple.receipts] == ["ACCEPTED", "REFUSED"],
      "allowed() and refused() set the outcome so the caller does not have to")
check(simple.receipts[0]["approved_by"] == "finance"
      and simple.receipts[0]["ledger"] == "stripe",
      "and the desk's context is set once on the Chain, not per receipt")
check(simple.receipts[0]["currency"] == "USD", "with the currency actually asked for")

# The CLI must tell three answers apart. A wrongly-shaped file is not tampered.
def _cli(body, name="f.json"):
    d = tempfile.mkdtemp()
    path = os.path.join(d, name)
    open(path, "w").write(body)
    r = subprocess.run([sys.executable, "-m", "knowyouragenticai_receipts",
                        "verify", name], cwd=d, env=env, capture_output=True, text=True)
    return r.returncode, r.stdout

real = json.loads(open(os.path.join(ROOT, "step-3-verify", "receipts.js")).read()
                  .split("[", 1)[1].rsplit("]", 1)[0].join("[]"))

code, out = _cli(json.dumps({"receipts": real}))
check(code == 0 and "every seal holds" in out,
      "the CLI finds a chain wrapped in an export instead of calling it BROKEN")

code, out = _cli(json.dumps({"setting": True}))
check(code == 2 and "not a receipt chain" in out and "BROKEN" not in out,
      "a file that was never a chain is never called BROKEN")

code, out = _cli("hello, not json at all")
check(code == 2 and "not JSON this tool can read" in out,
      "and unreadable input is told apart from readable-but-not-a-chain")

broken = json.loads(json.dumps(real)); broken[1]["amount"] = "9999.0"
code, out = _cli(json.dumps(broken))
check(code == 1 and "BROKEN at receipt 2" in out,
      "an actually tampered chain is still BROKEN, and names the receipt")
check("ask whoever gave you this file" in out,
      "and says what to do about it")

ex = subprocess.run([sys.executable, "-m", "knowyouragenticai_receipts", "example"],
                    cwd=ELSEWHERE, env=env, capture_output=True, text=True)
check(ex.returncode == 0 and "BROKEN at 3" in ex.stdout,
      "the example runs as a subcommand, and shows the tamper being caught")

# Everything the README promises must survive into the built artefacts. A
# README that points at a file which does not ship is a broken promise to
# everyone who installed rather than cloned -- which is most people.
import glob as _glob, re as _re, tarfile, zipfile
readme = open(os.path.join(ROOT, "pkg", "README.md")).read()
rel = [h for _t, h in _re.findall(r"\[([^\]]+)\]\(([^)]+)\)", readme)
       if not h.startswith("http")]
check(not rel, "no relative links in the README, which is rendered standalone on PyPI")

for cmd in _re.findall(r"python -m knowyouragenticai_receipts (\w+)", readme):
    r = subprocess.run([sys.executable, "-m", "knowyouragenticai_receipts", cmd,
                        *(["--help"] if cmd == "verify" else [])],
                       cwd=ELSEWHERE, env=env, capture_output=True, text=True)
    # `r.returncode in (0, 2)` accepted 2 -- which is exactly what an unknown
    # command returns, so this passed for a subcommand called `totallybogus`.
    check("unknown command" not in r.stdout,
          "the README's `%s` subcommand exists" % cmd)

print()
if fails:
    print("PACKAGE SMOKE FAILED - %d:" % len(fails))
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("the published format and the repository's are the same format.")
