#!/usr/bin/env python3
"""No statements after a return, and no method defined inside a constructor.

Both of these came from editing Python by string replacement: an insertion
landed in the middle of __init__, the lines after it became unreachable code
inside another method, and the server started but crashed on its first
request. The tests caught it; a syntax check could not, because it was
perfectly valid Python that did the wrong thing.

Run: python3 tests/deadcode_lint.py
"""
import ast, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {".git", "__pycache__", ".daml", "node_modules"}
bad = []

for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in SKIP]
    for fn in sorted(filenames):
        if not fn.endswith(".py"):
            continue
        rel = os.path.relpath(os.path.join(dirpath, fn), ROOT)
        try:
            tree = ast.parse(open(os.path.join(dirpath, fn)).read())
        except SyntaxError as e:
            bad.append("%s: does not parse (%s)" % (rel, e.msg))
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for i, stmt in enumerate(node.body[:-1]):
                if isinstance(stmt, (ast.Return, ast.Raise)):
                    nxt = node.body[i + 1]
                    bad.append("%s:%d unreachable after %s in %s()"
                               % (rel, nxt.lineno,
                                  type(stmt).__name__.lower(), node.name))

print("dead-code lint over the repository")
for b in bad:
    print("  FAIL", b)
if bad:
    print("\n%d unreachable statement(s)." % len(bad))
    sys.exit(1)
print("  PASS nothing unreachable")
