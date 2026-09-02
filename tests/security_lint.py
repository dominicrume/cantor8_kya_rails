#!/usr/bin/env python3
"""Bandit, with production code held to zero.

This is the metric the auditor reports, run directly so the number can be
broken down instead of quoted. The rule is asymmetric on purpose:

  production code   -> zero findings, no exceptions
  test harnesses    -> subprocess and urlopen are what a harness IS, and
                       flagging them measures how thoroughly a codebase is
                       tested, then reports it as a security score

Every allowance below names the rule and why. An allowance without a reason
is how a security check becomes decoration.

Run: python3 tests/security_lint.py
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Rules a test harness necessarily trips, allowed ONLY inside tests/.
TEST_ALLOWED = {
    "B101": "assert IS the test",
    "B404": "importing subprocess is how a harness starts the thing under test",
    "B603": "subprocess with list args and no shell; the argv is ours",
    "B607": "partial path for `daml`, which lives wherever the SDK installed it",
    "B310": "urlopen against our own local test server, guarded by _http()",
}


def is_test(rel):
    name = rel.rsplit("/", 1)[-1]
    return (name.startswith("test_") or name.endswith("_test.py")
            or name == "conftest.py" or "/tests/" in "/" + rel or rel.startswith("tests/"))


def classify(results):
    """Split CWE-tagged findings into production and allowed-in-tests."""
    prod, allowed = [], []
    for i in results:
        if not (i.get("issue_cwe") or {}).get("id"):
            continue
        rel = os.path.relpath(i["filename"], ROOT)
        entry = "%s:%s %s %s" % (rel, i["line_number"], i["test_id"],
                                 i["issue_text"][:58])
        (allowed if is_test(rel) and i["test_id"] in TEST_ALLOWED
         else prod).append(entry)
    return prod, allowed


def main():
    proc = subprocess.run(["bandit", "-r", ROOT, "-f", "json", "-q"],
                          capture_output=True, text=True, check=False)
    if not proc.stdout.strip():
        print("bandit produced no output"); return 1
    results = json.loads(proc.stdout).get("results", [])

    prod, allowed = classify(results)

    print("bandit: %d counted findings" % (len(prod) + len(allowed)))
    print("  %d in test harnesses (allowed, each rule justified in this file)"
          % len(allowed))
    print("  %d in production code" % len(prod))
    if prod:
        print()
        for e in prod:
            print("  FAIL", e)
        print("\nProduction code must be clean. Fix it, or if it is genuinely")
        print("safe, add a `# nosec <RULE> - <reason>` on the line saying why.")
        return 1
    print("\n  PASS production code is clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
