#!/usr/bin/env python3
"""Run the mutation harness on a package whose answers are known in advance.

    python3 tests/daml_mutate_fixture_run.py

Needs the Daml SDK (it really builds and tests), so it is not part of the fast
suite. It prints SKIPPED and exits 0 when `daml` is not on PATH.

tests/fixtures/mutate_fixture/lib is a tiny library with five checks. Which of
them are covered, and which are not, is written into the fixture's own comments
BEFORE the harness is run, so this is a known-answer test, not a snapshot of
whatever the tool happened to say:

    ensure balance >= 0.0        covered
    require "amount positive"    covered
    require "cannot overdraw"    covered
    require "daily limit"        UNCOVERED
    unless ... abort "reserved"  UNCOVERED
    unit <- require ...          cannot be tested: must be listed NOT SEEN

A LESSON FROM THE FIRST RUN. The fixture originally subtracted the amount, so an
overdraw made the balance negative and the template's `ensure balance >= 0.0`
refused it as well. The harness reported `require "cannot overdraw"` UNCOVERED
and my written expectation said covered. The harness was right: the two checks
masked each other. The fixture was changed so every check stands alone, and
this note stays so the reason is not lost.

WHAT THIS PROVES
  1. The legacy harness sees ONE of the five, and says "every fence is covered"
     while two are not. That is the blind spot this work exists to close, shown
     rather than described.
  2. With --constructs all it sees five, gives each its known verdict, exits
     non-zero because two are uncovered, and lists the sixth as NOT SEEN.
  3. It does not mutate the helper's own body, which would make every call
     vacuous at once and report everything "covered" for the wrong reason.
  4. The fixture's source is byte-identical afterwards.
  5. The sealed record carries NOT SEEN and SCOPE receipts, and still verifies.

Stdlib only, per THE-RULES.md.
"""
import json
import os
import re
import shutil
# B404 is suppressed below: running the harness is the whole test.
import subprocess  # nosec B404
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "mutate_fixture")
fails = []


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


def run(argv, cwd):
    # B603: literal argv built from this file's own constants, shell=False.
    p = subprocess.run([sys.executable] + argv, cwd=cwd,  # nosec B603
                       capture_output=True, text=True, timeout=1500)
    return p.returncode, p.stdout + p.stderr


def rows(out):
    """{line number: verdict} from the harness output."""
    return {int(m.group(3)): m.group(1) for m in
            re.finditer(r"^  (ok|UNCOVERED|BROKE|STALE)\s+(\S+?):(\d+)\s", out, re.M)}


def source_hash(lib):
    with open(os.path.join(lib, "daml", "Vault.daml"), "rb") as fh:
        return fh.read()


def legacy_phase(lib, test, harness):
    print("the old harness, on a package it cannot fully see")
    code, out = run([harness, "--src", lib, "--test", test], ROOT)
    check(len(rows(out)) == 1, "it sees ONE check of five (%d)" % len(rows(out)))
    check(code == 0 and "every fence is covered" in out,
          "  and reports every fence covered, while two are not: the blind spot")


def new_phase(lib, test, harness, before):
    print("")
    print("--constructs all, the same package")
    code, out = run([harness, "--src", lib, "--test", test, "--constructs", "all"], ROOT)
    got = rows(out)
    want = {27: "ok", 33: "ok", 34: "ok", 35: "UNCOVERED", 36: "UNCOVERED"}
    check(got == want, "five checks, each with its known verdict %s" % (got if got != want else ""))
    check(code == 1, "it exits 1 because two are uncovered (%d)" % code)
    check("NOT SEEN" in out or "not seen" in out, "  and says that check-like lines were not seen")
    check(set(got) == set(want),
          "the helper's own body (lines 16 to 17) is not among the mutated lines")
    check(source_hash(lib) == before, "the fixture source is byte-identical afterwards")


def record_phase(lib, test, tmp):
    print("")
    print("the sealed record")
    record = os.path.join(tmp, "findings.json")
    run([os.path.join(ROOT, "tools", "assurance.py"), "--src", lib, "--test", test,
         "--constructs", "all", "--out", record], ROOT)
    receipts = json.load(open(record)) if os.path.exists(record) else []
    outcomes = [r["outcome"] for r in receipts]
    check(outcomes.count("COVERED") == 3 and outcomes.count("UNCOVERED") == 2,
          "3 covered and 2 uncovered receipts (%s)" % sorted(set(outcomes)))
    check(outcomes.count("NOT SEEN") == 1 and outcomes[-1:] == ["SCOPE"],
          "one NOT SEEN receipt, with the reason, and a closing SCOPE receipt")
    why = next((r["rule"] for r in receipts if r["outcome"] == "NOT SEEN"), "")
    check("bound result" in why, "  the NOT SEEN receipt says why")
    scope = receipts[-1]["rule"] if receipts else ""
    check("recognised=5;not_seen=1" in scope, "  and the SCOPE receipt states the counts: %s" % scope)
    sys.path.insert(0, os.path.join(ROOT, "pkg", "src"))
    from knowyouragenticai_receipts import verify
    check(verify(receipts)[0] is True, "the record verifies")


def main():
    if shutil.which("daml") is None:
        print("SKIPPED: the Daml SDK is not on PATH, and this test builds for real.")
        return 0
    tmp = tempfile.mkdtemp(prefix="kya-fixture-")
    try:
        work = os.path.join(tmp, "mutate_fixture")
        shutil.copytree(FIXTURE, work, ignore=shutil.ignore_patterns(".daml"))
        lib, test = os.path.join(work, "lib"), os.path.join(work, "lib-test")
        harness = os.path.join(ROOT, "tools", "daml_mutate.py")
        legacy_phase(lib, test, harness)
        new_phase(lib, test, harness, source_hash(lib))
        record_phase(lib, test, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("")
    if fails:
        print("FAILED: %d" % len(fails))
        for f in fails:
            print("  - " + f)
        return 1
    print("the old harness missed four of five checks and called the package fully covered;")
    print("the new one found all five, gave each its known verdict, and listed what it could not test.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
