#!/usr/bin/env python3
"""The action does what its README promises, and cannot quietly stop.

An action is a contract with people who will never read its source. Three
things in it can rot without anything going red, and each is checked here.

**The inputs and outputs it advertises.** A renamed output is a broken
workflow in somebody else's repository, discovered by them, not us.

**The files it invokes.** The composite steps call `tools/assurance.py` and
`tools/assurance_report.py` by path through `$GITHUB_ACTION_PATH`. Move or
rename either and the action fails on a stranger's runner with a Python
traceback, while every suite here stays green.

**That it refuses rather than misleads.** Without the Daml assistant there is
nothing to mutate, and the action must say so plainly instead of reporting a
package with no findings -- which is what "0 uncovered" would read as.

The report generator is checked against a real sealed record, because its whole
job is to describe one, and it must never round an uncovered fence away.

Run: python3 tests/action_smoke.py
"""
import json
import os
import re
import subprocess  # nosec B404 - runs this repo's own report generator
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ACTION = os.path.join(ROOT, "action.yml")
RECORD = os.path.join(ROOT, "docs", "findings",
                      "canton-contracts-access-control-v1.json")

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


spec = open(ACTION).read()

print("the action advertises what callers depend on")
for name in ("src", "test", "subject", "out", "fail-on-uncovered"):
    check(re.search(r"^  %s:" % re.escape(name), spec, re.M) is not None,
          "input `%s` is declared" % name)
for name in ("fences", "covered", "uncovered", "head", "record"):
    check(re.search(r"^  %s:\n    description:" % re.escape(name), spec, re.M) is not None,
          "output `%s` is declared" % name)
check("using: composite" in spec,
      "it is a composite action: no container to build, nothing to pin")
check('default: "false"' in spec,
      "fail-on-uncovered defaults OFF -- a check red on day one is disabled on day two")

print()
print("every file the action invokes is really there")
called = re.findall(r'\$GITHUB_ACTION_PATH/([\w/.\-]+)', spec)
check(len(called) >= 2, "it invokes at least the two tools (%d found)" % len(called))
for rel in sorted(set(called)):
    check(os.path.exists(os.path.join(ROOT, rel)),
          "%s exists, so the action will not die on a stranger's runner" % rel)

print()
print("it refuses without Daml instead of reporting nothing found")
check("command -v daml" in spec, "it checks for the Daml assistant")
check("::error title=daml not found::" in spec, "  and fails with a named error, not a traceback")
i_check, i_run = spec.find("command -v daml"), spec.find("tools/assurance.py")
check(0 < i_check < i_run, "  and does so BEFORE anything is mutated")

print()
print("the record travels with the run")
check("actions/upload-artifact@v4" in spec, "the sealed record is uploaded")
check("if-no-files-found: error" in spec,
      "  and a missing record fails the step rather than passing quietly")

print()
print("the report describes a real record without softening it")
out = tempfile.mkstemp(suffix=".out")[1]
summ = tempfile.mkstemp(suffix=".md")[1]
env = dict(os.environ, GITHUB_OUTPUT=out, GITHUB_STEP_SUMMARY=summ)
r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "assurance_report.py"),  # nosec B603
                    RECORD], capture_output=True, text=True, env=env)
check(r.returncode == 0, "it runs against the committed OpenZeppelin record")

vals = dict(l.split("=", 1) for l in open(out).read().splitlines() if "=" in l)
receipts = json.load(open(RECORD))
real_unc = sum(1 for x in receipts if x["outcome"] == "UNCOVERED")
check(vals.get("fences") == str(len(receipts)), "fences output matches the record")
check(vals.get("uncovered") == str(real_unc),
      "uncovered output is the real count (%d), not a rounded one" % real_unc)
check(vals.get("head") == receipts[-1]["seal"],
      "head output is the record's head seal, in full")

body = open(summ).read()
check(body.count("|") > 6, "the summary carries a table of the uncovered fences")
for x in receipts:
    if x["outcome"] == "UNCOVERED":
        check(x["amount"] in body and x["payee"] in body,
              "%s:%s appears in the summary a reviewer reads" % (x["payee"], x["amount"]))
check("not vulnerabilities" in body,
      "the summary says these are not vulnerabilities, in CI, not only in the README")
check(receipts[-1]["seal"][:16] in body,
      "the head seal is shown, so the artifact can be matched to this run")

print()
print("an empty record is refused, never reported as clean")
empty = tempfile.mkstemp(suffix=".json")[1]
open(empty, "w").write("[]")
r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "assurance_report.py"),  # nosec B603
                    empty], capture_output=True, text=True)
check(r.returncode != 0, "exits non-zero on an empty record")
check("Nothing was checked" in r.stdout, "  and says nothing was checked")

print()
if fails:
    print("FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("the action is callable by a stranger, and says what it found without")
print("softening it or pretending it ran when it could not.")
