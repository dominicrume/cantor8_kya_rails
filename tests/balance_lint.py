#!/usr/bin/env python3
"""The float adds up, and every count in the README is still the true one.

Two failures this catches, and the second is the one that had already
happened twice.

**Coin that does not balance.** The strongest claim in this repository is that
a mandate-authorised transfer moved real Amulet and the account the agent was
told to redirect to received nothing. That is arithmetic, so it can be checked
rather than believed: opening total against closing total, and the unverified
party at zero on both sides. A README that says "total conserved" is a claim;
a table whose columns are re-added on every run is evidence.

**Numbers that drift away from the thing they describe.** The README said the
mutation suite broke 23 real things when it broke 37, and that the store suite
ran 42 checks when it ran 43. Nobody edited those lines wrongly -- the lines
stopped being true because the code around them grew. Every count in a document
is a claim about a file, and an unchecked claim about a file is the exact thing
this project exists to be careful about. So each one is re-derived here from
the file that produces it.

The same failure lived in `tests/devnet_check.py`, where `NEEDED = 3.5` came
from payouts of 2.0 and 1.5 that had become 0.2 and 0.1. It told an operator
holding 1.4 CC that a 0.3 CC run was unaffordable. That constant now reads
agent.py, and this file checks that it does.

Run: python3 tests/balance_lint.py
"""
import json
import os
import re
import subprocess  # nosec B404 - runs this repo's own suites to count their checks
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BALANCES = os.path.join(ROOT, "docs", "devnet-balances.json")
README = os.path.join(ROOT, "README.md")

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def parties(side):
    return {k: v for k, v in side.items() if k != "_"}


def cell(x):
    """A README figure as a number: strips bold, minus signs of either kind."""
    return float(x.replace("*", "").replace("−", "-").replace("+", "").strip())


# ---------------------------------------------------------------- the float
print("the float, either side of a real transfer")
d = json.load(open(BALANCES))
opening, closing = parties(d["opening"]), parties(d["closing"])

check(set(opening) == set(closing), "the same parties on both sides")
o_total, c_total = sum(opening.values()), sum(closing.values())
check(abs(o_total - c_total) < 1e-9,
      "no coin created or lost: %.4f in, %.4f out" % (o_total, c_total))
check(o_total > 0, "there was a float to move in the first place")

unv = [k for k in opening if "unverified" in k]
check(len(unv) == 1, "the unverified party is named in the record")
for k in unv:
    check(opening[k] == 0.0 and closing[k] == 0.0,
          "%s holds 0.0 on BOTH sides -- the redirect moved nothing" % k)

moved_out = sum(max(0.0, opening[k] - closing[k]) for k in opening)
moved_in = sum(max(0.0, closing[k] - opening[k]) for k in opening)
check(abs(moved_out - moved_in) < 1e-9,
      "what left the wallets equals what arrived (%.4f)" % moved_out)

# ------------------------------------------------- the table says the same
print()
print("the README's table is that record, cell for cell")
md = open(README).read()
rows = re.findall(r"^\| *[`*]*([\w-]+)[`*]* *\| *([\d.*\u2212+-]+) *\| *([\d.*\u2212+-]+) *\|",
                  md, re.M)
tabled = {name: (cell(op), cell(cl)) for name, op, cl in rows if name in opening}
check(len(tabled) == len(opening),
      "every party in the record has a row (%d of %d)" % (len(tabled), len(opening)))
for name, (op, cl) in sorted(tabled.items()):
    check(op == opening[name] and cl == closing[name],
          "%s reads %.4f -> %.4f, as recorded" % (name, op, cl))

totals = re.search(r"^\| *\*\*Total\*\* *\| *\*\*([\d.]+)\*\* *\| *\*\*([\d.]+)\*\*", md, re.M)
check(bool(totals), "the table carries a total row")
if totals:
    check(abs(float(totals.group(1)) - o_total) < 1e-9
          and abs(float(totals.group(2)) - c_total) < 1e-9,
          "the printed totals are the sums, not typed separately")

# ------------------------------------------------------------- the counts
print()
print("every count in the README is still the true one")


def rows_in(path, pattern):
    return len(re.findall(pattern, open(os.path.join(ROOT, path)).read(), re.M))


def ran(cmd):
    r = subprocess.run([sys.executable, os.path.join(ROOT, cmd)],  # nosec B603 - our own suite
                       capture_output=True, text=True, cwd=ROOT, timeout=900)
    return r.stdout


def passes_in(cmd):
    """Run a suite and count the checks it actually reports."""
    return len(re.findall(r"^\s+(?:PASS|ok)\b", ran(cmd), re.M))


def stated_in(cmd, pattern):
    """A suite that counts something itself is asked for its own figure --
    re-deriving it here would be a second implementation to keep in step, and
    the whole point of this file is that those drift."""
    m = re.search(pattern, ran(cmd))
    return int(m.group(1)) if m else -1


CLAIMS = [
    (r"breaks \*\*(\d+)\*\* real things",
     lambda: rows_in("tests/mutation_suite.py", r'^    \("'),
     "mutation_suite rows"),
    # store_smoke and route_fuzz moved to the kya-desk repository on
    # 2026-09-12 with the desk they tested. The journal itself stayed, because
    # losing receipts when a process dies is an evidence problem, and
    # tests/journal_smoke.py is what covers it here.
    (r"\*\*(\d+)\*\* checks on the journal",
     lambda: passes_in("tests/journal_smoke.py"),
     "journal checks"),
    (r"now covers \*\*(\d+) of \d+\*\*",
     lambda: passes_in("tests/mutation_py.py"),
     "mutation_py refusals"),

    # Added after the README carried "92 / 92 daml test scripts" in five places
    # while the suite ran 100. Nothing checked it, so it was true once and then
    # quietly was not, in the row that tells a judge the ledger is tested. The
    # Daml count is read from tests/mutation.py's manifest and from a real run
    # rather than from a second written-down number.
    (r"\*\*(\d+) / \d+\*\* `daml test` scripts",
     lambda: daml_script_count(),
     "daml scripts"),
    (r"all \*\*(\d+)\*\* in the Daml",
     lambda: fence_count(),
     "daml fences under mutation"),

    # The README said 16 conformance vectors in three places, and the file had
    # 20. Four vectors were added across three commits and no line that quotes
    # the number was one of the files those commits touched, which is precisely
    # the failure mode this lint exists for.
    (r"\[(\d+) conformance vectors\]\(tests/vectors\.json\)",
     lambda: vector_count(),
     "conformance vectors"),
]
def vector_count():
    """How many conformance vectors there are, from the file itself."""
    import json
    with open(os.path.join(ROOT, "tests", "vectors.json")) as f:
        return len(json.load(f)["cases"])


def fence_count():
    """How many fences the mutation manifest covers, read from the manifest."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "mut_count", os.path.join(ROOT, "tests", "mutation.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return len(mod.FENCES)


def daml_script_count():
    """How many Daml scripts there are, counted by running them.

    Deliberately a real run and not a grep for `: Script ()`. A script that
    exists and does not run is not a script that passed, and this number is
    quoted to a judge as evidence that the ledger is tested. If the toolchain
    is missing this returns -1, which fails the check loudly rather than
    letting the README's number stand unexamined.
    """
    import subprocess  # nosec B404 - fixed argv, no shell
    import shutil
    if shutil.which("daml") is None:
        return -1
    test_dir = os.path.join(ROOT, "step-1-mandate", "test")
    subprocess.run(  # nosec B603 B607 - literal argv
        ["daml", "build", "--no-legacy-assistant-warning"],
        cwd=os.path.dirname(test_dir), capture_output=True)
    p = subprocess.run(  # nosec B603 B607 - literal argv
        ["daml", "test", "--no-legacy-assistant-warning"],
        cwd=test_dir, capture_output=True, text=True)
    return (p.stdout + p.stderr).count(": ok,")


for pattern, truth, label in CLAIMS:
    m = re.search(pattern, md)
    if not m:
        check(False, "%s: the README line this checks has been reworded" % label)
        continue
    said, real = int(m.group(1)), truth()
    check(said == real, "%s: README says %d, the file has %d" % (label, said, real))

# --------------------------------------------- the constant that was wrong
print()
print("the DevNet check reads the payouts instead of restating them")
dc = open(os.path.join(ROOT, "tests", "devnet_check.py")).read()
check("NEEDED = needed()" in dc,
      "NEEDED is derived, not a literal that can go stale")
check(not re.search(r"^NEEDED = [\d.]+", dc, re.M),
      "  and no hardcoded threshold has crept back in")

print()
if fails:
    print("FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("the float balances, the unverified account got nothing, and every number")
print("the README shows a judge is still the number its file produces.")
