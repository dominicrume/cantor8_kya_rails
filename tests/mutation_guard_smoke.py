#!/usr/bin/env python3
"""A killed mutation run heals on the next one, and cannot be committed meanwhile.

The harnesses deliberately break files and put them back in a `finally`. A
SIGKILL -- a timeout, a closed laptop -- never runs a finally. In one night
that left a Daml spending fence deleted in the working tree, and then the D1
balances reading the opposite of the claim; the second was committed and
pushed, because the backups sat in a random temp directory and nothing at the
commit gate knew a run had been interrupted.

Four guards, and the fourth exists because the first three were not enough.

**Backups are somewhere the next run can find.** A known directory inside the
tree, with a manifest naming every file that is currently broken.

**The next run heals first.** Before a single new mutation, `heal()` puts back
everything the manifest names and removes the directory.

**The commit gate refuses while the directory exists,** and says which files.

**The commit gate also refuses while any known mutation is present in a
file** -- because the directory can be gone while a mutation is not. The first
version of this very test, run as a mutation row, shared the outer run's
directory, deleted its backups, and the outer run crashed before restoring.
The hook's own guard line was left reading `.never-exists`: the guard,
disabled by its own test, one commit from shipping. `tools/mutation_fingerprints.py`
asks the question the other way round and would have caught it.

This test is therefore written to run INSIDE a mutation run without touching
the outer run's directory: it never creates or removes `.mutation-in-progress`
when one already exists, and it heals only through an isolated directory of
its own.

Run: python3 tests/mutation_guard_smoke.py
"""
import json
import os
import shutil
import subprocess  # nosec B404 - runs this repo's own hook, harness and checker
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import mutation_suite as ms                                   # noqa: E402
import daml_mutate                                            # noqa: E402

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def run(*argv):
    r = subprocess.run(list(argv), cwd=ROOT,  # nosec B603 - our own scripts, literal argv
                       capture_output=True, text=True, timeout=300)
    return r.returncode, r.stdout + r.stderr


NESTED = os.path.isdir(ms.PROGRESS)     # an outer mutation run is live right now
PROBE = os.path.join(ROOT, ".guard-smoke-probe.txt")
README = os.path.join(ROOT, "README.md")
print("running %s an outer mutation run" % ("INSIDE" if NESTED else "outside"))

# ------------------------------------------------ 1. the marker directory
print()
print("the commit gate refuses while a run is in progress, and names a file")
made_marker = False
try:
    if NESTED:
        named = list(json.load(open(os.path.join(ms.PROGRESS, "manifest.json")))["files"])
    else:
        open(PROBE, "w").write("ORIGINAL\n")
        os.makedirs(ms.PROGRESS)
        made_marker = True
        bak = os.path.join(ms.PROGRESS, "000-probe.bak")
        shutil.copy(PROBE, bak)
        with open(os.path.join(ms.PROGRESS, "manifest.json"), "w") as f:
            json.dump({"started": "test", "files": {".guard-smoke-probe.txt": bak}}, f)
        open(PROBE, "w").write("MUTATED\n")           # ...and then the run was killed
        named = [".guard-smoke-probe.txt"]
    rc, out = run("bash", "tools/pre-commit")
    check(rc != 0, "tools/pre-commit exits non-zero (%d)" % rc)
    check("in progress, or was killed" in out,
          "  and says a mutation run is in progress or was killed")
    check(any(n in out for n in named), "  and names a file that is currently broken")
    check("heal" in out, "  and says how to heal it")
finally:
    if made_marker:
        shutil.rmtree(ms.PROGRESS, ignore_errors=True)
        if os.path.exists(PROBE):
            os.unlink(PROBE)

# ------------------------------------------------------- 2. heal, isolated
print()
print("the next run heals before it does anything else")
iso = tempfile.mkdtemp()
try:
    open(PROBE, "w").write("ORIGINAL\n")
    bak = os.path.join(iso, "000-probe.bak")
    shutil.copy(PROBE, bak)
    with open(os.path.join(iso, "manifest.json"), "w") as f:
        json.dump({"started": "test", "files": {".guard-smoke-probe.txt": bak}}, f)
    open(PROBE, "w").write("MUTATED\n")
    n = ms.heal(progress=iso)
    check(n == 1, "heal() put back %d file(s)" % n)
    check(open(PROBE).read() == "ORIGINAL\n", "  the probe is its original self again")
    check(not os.path.isdir(iso), "  and the in-progress directory is gone")
    check(ms.heal(progress=iso) == 0, "  a second heal on a clean tree does nothing, quietly")
finally:
    if os.path.exists(PROBE):
        os.unlink(PROBE)
    shutil.rmtree(iso, ignore_errors=True)

# ------------------------------------------ 3. the fingerprint check
print()
print("a mutation left in a file is caught even when the marker is gone")
original = open(README, encoding="utf-8").read()
if "**553** requests" not in original:
    print("  SKIP the README line this plants a mutation in has been reworded")
else:
    try:
        open(README, "w", encoding="utf-8").write(
            original.replace("**553** requests", "**500** requests", 1))
        rc, out = run(sys.executable, "tools/mutation_fingerprints.py")
        check(rc != 0, "mutation_fingerprints.py exits non-zero with a planted leftover")
        check("README.md" in out, "  and names the file carrying it")
    finally:
        open(README, "w", encoding="utf-8").write(original)
    rc, _ = run(sys.executable, "tools/mutation_fingerprints.py")
    check(rc == 0, "  and is silent again once the file is put back")

# ------------------------------------------- 4. the gate opens again
print()
if NESTED:
    print("the gate opening again is not testable inside a live run -- skipped")
else:
    print("and the gate opens again on an honest tree")
    rc, out = run("bash", "tools/pre-commit")
    check(rc == 0, "tools/pre-commit exits 0 once nothing is in progress (%d)" % rc)

# ------------------------------------------- 5. the foreign-repo harness
print()
print("the harness that runs on other people's code heals their tree too")
src = tempfile.mkdtemp()
os.makedirs(os.path.join(src, "daml"))
target = os.path.join(src, "daml", "Vault.daml")
open(target, "w").write('x = do\n  assertMsg "cap" (a <= cap)\n')
files = daml_mutate.backup_all({target}, src)
check(os.path.isdir(daml_mutate.progress_dir(src)),
      "backups go to a known directory inside the target")
check(list(files) == ["daml/Vault.daml"],
      "  the manifest names the file relative to the target")
open(target, "w").write("x = do\n  MUTATED\n")   # killed here
n = daml_mutate.heal(src)
check(n == 1, "heal(src) put back %d file(s)" % n)
check("MUTATED" not in open(target).read() and "assertMsg" in open(target).read(),
      "  the stranger's fence is back exactly as it was")
check(not os.path.isdir(daml_mutate.progress_dir(src)),
      "  and their tree carries no leftover directory")
check(daml_mutate.heal(src) == 0, "  healing a clean target does nothing")
rc, out = run(sys.executable, "tools/daml_mutate.py", "--src", src, "--test", src, "--heal")
check(rc == 0 and "nothing to heal" in out,
      "--heal is a real flag, and says when there is nothing to do")
shutil.rmtree(src, ignore_errors=True)

print()
print("the marker can never be committed by accident")
check(".mutation-in-progress/" in open(os.path.join(ROOT, ".gitignore")).read(),
      ".mutation-in-progress/ is ignored by git")

print()
if fails:
    print("FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("a run that dies leaves a map of what it broke; the next run reads the map")
print("first; and until then the commit gate refuses -- by the map, or by the")
print("mutation itself when the map is gone.")
