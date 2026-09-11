#!/usr/bin/env python3
"""Turn a mutation run into a record the client can check without trusting you.

An audit firm hands over a PDF. A PDF is a claim: it says what was checked and
you believe it because of who signed it. If a finding is later softened, or one
quietly removed before the report goes to a regulator, nothing about the
document reveals that.

This produces the same thing the rest of this repository produces for payments:
a hash-chained record where every entry names what was checked, what was found,
and the rule that decided it -- and where removing one breaks every seal after
it. The client drops the file on the public verifier page and confirms nobody
edited the findings, including the auditor.

    python3 tools/assurance.py --src PKG --test PKG --for "Their Name"
    python3 tools/assurance.py --src PKG --test PKG --out findings.json

The entries a mutation run produces are exactly the shape a receipt wants: an
attempt, an outcome, and the rule that produced it. `amount` carries the line
number, `payee` the file, `ledger` the toolchain that answered. Reusing the
format rather than inventing a second one is the whole point -- the verifier
page, the three independent implementations and the conformance vectors all
work on this file already, and none of them had to be told about audits.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "step-2-agent"))
sys.path.insert(0, HERE)

from kya_chain import Chain                                    # noqa: E402
import daml_mutate                                             # noqa: E402


def toolchain():
    """What answered. A finding is only as good as the thing that produced it,
    so the version goes inside the seal rather than beside it."""
    ok, out = daml_mutate.daml(["version"], ROOT)
    for line in out.splitlines():
        if "default SDK version" in line or "project SDK version" in line:
            return "daml " + line.strip().split()[0]
    return "daml (version not reported)"


def stamp_one(chain, row, subject, tools):
    """One fence, one receipt. COVERED and UNCOVERED are both recorded: a report
    that lists only problems is a report nobody can tell apart from a short
    one."""
    state, where, detail = row
    outcome = {"ok": "COVERED", "UNCOVERED": "UNCOVERED",
               "BROKE": "NOT TESTABLE", "STALE": "NOT CHECKED"}.get(state, state)
    path, _, rest = where.partition(":")
    line, _, text = rest.partition("  ")
    return chain.stamp(
        what=text.strip()[:120] or "fence",
        amount=line.strip(),                  # the line number, as a string
        payee=path.strip(),                   # the file it lives in
        rule=detail[:160],
        outcome=outcome,
        approved_by="mutation testing: the condition was made vacuous and the "
                    "suite re-run",
        ledger=tools,
        currency="N/A",
        instrument=subject,
    )


def summary(rows):
    counts = {}
    for state, _w, _d in rows:
        counts[state] = counts.get(state, 0) + 1
    return counts


def run(src, test, subject, out_path, under=None):
    found = daml_mutate.fences(src, under)
    if not found:
        print("No fences in %s. Nothing to assure." % src)
        return 1

    print("assuring %s" % subject)
    compiled, base, _out = daml_mutate.build_and_test(src, test)
    if not compiled or not base:
        print("  the project does not build and test cleanly before any mutation.")
        return 2
    print("  %d fence(s), %d passing script(s). This takes a while.\n"
          % (len(found), len(base)))

    rows = daml_mutate.run_all(found, src, test, base)
    tools = toolchain()

    chain = Chain()
    for row in rows:
        stamp_one(chain, row, subject, tools)

    ok, bad = chain.verify()
    if not ok:
        print("\nthe record does not verify at entry %s. Refusing to write it." % bad)
        return 3

    with open(out_path, "w") as f:
        json.dump(chain.receipts, f, indent=2)
    report(rows, chain, out_path, subject, len(base))
    return 0


def report(rows, chain, out_path, subject, scripts):
    counts = summary(rows)
    print()
    print("%s -- %d fence(s) against %d passing script(s)" % (subject, len(rows), scripts))
    for state, label in (("ok", "covered by a named test"),
                         ("UNCOVERED", "NO test notices their removal"),
                         ("BROKE", "not testable"),
                         ("STALE", "not checked")):
        if counts.get(state):
            print("  %-3d %s" % (counts[state], label))
    print()
    print("wrote %s -- %d sealed entries, head %s"
          % (out_path, len(chain.receipts), chain.receipts[-1]["seal"][:16] + "..."))
    print()
    print("Hand that file to whoever commissioned this. They can check it on")
    print("https://dominicrume.github.io/cantor8_kya_rails/ with nothing installed.")
    print("If a finding is removed or softened afterwards, every seal after it")
    print("stops matching -- including by the person who wrote the report.")


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", required=True, help="the Daml package holding the contracts")
    ap.add_argument("--test", required=True, help="the package holding the test scripts")
    ap.add_argument("--for", dest="subject", help="who or what this is about")
    ap.add_argument("--out", default="findings.json", help="where to write the record")
    ap.add_argument("--under", help="mutate only files under this path inside --src; "
                                    "the project still builds from --src. A library whose "
                                    "tests live in the same tree needs this, or the run "
                                    "mutates the tests it is measuring.")
    a = ap.parse_args(argv)
    subject = a.subject or os.path.basename(os.path.abspath(a.src))
    return run(a.src, a.test, subject, a.out, a.under)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
