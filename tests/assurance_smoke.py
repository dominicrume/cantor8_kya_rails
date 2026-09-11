#!/usr/bin/env python3
"""A findings record a client can check without trusting whoever wrote it.

An audit report is a claim. You believe it because of who signed it, and if a
finding is softened or dropped between the run and the PDF, the document reads
exactly the same. That is the part being removed here: `tools/assurance.py`
emits the findings as a receipt chain, so the client checks the report itself
rather than the reputation of the firm that produced it.

Three claims, and the third is the one that matters:

**Every fence becomes an entry, covered ones included.** A report listing only
problems cannot be told apart from a short one. If the covered fences were
dropped, "3 findings" would be indistinguishable from "3 findings out of 3"
and from "3 out of 300".

**The verdict survives the trip.** `ok` must arrive as COVERED and `UNCOVERED`
as UNCOVERED -- a mapping that silently swallowed an unknown state would put a
finding in the file under a label nobody reads.

**Softening a finding breaks the seal.** Not "is detectable if someone checks
the hashes" -- the same verify the public page runs must return the entry it
broke at. This is checked against the auditor's own worst behaviour: changing
UNCOVERED to COVERED, and deleting an entry entirely.

Runs without Daml: the mutation harness is stubbed, because what is under test
is the record, not the toolchain that fills it.

Run: python3 tests/assurance_smoke.py
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in ("tools", "step-2-agent"):
    sys.path.insert(0, os.path.join(ROOT, _p))

import assurance                                        # noqa: E402
from kya_chain import Chain, canonical, seal               # noqa: E402


def as_chain(receipts):
    """Verify a list of entries the way the page does: it is handed a file,
    not an object that built itself."""
    c = Chain()
    c.receipts = receipts
    return c

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


# Two real rows from the OpenZeppelin run, in the shape run_all returns.
ROWS = [
    ("ok", "AccessControlV1.daml:288  assertMsg eRoleAdminMismatch (grant.admin == admin)",
     "daml/OpenZeppelin/AccessControlV1Test.daml:test_grantRole goes red"),
    ("UNCOVERED", "AccessControlV1.daml:289  assertMsg eRoleAssigneeMismatch (grant.account == caller)",
     "every test still passes without it"),
    ("BROKE", "Oracle.daml:29  assertMsg \"New price must be positive\"",
     "the module stopped compiling -- not testable, not covered"),
]


def built():
    chain = Chain()
    for row in ROWS:
        assurance.stamp_one(chain, row, "subject under test", "daml 3.4.11")
    return chain


print("the record carries every fence, not only the bad ones")
c = built()
check(len(c.receipts) == 3, "3 fences in, 3 entries out")
outcomes = [r["outcome"] for r in c.receipts]
check(outcomes == ["COVERED", "UNCOVERED", "NOT TESTABLE"],
      "ok/UNCOVERED/BROKE arrive as COVERED/UNCOVERED/NOT TESTABLE")
check(any(r["outcome"] == "COVERED" for r in c.receipts),
      "a covered fence is recorded, so a short report cannot pass for a clean one")

print()
print("each entry says where, and on whose authority")
r = c.receipts[1]
check(r["payee"] == "AccessControlV1.daml", "the file is named")
check(r["amount"] == "289", "the line number is carried")
check("every test still passes" in r["rule"], "the rule that produced the verdict is carried")
check(r["ledger"] == "daml 3.4.11", "the toolchain version is inside the seal, not beside it")
check(r["instrument"] == "subject under test", "the subject is on every entry")
check("mutation testing" in r["approved_by"], "the method is stated, not assumed")

print()
print("an unknown state is carried through, never quietly dropped")
c2 = Chain()
assurance.stamp_one(c2, ("WEIRD", "X.daml:1  fence", "detail"), "s", "t")
check(c2.receipts[0]["outcome"] == "WEIRD",
      "a state the mapping has never seen still reaches the file")

print()
print("the same verify the public page runs")
ok, bad = c.verify()
check(ok and bad is None, "the record as written holds")

soft = json.loads(json.dumps(c.receipts))
soft[1]["outcome"] = "COVERED"          # the auditor softens a finding
ok, bad = as_chain(soft).verify()
check(not ok and bad == 2, "softening entry 2 breaks the chain AT entry 2, not vaguely")

gone = json.loads(json.dumps(c.receipts))
del gone[1]                              # the auditor removes it entirely
ok, bad = as_chain(gone).verify()
check(not ok, "deleting a finding breaks the chain")

quiet = json.loads(json.dumps(c.receipts))
quiet[1]["rule"] = "covered by review"   # rewriting the reason, leaving the verdict
ok, bad = as_chain(quiet).verify()
check(not ok and bad == 2, "rewriting only the REASON breaks it too")

print()
print("the seal is the project's, not a second scheme")
r = c.receipts[0]
body = {k: v for k, v in r.items() if k != "seal"}
check(r["seal"] == seal(body, r["prev"]),
      "sha256(canonical(entry without seal) + prev), byte for byte")
check(canonical(body) == canonical(dict(reversed(list(body.items())))),
      "canonical form does not depend on key order, so neither does the seal")

print()
print("--under really does keep a library's own tests out of the mutation set")
import tempfile as _tf
_root = _tf.mkdtemp()
for rel, text in (("src/main/daml/Vault.daml", 'x = do\n  assertMsg "cap" (a <= cap)\n'),
                  ("src/test/daml/VaultTest.daml", 'y = do\n  assertMsg "test helper" True\n'),
                  ("packages/vendored/daml/Dep.daml", 'z = do\n  assertMsg "vendored" True\n')):
    _p = os.path.join(_root, rel); os.makedirs(os.path.dirname(_p), exist_ok=True)
    open(_p, "w").write(text)
_all = assurance.daml_mutate.fences(_root)
_main = assurance.daml_mutate.fences(_root, "src/main/daml")
check(len(_all) == 3, "without --under the whole tree is a candidate (%d fences)" % len(_all))
check(len(_main) == 1 and _main[0][0].endswith("Vault.daml"),
      "with --under src/main/daml only the library's own fence remains (%d)" % len(_main))
check(not any("Test" in f[0] or "vendored" in f[0] for f in _main),
      "  no test file and no vendored package is in the mutation set")

print()
print("the harness is told what to mutate, separately from where to build")
seen = {}
_f = assurance.daml_mutate.fences
assurance.daml_mutate.fences = lambda pkg, under=None: seen.setdefault("under", under) or [
    ("x.daml", 1, "assertMsg x")]
assurance.daml_mutate.build_and_test = lambda s, t: (True, {"A:b"}, "")
assurance.daml_mutate.run_all = lambda *a: ROWS
_p = os.path.join(tempfile.mkdtemp(), "u.json")
assurance.run("src", "test", "subject", _p, "src/main/daml")
assurance.daml_mutate.fences = _f
check(seen.get("under") == "src/main/daml",
      "--under reaches the fence scan, so a library's own tests are not mutated")

print()
print("a record that does not verify is never written")
bad_path = os.path.join(tempfile.mkdtemp(), "findings.json")
_saved = assurance.daml_mutate.run_all, assurance.daml_mutate.build_and_test, assurance.daml_mutate.fences
assurance.daml_mutate.fences = lambda pkg, under=None: [("x.daml", 1, "assertMsg x")]
assurance.daml_mutate.build_and_test = lambda s, t: (True, {"A:b"}, "")
assurance.daml_mutate.run_all = lambda *a: ROWS
try:
    rc = assurance.run("src", "test", "subject", bad_path)
    check(rc == 0, "a clean stubbed run writes the file and exits 0")
    check(os.path.exists(bad_path), "the file is there")
    on_disk = json.load(open(bad_path))
    check(as_chain(on_disk).verify()[0], "what landed on disk verifies")
    check(len(on_disk) == 3, "every entry reached the file")

    assurance.daml_mutate.build_and_test = lambda s, t: (False, set(), "boom")
    rc = assurance.run("src", "test", "subject", bad_path + ".2")
    check(rc == 2, "a project that does not build cleanly is refused, not reported on")
    check(not os.path.exists(bad_path + ".2"), "and nothing is written")

    assurance.daml_mutate.fences = lambda pkg, under=None: []
    rc = assurance.run("src", "test", "subject", bad_path + ".3")
    check(rc == 1, "nothing to assure is said, not reported as clean")
    check(not os.path.exists(bad_path + ".3"), "and nothing is written")

    # The guard that refuses to hand over a record that does not hold. It
    # should never fire -- which is exactly why it needs a test: an unfirable
    # guard and a broken one look identical from the outside.
    class Broken(Chain):
        def verify(self):
            return False, 2
    assurance.daml_mutate.fences = lambda pkg, under=None: [("x.daml", 1, "assertMsg x")]
    assurance.daml_mutate.build_and_test = lambda s, t: (True, {"A:b"}, "")
    _chain, assurance.Chain = assurance.Chain, Broken
    try:
        rc = assurance.run("src", "test", "subject", bad_path + ".4")
    finally:
        assurance.Chain = _chain
    check(rc == 3, "a record that fails its own verify is refused")
    check(not os.path.exists(bad_path + ".4"),
          "and is never written, so no unverifiable file can leave the building")
finally:
    assurance.daml_mutate.run_all, assurance.daml_mutate.build_and_test, assurance.daml_mutate.fences = _saved

print()
if fails:
    print("FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("all good: findings are sealed, and no edit to one survives the public check.")
