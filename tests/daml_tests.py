#!/usr/bin/env python3
"""Run the Daml suite, from the float, against the source rather than an artefact.

tools/dashboard.py already ran `daml test` and already gated on its exit code,
so this is not a suite that was missing. What it was doing is running from the
test package without rebuilding the mandate first, which means it checked
whatever DAR happened to be sitting on disk. Edit a spending fence, run the
dashboard, watch it go green against the old code.

The README says the cap is enforced in Daml and that a cap checked in Python is
a suggestion. If that is true, this is the most important suite here, and it was
the one reading a build artefact instead of the file a person just changed.

On this SDK `daml test` does exit non-zero when a script fails, which was worth
checking rather than assuming: an earlier version of this docstring asserted the
opposite. The output is still parsed, for the case the exit code cannot express
-- zero scripts run. A compile error or a renamed module can leave a suite that
ran nothing, and a suite that ran nothing is not a suite that passed.

Run: python3 tests/daml_tests.py
"""
import os
import re
import shutil
import subprocess  # nosec B404 - fixed argv, no shell
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEST = os.path.join(ROOT, "step-1-mandate", "test")

if shutil.which("daml") is None:
    print("the Daml suite cannot run: no `daml` on PATH.")
    print()
    print("This is a failure and not a skip. The spending rules are enforced in")
    print("step-1-mandate/daml/KyaMandate.daml, so a checkout that cannot build")
    print("it cannot check the one claim the rest of this repository rests on.")
    print("Install the SDK, or run the dashboard somewhere that has it.")
    sys.exit(1)

print("the ledger's own tests, which enforce what Python only reports")

# The parent DAR is rebuilt FIRST, and this is not an optimisation.
#
# step-1-mandate/test/daml.yaml takes the mandate as a data-dependency on a
# built artefact: ../.daml/dist/kya-rails-mandate-1.1.1.dar. So `daml test`
# checks whatever DAR is sitting on disk, not the source next to it. Edit a
# spending fence, run the tests, and they pass against the old code.
#
# tools/dashboard.py did run `daml test` before this file existed, and did gate
# on its exit code, so the suite was not missing. It ran the same way: from the
# test package, against the DAR already on disk. Both were reading an artefact
# rather than the source, which is why deleting the allow-list rule from
# refusalReason came back BLIND from the mutation harness. The same repository
# already has a commit called "The bundle I shipped was built from mutated
# source"; this is that mistake pointing the other way.
build = subprocess.run(  # nosec B603 B607 - literal argv, no shell
    ["daml", "build", "--no-legacy-assistant-warning"],
    cwd=os.path.dirname(TEST), capture_output=True, text=True)
if build.returncode != 0:
    print("  FAIL the mandate package does not compile")
    print()
    for line in (build.stdout + build.stderr).splitlines():
        if line.strip():
            print("  " + line)
    sys.exit(1)

r = subprocess.run(  # nosec B603 B607 - literal argv, no shell
    ["daml", "test", "--no-legacy-assistant-warning"],
    cwd=TEST, capture_output=True, text=True)
out = r.stdout + r.stderr

# One line per script: `daml/KyaTest.daml:testThing: ok, N active contracts...`
results = re.findall(r"^(\S+\.daml:\S+?):\s*(ok|fail)", out, re.MULTILINE)
bad = [name for name, verdict in results if verdict != "ok"]

# A compile error produces no result lines at all. The exit code covers that
# here, but zero scripts is worth failing on in its own right: it is the one
# outcome that looks like success from every angle except this one.
if not results:
    print("  FAIL no Daml scripts ran at all")
    print()
    for line in out.splitlines():
        if line.strip():
            print("  " + line)
    sys.exit(1)

by_file = {}
for name, verdict in results:
    by_file.setdefault(name.split(":")[0], []).append(verdict)
for path, verdicts in sorted(by_file.items()):
    ok = sum(1 for v in verdicts if v == "ok")
    print("  %-34s %d/%d" % (path, ok, len(verdicts)))

print()
if bad or r.returncode != 0:
    print("DAML SUITE FAILED - %d:" % len(bad))
    for name in bad:
        print("  - " + name)
    if not bad:
        print("  - daml test exited %d with every script ok, which means the"
              % r.returncode)
        print("    failure is in the build rather than in a script")
    sys.exit(1)
print("%d scripts, all green. The fences hold where they are enforced,"
      % len(results))
print("and a refusal is a contract on the ledger rather than a note we wrote.")
