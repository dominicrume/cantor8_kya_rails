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


def counts(receipts):
    return Counter(r["outcome"] for r in receipts)


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
           "%d fence(s) checked with %s." % (len(receipts), tools), ""]
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
    emit("fences", len(receipts))
    emit("covered", c.get("COVERED", 0))
    emit("uncovered", c.get("UNCOVERED", 0))
    emit("head", receipts[-1]["seal"])
    emit("record", os.path.abspath(path))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
