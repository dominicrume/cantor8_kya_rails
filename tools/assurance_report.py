#!/usr/bin/env python3
"""Turn a findings record into what CI shows a reviewer, and what it exports.

The record is the deliverable, but nobody reads JSON on a pull request. This
writes the run's summary into GitHub's own job summary, sets the outputs a
later step can branch on, and -- the part that matters -- prints the head seal
where the reviewer can see it, so the artifact they download can be matched
against the run that produced it.

    python3 tools/assurance_report.py findings.json

Deliberately separate from assurance.py: producing the record is a claim about
somebody's code, and formatting it is a claim about nothing. Keeping the second
out of the first means a change to how CI renders a table can never alter what
was sealed.
"""
import json
import os
import sys
from collections import Counter

LABEL = {
    "COVERED": "covered by a named test",
    "UNCOVERED": "**no test notices their removal**",
    "NOT TESTABLE": "not testable",
    "NOT CHECKED": "not checked",
}


FENCE_OUTCOMES = ("COVERED", "UNCOVERED", "NOT TESTABLE", "NOT CHECKED")


def counts(receipts):
    return Counter(r["outcome"] for r in receipts)


def fence_count(receipts):
    """Receipts that are about a fence. A record may also carry NOT SEEN and
    SCOPE receipts (written with --constructs all); counting those as fences
    would report checks nobody ran."""
    c = counts(receipts)
    return sum(c.get(k, 0) for k in FENCE_OUTCOMES)


def scope_lines(receipts):
    """What the record covers and what it does not, when it says. A record
    without a SCOPE receipt predates the generalised discovery and is described
    as such, never as complete."""
    scope = [r for r in receipts if r["outcome"] == "SCOPE"]
    if not scope:
        return []
    c = counts(receipts)
    seen = fence_count(receipts)
    return ["Scope: %d recognised; **%d check-like line(s) were not seen** and "
            "are listed in the record as NOT SEEN, each with a reason. "
            "Covered %d of the %d the tool could see." % (
                seen, c.get("NOT SEEN", 0), c.get("COVERED", 0), seen),
            "Helper names declared to be checks by whoever ran it: %s."
            % scope[0]["approved_by"].replace("named check helpers: ", ""), ""]


def table(receipts):
    """Only the uncovered ones, most-specific first. A CI summary listing all
    69 is a summary nobody reads."""
    bad = [r for r in receipts if r["outcome"] == "UNCOVERED"]
    if not bad:
        return ["", "Every fence is covered: making it vacuous turns a named test red."]
    out = ["", "| File | Line | Fence |", "|---|---:|---|"]
    for r in bad:
        out.append("| `%s` | %s | `%s` |"
                   % (r["payee"], r["amount"], r["what"].replace("|", "\\|")))
    return out


def lines(receipts, path):
    c = counts(receipts)
    subject = receipts[0].get("instrument", "the package")
    tools = receipts[0].get("ledger", "unknown toolchain")
    out = ["## Fence assurance — %s" % subject, "",
           "%d fence(s) checked with %s." % (fence_count(receipts), tools), ""]
    out += scope_lines(receipts)
    for k in ("COVERED", "UNCOVERED", "NOT TESTABLE", "NOT CHECKED"):
        if c.get(k):
            out.append("- **%d** %s" % (c[k], LABEL[k]))
    out += table(receipts)
    out += ["",
            "These are not vulnerabilities. Every fence is present and working; the",
            "finding is that the suite would not notice if one were removed.", "",
            "The record is sealed and chained — `%s`, head `%s`."
            % (os.path.basename(path), receipts[-1]["seal"][:16] + "…"),
            "Change one verdict and the chain breaks at that entry. Check it at",
            "<https://dominicrume.github.io/cantor8_kya_rails/> with nothing installed."]
    return out


def emit(name, value):
    """A GitHub Actions output, or stdout when run outside CI."""
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        print("%s=%s" % (name, value))
        return
    with open(path, "a") as f:
        f.write("%s=%s\n" % (name, value))


def main(argv):
    if not argv:
        print("usage: assurance_report.py <findings.json>")
        return 2
    path = argv[0]
    with open(path) as f:
        receipts = json.load(f)
    if not receipts:
        print("the record is empty. Nothing was checked.")
        return 2

    text = "\n".join(lines(receipts, path))
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(text + "\n")

    c = counts(receipts)
    emit("fences", fence_count(receipts))
    emit("covered", c.get("COVERED", 0))
    emit("uncovered", c.get("UNCOVERED", 0))
    emit("head", receipts[-1]["seal"])
    emit("record", os.path.abspath(path))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
