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
    # BOTH packages. canton-refusal-record is separate on purpose, and a count
    # that reads only the mandate is a count of the wrong thing: the README
    # said 111 and this said 103 the moment the second package existed.
    #
    # IN DEPENDENCY ORDER, and the order is load-bearing. step-0-refusal
    # data-depends on interface/.daml/dist/canton-journal-interface-1.0.0.dar,
    # so on a clean checkout that package cannot build until the interface has.
    # This used to skip the interface and ignore `daml build`'s exit code, so
    # on CI the build failed, `daml test` found nothing, the total came back
    # 103 instead of 165, and the message blamed the README:
    #
    #     FAIL daml scripts: README says 165, the file has 103
    #
    # The README was right. Three commits were spent on a number that was
    # never wrong, because a swallowed exit code was reported as a bad claim.
    # A build that fails now returns -1 and says so.
    total = 0
    for pkg in ("step-1-mandate",
                os.path.join("step-0-refusal", "interface"),
                "step-0-refusal"):
        built = subprocess.run(  # nosec B603 B607 - literal argv
            ["daml", "build", "--no-legacy-assistant-warning"],
            cwd=os.path.join(ROOT, pkg), capture_output=True, text=True)
        if built.returncode != 0:
            print("    daml build failed in %s:" % pkg)
            print("      " + (built.stderr or built.stdout).strip()[-300:])
            return -1
        test_dir = os.path.join(ROOT, pkg, "test")
        if not os.path.isdir(test_dir):
            continue          # the interface package has no test package
        p = subprocess.run(  # nosec B603 B607 - literal argv
            ["daml", "test", "--no-legacy-assistant-warning"],
            cwd=test_dir, capture_output=True, text=True)
        total += (p.stdout + p.stderr).count(": ok,")
    return total


for pattern, truth, label in CLAIMS:
    m = re.search(pattern, md)
    if not m:
        check(False, "%s: the README line this checks has been reworded" % label)
        continue
    said, real = int(m.group(1)), truth()
    check(said == real, "%s: README says %d, the file has %d" % (label, said, real))

# ------------------------------------------- the download figure, everywhere
# Added 2026-11-10. STATUS.md carried "84 real downloads a month excluding
# mirrors" for 24 days. It was never produced by a tool; the only cache in the
# tree was 47 days old and counted mirrors, so it could not have been the
# source. The true figure was 226, so the repository was understating itself by
# nearly 3x in the one file whose job is to be true.
#
# This reads docs/evidence/downloads.json, which tools/downloads.py writes, and
# never the network, because it runs inside the pre-commit hook. It also fails
# when that cache goes stale, since a gate that happily checks prose against a
# three-month-old measurement is theatre.
print()
print("every download figure in prose matches the last measurement")
DL = os.path.join(ROOT, "docs", "evidence", "downloads.json")
if not os.path.exists(DL):
    check(False, "docs/evidence/downloads.json is missing; run tools/downloads.py")
else:
    with open(DL) as f:
        dl = json.load(f)
    check(dl.get("mirrors_excluded") is True,
          "the cache states mirrors are excluded (the old one did not)")

    from datetime import date as _date
    y, m, d = (int(x) for x in dl["measured"].split("-"))
    age = (_date.today() - _date(y, m, d)).days
    check(age <= 45,
          "the measurement is %d days old, inside the 45-day limit" % age)

    want30, wantall = dl["window_30d"]["downloads"], dl["all_time"]
    DOWNLOAD_PROSE = ["STATUS.md", "docs/opportunities.md", "docs/accomplished.md",
                      "docs/evidence/index.md", "docs/dev-fund-proposal.md"]
    # \s+ not a literal space: "226\nin the thirty days" is the same claim and
    # the first version of this regex silently skipped the one file where the
    # number happened to fall at a line break. A gate that quietly matches
    # nothing is the failure it was built to stop.
    pat30 = re.compile(r"(\d[\d,]*)\s+(?:downloads\s+)?in\s+the\s+(?:30|thirty)\s+days")
    for rel in DOWNLOAD_PROSE:
        text = open(os.path.join(ROOT, rel)).read()
        said = set(int(n.replace(",", "")) for n in pat30.findall(text))
        if not said:
            check(False, "%s: no 30-day download figure found; has the line "
                         "been reworded out of the gate's sight?" % rel)
            continue
        check(said == {want30},
              "%s: says %s in the last 30 days, the measurement is %d"
              % (rel, " and ".join(str(n) for n in sorted(said)), want30))
        if "all time" in text:
            alls = set(int(n.replace(",", "")) for n in
                       re.findall(r"(\d[\d,]*)\s+(?:downloads\s+)?all time", text))
            bad = alls - {wantall, dl["all_time_including_mirrors"]}
            check(not bad,
                  "%s: all-time figures %s agree with the measurement (%d "
                  "excluding mirrors, %d including)"
                  % (rel, sorted(alls) or "none", wantall,
                     dl["all_time_including_mirrors"]))

# ------------------------------- the same number, in the files the README is not
# Found 2026-11-09 while extracting the domain knowledge into .claude/skills/.
# The CLAIMS loop above reads README.md only, and its pattern matches the
# markdown-link form `[20 conformance vectors](tests/vectors.json)`. So the
# README was right and SPEC.md line 390 and tools/dashboard.py both still said
# 16, against 20 cases in tests/vectors.json. Four vectors were added across
# three commits and neither of those files was touched by any of them.
#
# A gate that guards one file is not a gate on the number. These two are named
# explicitly rather than walking the tree, so adding a third place that quotes
# the figure is a deliberate act that shows up in a diff.
print()
print("the vector count is the same number everywhere it is written down")
VECTOR_PROSE = ["SPEC.md", "tools/dashboard.py", "README.md"]
for rel in VECTOR_PROSE:
    text = open(os.path.join(ROOT, rel)).read()
    found = set(int(n) for n in re.findall(r"(\d+) conformance vectors", text))
    if not found:
        check(False, "%s: no longer quotes the vector count at all" % rel)
        continue
    real = vector_count()
    check(found == {real},
          "%s: quotes %s conformance vectors, the file has %d"
          % (rel, " and ".join(str(n) for n in sorted(found)), real))

# ----------------------------- the vote figures, in every file that states them
# Added 2026-11-10. The research document was re-measured and the figures
# moved: 27 votes became 29, and "three failed" became seven once the tool
# counted vote EVENTS instead of labels. Two other files still said 27 and
# six: STATUS.md and .claude/skills/ecosystem-mechanics/SKILL.md. The skill is
# the worse of the two, because that is the file an agent reads to decide what
# to do, and for a day it taught that #866 had died when #866 had a live vote.
#
# So the number is pinned to the document that carries the working, and every
# other file that states it must agree. The source of truth is
# docs/dev-fund-vote-mechanism.md, and that document says to re-run
# tools/vote_pipeline.py before quoting anything from it.
#
# This gate does NOT call GitHub. A lint that needs the network fails on a
# plane and gets disabled. It checks only that the files agree with each
# other, which is the failure that actually happened.
print()
print("the Dev Fund vote figures agree across every file that states them")
VOTE_SOURCE = "docs/dev-fund-vote-mechanism.md"
VOTE_PROSE = ["STATUS.md", ".claude/skills/ecosystem-mechanics/SKILL.md"]


def votes_opened(text):
    """Every count of votes ever opened that a file states."""
    pats = [r"all (\d+) votes in the repository",
            r"\*\*All (\d+) votes were opened",
            r"(\d+) of 400 proposals have ever reached a vote",
            r"\*\*(\d+) have ever reached a vote",
            r"@hythloda (\d+) times out of"]
    out = set()
    for pat in pats:
        out.update(int(n) for n in re.findall(pat, text))
    return out


WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
         "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def as_int(token):
    """A count written as a digit or as an English word, up to ten."""
    return int(token) if token.isdigit() else WORDS[token.lower()]


def votes_failed(text):
    """Every count of failed votes that a file states, digits or words.

    Both files spell it "Seven votes have failed", so a digit-only pattern
    found nothing and the gate passed while checking nothing. A check that
    cannot see the thing it guards is worse than no check, because it reports
    PASS.
    """
    found = re.findall(r"\b(\d+|[A-Za-z]+) votes? ha(?:ve|s) "
                       r"(?:actually )?failed", text)
    return set(as_int(t) for t in found if t.isdigit() or t.lower() in WORDS)


src = open(os.path.join(ROOT, VOTE_SOURCE)).read()
opened, failed = votes_opened(src), votes_failed(src)
check(len(opened) == 1,
      "%s states one vote count, not %s"
      % (VOTE_SOURCE, sorted(opened) or "none"))
check(len(failed) == 1,
      "%s states one failed-vote count, not %s"
      % (VOTE_SOURCE, sorted(failed) or "none"))
for rel in VOTE_PROSE:
    text = open(os.path.join(ROOT, rel)).read()
    here = votes_opened(text)
    if not here:
        check(False, "%s: no longer states the vote count at all" % rel)
        continue
    check(here == opened,
          "%s: says %s votes opened, %s says %s"
          % (rel, " and ".join(str(n) for n in sorted(here)),
             VOTE_SOURCE, " and ".join(str(n) for n in sorted(opened))))
    hf = votes_failed(text)
    check(not hf or hf == failed,
          "%s: says %s votes failed, %s says %s"
          % (rel, " and ".join(str(n) for n in sorted(hf)),
             VOTE_SOURCE, " and ".join(str(n) for n in sorted(failed))))

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
