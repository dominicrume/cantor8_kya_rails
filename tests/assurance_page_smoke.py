#!/usr/bin/env python3
"""The customer's report page must tell the truth about the record, and nothing else.

    python3 tests/assurance_page_smoke.py

tools/assurance_page.py renders a sealed findings record as a page. This proves
the numbers on the page are the record's numbers, that nothing from the record
reaches the page unescaped, that the page carries what the review does not prove,
and that a record whose seal chain does not verify produces no page at all.

Stdlib only, per THE-RULES.md.
"""
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "step-2-agent"))
import assurance_page as P  # noqa: E402
from kya_chain import seal  # noqa: E402

fails = []
TOOL = os.path.join(ROOT, "tools", "assurance_page.py")


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


def record(entries, instrument="demo / package @ abc123"):
    """MOCKED record: entries are (what, line, file, outcome, rule)."""
    out, prev = [], "GENESIS"
    for n, (what, line, name, outcome, rule) in enumerate(entries, 1):
        r = {"n": n, "what": what, "amount": str(line), "payee": name, "currency": "N/A",
             "instrument": instrument, "rule": rule, "outcome": outcome,
             "approved_by": "mutation testing", "ledger": "daml 3.4.11",
             "at": "2026-11-20T10:00:00Z", "prev": prev}
        r["seal"] = seal(r, prev)
        out.append(r)
        prev = r["seal"]
    return out


GAP = "every test still passes without it"
MIXED = [("ensure a > 0", 10, "A.daml", "UNCOVERED", GAP),
         ("assertMsg \"b\" (b)", 20, "A.daml", "UNCOVERED", GAP),
         ("ensure c", 5, "B.daml", "UNCOVERED", GAP),
         ("ensure d", 7, "B.daml", "COVERED", "daml/T.daml:test_d goes red"),
         ("ensure e", 9, "B.daml", "COVERED", "daml/T.daml:test_e goes red")]


def numbers_and_branches():
    page = P.render(record(MIXED))
    check("3 of 5 checks have no test that notices their removal" in page,
          "the headline is the record's own count")
    check("test_d" in page and "test_e" in page, "a covered check names the test that protects it")
    page = P.render(record([m for m in MIXED if m[3] == "COVERED"]))
    check("Every one of the 2 checks has a test" in page and "Checks nobody would notice" not in page,
          "a record with no gaps says so and shows no gap section")
    check("could not be tested" not in P.render(record(MIXED)),
          "the could-not-be-tested card is absent when nothing was untestable")
    skipped = MIXED + [("ensure f", 3, "B.daml", "NOT TESTABLE", "no test package")]
    check("could not be tested" in P.render(record(skipped)),
          "the card appears when a check could not be tested")


def escaping():
    evil = '<script>alert(1)</script> & "x"'
    page = P.render(record([(evil, 1, "<b>F.daml</b>", "UNCOVERED", GAP)],
                           instrument="<img src=x onerror=1>"))
    check("<script>alert" not in page and "&lt;script&gt;alert" in page,
          "a check's text is escaped before it reaches the page")
    check("<b>F.daml</b>" not in page and "<img src=x" not in page,
          "file names and the package name are escaped too")
    check("<script" not in page and "http://" not in page and "https://" not in page,
          "the page has no script and no outside reference")


def seal_and_limits():
    rec = record(MIXED)
    page = P.render(rec)
    check(rec[-1]["seal"] in page, "the page shows the record's head seal")
    check("does not prove" in page and "coverage finding, not a vulnerability" in page,
          "the page says what the review does not prove")


def run_tool(path_in):
    out = os.path.join(os.path.dirname(path_in), "out.html")
    r = subprocess.run([sys.executable, TOOL, path_in, out], capture_output=True, text=True)
    return r.returncode, os.path.exists(out)


def refusals():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "r.json")
        rec = record(MIXED)
        json.dump(rec, open(path, "w"))
        check(run_tool(path) == (0, True), "a record that verifies produces a page")
        os.remove(os.path.join(d, "out.html"))
        rec[1]["amount"] = "999"
        json.dump(rec, open(path, "w"))
        check(run_tool(path) == (1, False), "a tampered record is refused and no page is written")
        json.dump([], open(path, "w"))
        check(run_tool(path)[0] == 2, "an empty record is a usage error, not a page")
        open(path, "w").write("not json")
        check(run_tool(path)[0] == 2, "an unreadable record is a usage error, not a page")


def a_real_record():
    path = os.path.join(ROOT, "docs", "findings", "canton-token-template-simple-token.json")
    rec = P.load(path)
    page = P.render(rec)
    counts = Counter(r["outcome"] for r in rec)
    check(P.verified(rec), "the real record in docs/findings verifies")
    check("%d of %d checks have no test" % (counts["UNCOVERED"], len(rec)) in page,
          "its headline matches its own receipts (%d of %d)" % (counts["UNCOVERED"], len(rec)))


def main():
    print("assurance page")
    for step in (numbers_and_branches, escaping, seal_and_limits, refusals, a_real_record):
        step()
    print("\n%s" % ("ALL GREEN" if not fails else "%d FAILED: %s" % (len(fails), fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
