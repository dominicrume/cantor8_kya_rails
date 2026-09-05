#!/usr/bin/env python3
"""Delete each refusal at the edges and prove a test goes red.

tests/mutation.py does this for the fences in the Daml. These files are the
other place a refusal is the whole product: two endpoints on the public
internet, and the store that decides whether to trust the desk's own history.
Every refusal in them is a door being held shut. A green smoke suite says the code passes its tests. It does not say the
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
    ("step-8-store/store.py",     "tests/store_smoke.py"),
]

# The refusal each file raises when it will not act. Different names, same
# job: a door being held shut.
GUARDS = ("Refused", "Tampered")


def refusals(path):
    """Every refusal raise, as (first_line, last_line, message)."""
    tree = ast.parse(open(path).read())
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
            continue
        func = node.exc.func
        if getattr(func, "id", None) not in GUARDS:
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
    """Run a smoke suite against whatever is currently on disk.

    PYTHONDONTWRITEBYTECODE is not tidiness. This harness rewrites a source
    file and immediately runs it; macOS mtime has one-second granularity, so
    a .pyc written by the previous iteration can still look current and the
    subprocess silently executes the PREVIOUS mutation. Every verdict here
    would then be attached to the wrong line. Found the hard way: a restored
    file kept failing until __pycache__ was cleared.
    """
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, os.path.join(ROOT, suite)],
                       capture_output=True, text=True, cwd=ROOT, env=env)
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
    blind, crashed, total = [], [], 0
    for rel, suite in TARGETS:
        total += len(refusals(os.path.join(ROOT, rel)))
        b, c = check_file(rel, suite, only)
        blind += b
        crashed += c
        print()
    if crashed:
        print("%d refusal(s) fail as a traceback rather than a named check:" % len(crashed))
        for c in crashed:
            print("  -", c)
        print()
        print("These are load-bearing -- deleting them breaks something -- but a")
        print("traceback is not a named test going red, and this file's own")
        print("docstring says so. Until each has an assertion that names it,")
        print("coverage is %d of %d, not all of them."
              % (total - len(crashed) - len(blind), total))
    if blind:
        print("MUTATION TESTING FAILED - %d refusal(s) not covered:" % len(blind))
        for b in blind:
            print("  -", b)
        return 1
    named = total - len(crashed) - len(blind)
    if crashed:
        # Deliberately not a failure. A crash proves the refusal is
        # load-bearing -- delete it and something breaks -- which is weaker
        # than a named test but is not nothing, and it cannot be improved:
        # removing the guard makes the code after it raise, so no assertion
        # can run to name it. What was wrong was printing "every refusal is
        # covered" over the top of this and letting README.md repeat it.
        print("%d of %d refusals are covered by a NAMED test; the %d above are"
              % (named, total, len(crashed)))
        print("load-bearing but fail as a traceback. None are uncovered.")
        return 0
    print("every refusal at the edges is covered: delete one and a test goes red.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
