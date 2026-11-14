#!/usr/bin/env python3
"""Mutation-test the published package, on a copy of the repository.

    python3 tools/mutate_package.py

WHAT IT ANSWERS. The package `knowyouragenticai-receipts` is on PyPI and its
README says what its tests prove. This asks the harder question about those
tests: if the code were wrong in one small way, would any test notice? It makes
one small change at a time to the package source, runs the tests that import
it, and counts how many changes were noticed.

THE CHANGES, the classic ones, chosen because each is a plausible real bug:
  - a comparison flipped          == becomes !=, < becomes >=, in becomes not in
  - and swapped for or, and back
  - a `not` removed
  - True and False swapped
  - a `raise` replaced by `pass`  (the error path that silently stops erroring)

WHAT A SURVIVOR MEANS, said before the numbers so they are not oversold. A
mutant that survives is a change no test noticed. That is either a gap in the
tests or an EQUIVALENT mutant: a change that does not alter behaviour, such as
flipping a comparison whose two branches do the same thing. This tool cannot
tell those apart, so it reports the score as killed over total and lists every
survivor with its file and line, unclassified. Anything quoted from the result
must say "unclassified survivors" unless somebody has read them.

THREE THINGS IT DOES FIRST, because a harness that can only report success
cannot tell you whether it ran:
  1. It copies the repository to a temporary directory and only ever writes
     there. The real working tree is never touched. (tests/mutation_suite.py
     mutates the real tree in place and takes about an hour; this does not.)
  2. BASELINE: every test must pass on the unmutated copy. If one does not,
     nothing below means anything and it refuses to report.
  3. CONTROL: a deliberately broken module must be KILLED. If it survives, the
     tests cannot see failure and it refuses to report.

WHY A COPY MATTERS HERE. Every test inserts ROOT/pkg/src into sys.path, where
ROOT comes from the test file's own location. Run from a copy, they import the
mutated copy. Run from the real tree, they would import the real package and
every mutant would "survive" for the wrong reason.

Stdlib only, per THE-RULES.md.
"""
import ast
import os
import shutil
# B404 is suppressed below: running the tests is this tool's whole job.
import subprocess  # nosec B404
import sys
import queue
import tempfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join("pkg", "src", "knowyouragenticai_receipts")
MODULES = ["__init__.py", "disclose.py", "policy.py", "guard.py"]
# EVERY test in the repository that imports the package, found with
#     grep -l knowyouragenticai_receipts tests/*.py
# minus tests/mutation_suite.py, which mutates the real tree in place. The
# first version of this tool listed four of them and left out package_smoke
# and release_readiness, which test BrokenChain, NonAsciiInReceipt, Refused
# and the guard decorator. 42 of 145 mutants "survived" that incomplete list,
# several of them on exactly those lines. A survivor means nothing unless the
# suite it survived is complete, so this list is stated and checkable.
# Fast tests first, so a killed mutant stops early.
SUITES = ["tests/policy_smoke.py", "tests/assurance_level_smoke.py",
          "tests/disclosure_smoke.py", "tests/completeness_smoke.py",
          "tests/package_smoke.py", "tests/release_readiness.py",
          "tests/package_failure_paths_smoke.py"]
WORKERS = 4
TIMEOUT = 60
# Free copies of the repository. A worker takes one, mutates and tests in it,
# and puts it back. The first version tagged each job with a copy by index,
# but threads do not run in index order, so two could mutate the same copy at
# once and corrupt each other's result.
FREE = queue.Queue()

CMP = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.GtE, ast.LtE: ast.Gt,
       ast.Gt: ast.LtE, ast.GtE: ast.Lt, ast.Is: ast.IsNot, ast.IsNot: ast.Is,
       ast.In: ast.NotIn, ast.NotIn: ast.In}
BOOL = {ast.And: ast.Or, ast.Or: ast.And}


class One(ast.NodeTransformer):
    """Apply the Nth mutation site and no other. target -1 only counts."""

    def __init__(self, target):
        self.target, self.n, self.where = target, -1, None

    def _hit(self, node, what):
        self.n += 1
        if self.n != self.target:
            return False
        self.where = (node.lineno, what)
        return True

    def visit_Compare(self, node):
        self.generic_visit(node)
        for k, op in enumerate(node.ops):
            if type(op) in CMP and self._hit(node, "comparison flipped"):
                node.ops[k] = CMP[type(op)]()
        return node

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        if self._hit(node, "and/or swapped"):
            node.op = BOOL[type(node.op)]()
        return node

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.Not) and self._hit(node, "`not` removed"):
            return node.operand
        return node

    def visit_Constant(self, node):
        if isinstance(node.value, bool) and self._hit(node, "True/False swapped"):
            return ast.copy_location(ast.Constant(value=not node.value), node)
        return node

    def visit_Raise(self, node):
        self.generic_visit(node)
        if self._hit(node, "raise replaced by pass"):
            return ast.copy_location(ast.Pass(), node)
        return node


def count_sites(source):
    """How many mutation sites a module has. target -1 never applies one."""
    walker = One(-1)
    walker.visit(ast.parse(source))
    return walker.n + 1


def mutate(source, target):
    """The source with mutation site `target` applied, and where it was."""
    walker = One(target)
    tree = walker.visit(ast.parse(source))
    ast.fix_missing_locations(tree)
    return ast.unparse(tree), walker.where


def run(argv, cwd):
    """Run one test in the copy. True when it passed."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
               PYTHONPATH=os.path.join(cwd, "pkg", "src"))
    try:
        # B603: literal argv built from this file's own constants, shell=False.
        r = subprocess.run(  # nosec B603
            [sys.executable] + argv, cwd=cwd, env=env, capture_output=True,
            timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return False        # a mutant that hangs is noticed, not survived
    return r.returncode == 0


def first_failure(cwd):
    """The first test that fails in this copy, or None if all pass."""
    for suite in SUITES:
        if not run([suite], cwd):
            return suite
    if not run(["-m", "knowyouragenticai_receipts", "selftest"], cwd):
        return "selftest (20 vectors)"
    return None


def make_copy():
    ignore = shutil.ignore_patterns(".git", ".daml", "node_modules",
                                    "__pycache__", "log",
                                    ".mutation-in-progress")
    tmp = tempfile.mkdtemp(prefix="kya-mutate-")
    dest = os.path.join(tmp, "repo")
    shutil.copytree(ROOT, dest, ignore=ignore)
    return tmp, dest


def worker(job):
    """Apply one mutant in a copy no other worker is using, test, restore."""
    module, original, target = job
    dest = FREE.get()
    try:
        path = os.path.join(dest, PKG, module)
        source, where = mutate(original, target)
        with open(path, "w") as fh:
            fh.write(source)
        try:
            killer = first_failure(dest)
        finally:
            with open(path, "w") as fh:
                fh.write(original)
        return module, where, killer
    finally:
        FREE.put(dest)


def control(dest):
    """A broken module MUST be killed, or this harness cannot see failure."""
    path = os.path.join(dest, PKG, "policy.py")
    original = open(path).read()
    with open(path, "w") as fh:
        fh.write("raise SystemExit(1)\n")
    try:
        return first_failure(dest) is not None
    finally:
        with open(path, "w") as fh:
            fh.write(original)


def group(results):
    """Results grouped by module: {module: [(where, killer), ...]}."""
    by = {}
    for module, where, killer in results:
        by.setdefault(module, []).append((where, killer))
    return by


def table(by):
    """One line per module and a total. Counts only, no judgement."""
    total = dead = 0
    for module in MODULES:
        rows = by.get(module, [])
        k = sum(1 for _, killer in rows if killer)
        total, dead = total + len(rows), dead + k
        print("  %-14s %3d mutants, %3d noticed, %3d survived"
              % (module, len(rows), k, len(rows) - k))
    print("  %-14s %3d mutants, %3d noticed, %3d survived"
          % ("TOTAL", total, dead, total - dead))


def survivors(by):
    """Every mutant no test noticed, with its line. Not classified."""
    print("\nSURVIVORS, unclassified (a test gap, or an equivalent mutant):")
    for module in MODULES:
        for where, killer in by.get(module, []):
            if not killer and where:
                print("  %s:%d  %s" % (module, where[0], where[1]))


def report(results):
    by = group(results)
    print("")
    table(by)
    survivors(by)


def main():
    tmp, base = make_copy()
    try:
        print("working in a copy, the real tree is not touched: %s" % base)
        bad = first_failure(base)
        if bad:
            print("BASELINE FAILED on the unmutated copy: %s" % bad)
            print("Nothing below would mean anything. Refusing to report.")
            return 1
        print("baseline: every test passes on the unmutated copy")
        if not control(base):
            print("CONTROL FAILED: a broken module was NOT noticed.")
            print("These tests cannot see failure. Refusing to report.")
            return 1
        print("control: a deliberately broken module is noticed")
        jobs = plan(base, tmp)
        print("running %d mutants on %d workers" % (len(jobs), WORKERS))
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            report(list(pool.map(worker, jobs)))
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def plan(base, tmp):
    """One job per mutation site. Fills FREE with one copy per worker."""
    FREE.put(base)
    for i in range(1, WORKERS):
        dest = os.path.join(tmp, "repo%d" % i)
        shutil.copytree(base, dest)
        FREE.put(dest)
    jobs = []
    for module in MODULES:
        original = open(os.path.join(base, PKG, module)).read()
        for target in range(count_sites(original)):
            jobs.append((module, original, target))
    return jobs


if __name__ == "__main__":
    sys.exit(main())
