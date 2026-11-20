#!/usr/bin/env python3
"""Check a dedicated synchronizer's traffic report against what the parties hold.

    python3 tools/check_traffic_report.py --demo
    python3 tools/check_traffic_report.py REPORT.json --records RECORDS.json

CIP-0129 (Approved) has the operator of each dedicated synchronizer publish
aggregate traffic reports, attributed per party, and says plainly: "At launch,
these reports rely on the operator being honest. A maliciously constructed report
can misdirect rewards between participants of the dedicated synchronizer."

Misdirection moves traffic from one party's row to another's. The total does not
change, so no total check can see it. Each party's own record can. This tool
compares every row of the operator's report with the hash-chained record that
party holds, and says how much of the report it could and could not check.

WHAT IS MOCKED OR ASSUMED, stated up front:
  * CIP-0129 defines no report format. The JSON below is ASSUMED, not the
    network's. The demo data is MOCKED.
  * How a real validator exports its own traffic receipts is NOT BUILT. This
    tool takes receipts in the KYA chain format (step-2-agent/kya_chain.py).

WHAT IT DOES NOT PROVE, printed on every run:
  * A MATCH means operator and party agree. It does not mean either is right.
    If they collude, or the party copies the operator's row, they match.
  * A party that supplies no record, or a broken one, is UNCHECKED, and the
    share of reported traffic that is unchecked still rests on the operator.
  * It says nothing about the CC burned, discounts or the reward weights.

Report format (ASSUMED):
  {"synchronizer": "...", "period": "2026-12", "total_bytes": 300,
   "rows": [{"party": "alice::demo", "bytes": 100}, ...]}
Records format (ASSUMED): {"records": {"alice::demo": [<kya receipts>], ...}}
A receipt counts only if outcome is ACCEPTED, instrument is "traffic", payee is
the synchronizer, and its "at" date falls in the period (YYYY-MM prefix).

Exit 0: nothing disagreed. 1: at least one disagreement. 2: bad input.
3: the built-in control failed, so no verdict is given. Stdlib only.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "step-2-agent"))
from kya_chain import Chain, seal  # noqa: E402  (the same seal math as the verifier)

MATCH, OVER, UNDER = "MATCH", "OPERATOR_COUNTS_MORE", "OPERATOR_COUNTS_LESS"
BROKEN, NO_RECORD = "RECORD_BROKEN", "NO_RECORD"
UNCHECKED = (BROKEN, NO_RECORD)

LIMITS = (
    "a MATCH means the operator and the party agree, not that either is right",
    "an unchecked row still rests on the operator being honest",
    "the report format is ASSUMED: CIP-0129 defines none",
    "no real validator export is built: the demo data is MOCKED",
    "nothing here checks the CC burned, the discounts or the reward weights",
)


class BadInput(ValueError):
    pass


def make_chain(synchronizer, events):
    """MOCKED party record: a sealed KYA chain from (iso_time, bytes) events."""
    receipts, prev = [], "GENESIS"
    for n, (at, size) in enumerate(events, 1):
        r = {"n": n, "what": "sequencer traffic", "amount": str(size),
             "payee": synchronizer, "currency": "BYTE", "instrument": "traffic",
             "rule": "traffic-cost", "outcome": "ACCEPTED", "approved_by": "party",
             "ledger": "MOCKED", "at": at, "prev": prev}
        r["seal"] = seal(r, prev)
        receipts.append(r)
        prev = r["seal"]
    return receipts


def _size(value, what):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BadInput("%s must be a non-negative whole number of bytes" % what)
    return value


def read_report(raw):
    for key in ("synchronizer", "period", "total_bytes", "rows"):
        if key not in raw:
            raise BadInput("report has no %r" % key)
    rows, seen = {}, set()
    for row in raw["rows"]:
        party = row.get("party")
        if not party or party in seen:
            raise BadInput("report has a missing or repeated party: %r" % party)
        seen.add(party)
        rows[party] = _size(row.get("bytes"), "bytes for %s" % party)
    return raw["synchronizer"], raw["period"], _size(raw["total_bytes"], "total_bytes"), rows


def held_bytes(receipts, synchronizer, period):
    total = 0
    for r in receipts:
        counts = (r.get("outcome") == "ACCEPTED" and r.get("instrument") == "traffic"
                  and r.get("payee") == synchronizer
                  and str(r.get("at", "")).startswith(period))
        if counts:
            total += int(r["amount"])
    return total


def chain_ok(receipts):
    chain = Chain()
    chain.receipts = receipts
    try:
        return chain.verify()[0]
    except (KeyError, TypeError):
        return False


def judge(reported, receipts, synchronizer, period):
    """One party: (verdict, bytes the party holds or None)."""
    if receipts is None:
        return NO_RECORD, None
    if not chain_ok(receipts):
        return BROKEN, None
    held = held_bytes(receipts, synchronizer, period)
    if reported == held:
        return MATCH, held
    return (OVER if reported > held else UNDER), held


def compare(report, records, tolerance=0):
    synchronizer, period, total, rows = read_report(report)
    out = {"synchronizer": synchronizer, "period": period, "parties": {},
           "sum_matches_total": sum(rows.values()) == total, "total": total}
    for party in sorted(set(rows) | set(records)):
        reported = rows.get(party, 0)
        verdict, held = judge(reported, records.get(party), synchronizer, period)
        if verdict in (OVER, UNDER) and held is not None and abs(reported - held) <= tolerance:
            verdict = MATCH
        out["parties"][party] = {"reported": reported, "held": held, "verdict": verdict}
    return out


def coverage(result):
    """Share of the reported traffic whose row a party's own record confirmed."""
    total = result["total"]
    confirmed = sum(p["reported"] for p in result["parties"].values()
                    if p["verdict"] == MATCH)
    return 100.0 * confirmed / total if total else 0.0


def disagreements(result):
    bad = [p for p, v in result["parties"].items() if v["verdict"] in (OVER, UNDER)]
    return bad, not result["sum_matches_total"]


def _demo_records(synchronizer, period):
    at = period + "-05T10:00:00Z"
    sizes = {"alice::demo": [60, 40], "bob::demo": [120], "carol::demo": [80]}
    return {p: make_chain(synchronizer, [(at, s) for s in ev]) for p, ev in sizes.items()}


def demo_inputs(misdirect=0):
    """MOCKED: three parties on one synchronizer. misdirect moves bytes bob -> alice."""
    synchronizer, period = "sync-demo", "2026-12"
    rows = [{"party": "alice::demo", "bytes": 100 + misdirect},
            {"party": "bob::demo", "bytes": 120 - misdirect},
            {"party": "carol::demo", "bytes": 80}]
    report = {"synchronizer": synchronizer, "period": period, "total_bytes": 300, "rows": rows}
    return report, _demo_records(synchronizer, period)


def control():
    """The tool must see a misdirection it was handed, or it refuses to speak."""
    honest = compare(*demo_inputs(0))
    bad = compare(*demo_inputs(40))
    verdicts = {p: v["verdict"] for p, v in bad["parties"].items()}
    return (all(v["verdict"] == MATCH for v in honest["parties"].values())
            and bad["sum_matches_total"]
            and verdicts == {"alice::demo": OVER, "bob::demo": UNDER, "carol::demo": MATCH})


def _rows(result):
    for party, v in result["parties"].items():
        held = "-" if v["held"] is None else str(v["held"])
        print("  %-14s reported %-6d held %-6s %s" % (party, v["reported"], held, v["verdict"]))


def _summary(result):
    bad, sum_off = disagreements(result)
    print("  row sum equals the reported total: %s" % ("yes" if not sum_off else "NO"))
    print("  confirmed by a party's own record: %.1f%% of reported traffic" % coverage(result))
    unchecked = [p for p, v in result["parties"].items() if v["verdict"] in UNCHECKED]
    if unchecked:
        print("  UNCHECKED (rests on the operator): " + ", ".join(unchecked))
    print("DISAGREEMENT: " + ", ".join(bad) if bad or sum_off
          else "no disagreement among the parties that could be checked")


def render(result):
    print("synchronizer %s, period %s, reported total %d bytes"
          % (result["synchronizer"], result["period"], result["total"]))
    _rows(result)
    _summary(result)
    print("DOES NOT PROVE:")
    for line in LIMITS:
        print("  - " + line)


def run(report, records, tolerance=0):
    if not control():
        print("CONTROL FAILED: the tool did not catch a misdirection it was handed. "
              "No verdict is given.")
        return 3
    print("control passed: a misdirection with an unchanged total is caught.\n")
    result = compare(report, records, tolerance)
    render(result)
    bad, sum_off = disagreements(result)
    return 1 if bad or sum_off else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("report", nargs="?", help="operator report, JSON")
    ap.add_argument("--records", help="party records, JSON")
    ap.add_argument("--tolerance", type=int, default=0, help="bytes of difference allowed")
    ap.add_argument("--demo", action="store_true", help="run on MOCKED data, honest then misdirected")
    args = ap.parse_args(argv)
    if args.demo:
        print("MOCKED DATA. An honest report first, then one that moves 40 bytes from bob to alice.\n")
        first = run(*demo_inputs(0))
        print("\n" + "=" * 60 + "\n")
        second = run(*demo_inputs(40))
        return 0 if (first, second) == (0, 1) else 3
    if not (args.report and args.records):
        ap.error("give REPORT.json and --records RECORDS.json, or use --demo")
    try:
        with open(args.report) as f:
            report = json.load(f)
        with open(args.records) as f:
            records = json.load(f).get("records", {})
        return run(report, records, args.tolerance)
    except (OSError, ValueError, AttributeError) as err:
        print("bad input: %s" % err)
        return 2


if __name__ == "__main__":
    sys.exit(main())
