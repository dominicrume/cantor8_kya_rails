#!/usr/bin/env python3
"""Hold the line on complexity, and make every exception state its reason.

A mean is a soft number: it drifts, and it can be gamed by adding trivial
functions. This lint enforces two hard ones instead.

  1. CEILING. No function may exceed MAX_CC unless it is named in EARNED
     below with a written reason. A new complicated function fails the build.
  2. NO STALE EXEMPTIONS. Every entry in EARNED must still exist and must
     still be over the ceiling. Once a function is tidied its excuse goes with
     it, so the list cannot quietly become a graveyard of old apologies.

The metric is McCabe, computed here from the standard library `ast` because
this repository installs nothing (THE-RULES.md). It follows the usual model --
one point per branch, per loop, per except handler, per assert, per
comprehension and each of its filters, one per extra operand in a boolean
chain, one per match case -- but it is our own implementation and may differ
by a point from radon or any other tool on unusual code. That is the point of
writing it down: what is enforced is this file's number against this file's
ceiling, and both are visible right here rather than in a vendor's default.

    python3 tests/complexity_lint.py           check, non-zero exit on failure
    python3 tests/complexity_lint.py --report  every function, worst first

Run from anywhere; paths resolve relative to the repository root.
"""
import ast, os, sys

MAX_CC = 8
SKIP_DIRS = {".git", "__pycache__", ".daml", "node_modules", ".auditor"}

# Functions allowed above the ceiling, each with the reason it is earned.
# A reason must say why splitting it would make the code WORSE. "It is long"
# is not a reason, and the stale-exemption check deletes excuses that outlive
# their function.
EARNED = {
    "step-2-agent/agent.py:MockLedger.charge":
        "A flat chain of guards, one per assertion in KyaMandate.daml, in the "
        "same order. That correspondence is what makes this a mirror of the "
        "contract rather than an approximation of it, and a reader checking "
        "the two side by side is the only reason this class exists. Tidying "
        "it into helpers breaks the one property it has. Every branch is "
        "covered by tests/mutation.py, which deletes each fence in the Daml "
        "and requires a named test to go red.",
}

# `with` is deliberately absent: it is not a branch.
BRANCHING = (ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While,
             ast.ExceptHandler, ast.Assert)
FUNCS = (ast.FunctionDef, ast.AsyncFunctionDef)


def complexity(node):
    """McCabe for one function, not counting functions nested inside it.

    A nested def is reported as its own entry, so a closure's branches are
    never charged twice.
    """
    score = 1
    stack = list(ast.iter_child_nodes(node))
    while stack:
        n = stack.pop()
        if isinstance(n, FUNCS + (ast.ClassDef,)):
            continue                      # counted as its own entry
        if isinstance(n, BRANCHING):
            score += 1
        elif isinstance(n, ast.BoolOp):
            score += len(n.values) - 1
        elif isinstance(n, ast.comprehension):
            score += 1 + len(n.ifs)
        elif isinstance(n, ast.Match):
            score += len(n.cases)
        stack.extend(ast.iter_child_nodes(n))
    return score


def walk(tree, prefix=""):
    """Every function in a module, named the way a reader would name it."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            yield from walk(node, prefix + node.name + ".")
        elif isinstance(node, FUNCS):
            yield prefix + node.name, complexity(node)
            yield from walk(node, prefix + node.name + ".")


def sources(root):
    """Every .py file in the repository, as (absolute, repo-relative) pairs."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in sorted(filenames):
            if name.endswith(".py"):
                full = os.path.join(dirpath, name)
                yield full, os.path.relpath(full, root)


def scan(root):
    """Score every function. Unparseable files come back as failures, not as
    silently missing scores -- a file this lint cannot read is a file it
    cannot vouch for."""
    scores, unreadable = {}, []
    for full, path in sources(root):
        with open(full) as fh:
            try:
                tree = ast.parse(fh.read())
            except SyntaxError as e:
                unreadable.append("%s does not parse: %s" % (path, e))
                continue
        for name, cc in walk(tree):
            scores["%s:%s" % (path, name)] = cc
    return scores, unreadable


def over_ceiling_without_reason(over):
    for k in sorted(over):
        if k not in EARNED:
            yield ("%s is cc %d, over the ceiling, and has no written reason.\n"
                   "      Either simplify it, or add it to EARNED in this file "
                   "with the reason splitting it would make the code worse."
                   % (k, over[k]))


def stale_exemptions(scores, over):
    """An excuse must expire with the thing it excused."""
    for k in sorted(EARNED):
        if k not in scores:
            yield "%s is in EARNED but no longer exists. Remove the exemption." % k
        elif k not in over:
            yield ("%s is in EARNED but is now cc %d, under the ceiling. "
                   "Remove the exemption -- it is no longer earned." % (k, scores[k]))


def report(scores):
    for k, v in sorted(scores.items(), key=lambda kv: -kv[1])[:25]:
        print("  %3d  %s%s" % (v, k, "   [earned]" if k in EARNED else ""))
    print("\n  %d functions, mean %.2f, ceiling %d, %d earned exception(s)"
          % (len(scores), sum(scores.values()) / len(scores), MAX_CC, len(EARNED)))


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scores, fails = scan(root)
    if "--report" in sys.argv:
        report(scores)
        return 0
    over = {k: v for k, v in scores.items() if v > MAX_CC}
    fails += list(over_ceiling_without_reason(over))
    fails += list(stale_exemptions(scores, over))
    print("complexity lint: ceiling %d, %d earned exception(s)" % (MAX_CC, len(EARNED)))
    if fails:
        print("  FAIL")
        for f in fails:
            print("    - " + f)
        return 1
    print("  PASS every function is at or under %d, or says why not (worst: %d)"
          % (MAX_CC, max(scores.values(), default=0)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
