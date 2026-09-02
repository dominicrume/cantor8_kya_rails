#!/usr/bin/env python3
"""Delete each refusal in the webhook adapters and prove a test goes red.

tests/mutation.py does this for the fences in the Daml. These two files are
the other place a refusal is the whole product: they are the endpoints on the
public internet, and every `raise Refused(...)` in them is a door being held
shut. A green smoke suite says the code passes its tests. It does not say the
tests would notice if a door were left open.

The mutation: replace one `raise Refused(...)` with `pass`, so the guard
evaluates and then does nothing, and run that adapter's smoke suite. It must
fail. Three outcomes are reported:

  ok     the suite went red -- the refusal is covered
  BLIND  the suite still passed -- nothing tests that refusal
  crash  the suite errored rather than failing a named check. The refusal is
         load-bearing but the failure is a traceback, not an assertion, so it
         is reported separately rather than counted as coverage.

Run: python3 tests/mutation_py.py            (a few seconds per refusal)
     python3 tests/mutation_py.py signature  (only refusals matching a word)
"""
import ast, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = [
    ("step-7-providers/meta.py",  "tests/meta_smoke.py"),
    ("step-7-providers/breet.py", "tests/breet_smoke.py"),
]


def refusals(path):
    """Every `raise Refused(...)`, as (first_line, last_line, message)."""
    tree = ast.parse(open(path).read())
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
            continue
        func = node.exc.func
        if getattr(func, "id", None) != "Refused":
            continue
        out.append((node.lineno, node.end_lineno, describe(node.exc)))
    return sorted(out)


def describe(call):
    """The literal part of the refusal message, enough to name it in output."""
    for arg in call.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value.split("%")[0].strip() or "<formatted>"
        if isinstance(arg, ast.BinOp) and isinstance(arg.left, ast.Constant):
            return str(arg.left.value).split("%")[0].strip()
    return "<no literal message>"


def neutralise(path, first, last):
    """Replace one raise with `pass`, keeping the file's line count."""
    lines = open(path).read().splitlines(True)
    indent = len(lines[first - 1]) - len(lines[first - 1].lstrip())
    lines[first - 1] = " " * indent + "pass\n"
    for i in range(first, last):
        lines[i] = "\n"
    open(path, "w").writelines(lines)


def run(suite):
    r = subprocess.run([sys.executable, os.path.join(ROOT, suite)],
                       capture_output=True, text=True, cwd=ROOT)
    return r.returncode, (r.stdout + r.stderr)


def classify(code, out):
    if code == 0:
        return "BLIND"
    return "ok" if "FAILED" in out else "crash"


def check_one(path, suite, first, last, message):
    neutralise(path, first, last)
    code, out = run(suite)
    verdict = classify(code, out)
    print("  %-5s line %-4d %s" % (verdict, first, message[:52]))
    return verdict


def check_file(rel, suite, only):
    path = os.path.join(ROOT, rel)
    print("%s -> %s" % (rel, suite))
    found = refusals(path)
    blind, crashed = [], []
    backup = tempfile.mkstemp(suffix=".py")[1]
    shutil.copy(path, backup)
    try:
        for first, last, message in found:
            if only and only not in message:
                continue
            shutil.copy(backup, path)
            verdict = check_one(path, suite, first, last, message)
            if verdict == "BLIND":
                blind.append("%s:%d %s" % (rel, first, message))
            elif verdict == "crash":
                crashed.append("%s:%d %s" % (rel, first, message))
    finally:
        shutil.copy(backup, path)
        os.unlink(backup)
    return blind, crashed


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    blind, crashed = [], []
    for rel, suite in TARGETS:
        b, c = check_file(rel, suite, only)
        blind += b
        crashed += c
        print()
    if crashed:
        print("%d refusal(s) fail as a traceback rather than a named check:" % len(crashed))
        for c in crashed:
            print("  -", c)
        print()
    if blind:
        print("MUTATION TESTING FAILED - %d refusal(s) not covered:" % len(blind))
        for b in blind:
            print("  -", b)
        return 1
    print("every refusal in the webhook adapters is covered: delete one and a "
          "test goes red.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
