#!/usr/bin/env python3
"""The traffic-report checker must catch what a total cannot, and say what it cannot.

    python3 tests/traffic_report_smoke.py

CIP-0129 lets a dedicated synchronizer's operator publish per-party traffic and
admits a false report can misdirect rewards between participants. Misdirection
leaves the total unchanged. This proves tools/check_traffic_report.py catches it
from the parties' own records, treats a missing or broken record as UNCHECKED and
never as a match, and refuses to speak when its control fails.

All data is MOCKED. Stdlib only, per THE-RULES.md.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import check_traffic_report as T  # noqa: E402

fails = []
ALICE, BOB, CAROL = "alice::demo", "bob::demo", "carol::demo"
AT = "2026-12-05T10:00:00Z"


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


def verdicts(result):
    return {p: v["verdict"] for p, v in result["parties"].items()}


def honest_and_misdirected():
    r = T.compare(*T.demo_inputs(0))
    check(set(verdicts(r).values()) == {T.MATCH} and T.coverage(r) == 100.0,
          "an honest report matches every party and is fully confirmed")
    r = T.compare(*T.demo_inputs(40))
    check(r["sum_matches_total"], "a misdirection leaves the row sum equal to the total")
    check(verdicts(r) == {ALICE: T.OVER, BOB: T.UNDER, CAROL: T.MATCH},
          "the parties' own records catch it, on exactly the two parties involved")
    check(round(T.coverage(r), 1) == round(100.0 * 80 / 300, 1),
          "only the row a party's record confirmed counts toward coverage (80 of 300)")
    a, b = r["parties"][ALICE], r["parties"][BOB]
    check(a["reported"] - a["held"] == b["held"] - b["reported"] == 40,
          "what one party is over-credited the other is under-credited")


def invented_and_left_out():
    report, records = T.demo_inputs(0)
    report["rows"][0]["bytes"] += 50
    r = T.compare(report, records)
    check(not r["sum_matches_total"] and T.disagreements(r)[1],
          "rows that do not add up to the reported total are flagged on their own")
    report, records = T.demo_inputs(0)
    report["rows"][0]["bytes"] += 50
    report["total_bytes"] += 50
    r = T.compare(report, records)
    check(verdicts(r)[ALICE] == T.OVER and r["sum_matches_total"],
          "invented traffic with the total adjusted to fit is still caught")
    report, records = T.demo_inputs(0)
    report["rows"] = [x for x in report["rows"] if x["party"] != CAROL]
    report["total_bytes"] -= 80
    r = T.compare(report, records)
    check(verdicts(r).get(CAROL) == T.UNDER and r["parties"].get(CAROL, {}).get("reported") == 0,
          "a party the report leaves out is caught from its own record")


def missing_and_broken_records():
    report, records = T.demo_inputs(0)
    del records[BOB]
    r = T.compare(report, records)
    check(verdicts(r)[BOB] == T.NO_RECORD and T.coverage(r) < 100.0,
          "a party with no record is UNCHECKED, not a match, and coverage falls")
    report, records = T.demo_inputs(0)
    records[BOB][0]["amount"] = "1"
    r = T.compare(report, records)
    check(verdicts(r)[BOB] == T.BROKEN, "a tampered record is RECORD_BROKEN, not a match")
    check(T.coverage(r) < 100.0, "a broken record does not count toward coverage")


def receipts_that_must_not_count():
    report, records = T.demo_inputs(0)
    refused = T.make_chain("sync-demo", [(AT, 100)])
    refused[0]["outcome"] = "REFUSED"
    refused[0]["seal"] = T.seal({k: v for k, v in refused[0].items() if k != "seal"}, "GENESIS")
    cases = (("another synchronizer", T.make_chain("other-sync", [(AT, 100)])),
             ("another month", T.make_chain("sync-demo", [("2026-11-05T10:00:00Z", 100)])),
             ("a REFUSED receipt", refused))
    for label, receipts in cases:
        records[ALICE] = receipts
        check(verdicts(T.compare(report, records))[ALICE] == T.OVER,
              "%s is not counted as traffic" % label)


def bad_input_is_rejected():
    bad = {"synchronizer": "s", "period": "2026-12", "total_bytes": 1,
           "rows": [{"party": "a", "bytes": 1}, {"party": "a", "bytes": 0}]}
    try:
        T.compare(bad, {})
        check(False, "a repeated party in the report is rejected")
    except T.BadInput:
        check(True, "a repeated party in the report is rejected")
    for value in (True, -1, 1.5):
        try:
            T.read_report({"synchronizer": "s", "period": "p", "total_bytes": value, "rows": []})
            check(False, "total_bytes %r is rejected" % (value,))
        except T.BadInput:
            check(True, "total_bytes %r is rejected" % (value,))


def blind_comparison():
    return {"parties": {p: {"verdict": T.MATCH, "reported": 0, "held": 0} for p in (ALICE, BOB, CAROL)},
            "sum_matches_total": True, "total": 300}


def the_control():
    check(T.control(), "the built-in control passes when the comparison is sound")
    real = T.compare
    T.compare = lambda *a, **k: blind_comparison()
    try:
        check(not T.control(), "a comparison that cannot see misdirection fails the control")
    finally:
        T.compare = real


def the_demo_runs():
    out = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_traffic_report.py"),
                          "--demo"], capture_output=True, text=True)
    check(out.returncode == 0 and "DOES NOT PROVE" in out.stdout and "MOCKED" in out.stdout,
          "the demo runs, exits 0, and prints what it does not prove")
    check("DISAGREEMENT: alice::demo, bob::demo" in out.stdout,
          "the demo's misdirected report is named in the output")


def main():
    print("traffic-report checker")
    for step in (honest_and_misdirected, invented_and_left_out, missing_and_broken_records,
                 receipts_that_must_not_count, bad_input_is_rejected, the_control, the_demo_runs):
        step()
    print("\n%s" % ("ALL GREEN" if not fails else "%d FAILED: %s" % (len(fails), fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
