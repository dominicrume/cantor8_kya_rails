#!/usr/bin/env python3
"""Mutation testing for Daml authorisation fences, on any project.

"All tests pass" is a claim about agreement between code and tests, not about
protection. The two diverge silently and in one direction: a test written after
a fence, asserting the behaviour the fence already produces, passes whether or
not the fence is there.

`daml-lint` asks whether the source contains a known anti-pattern. `daml-props`
asks whether an invariant holds under generated inputs. `daml-verify` asks
whether a stated property can be proved. All three reason about the CONTRACT.
None can tell you the test guarding it is incapable of failing.

This deletes each fence in turn, rebuilds, and requires a NAMED test to die.
A fence whose removal leaves the suite green is reported as uncovered.

    python3 tools/daml_mutate.py --src PKG --test PKG
    python3 tools/daml_mutate.py --src PKG --test PKG --only "timelock"

Three things make a naive version worse than useless, and each is handled:

  a mutation whose text is not found proves nothing, so it is reported as STALE
  and exits non-zero rather than being counted as covered;

  a module that stops COMPILING is not the same as a test going red -- every
  test vanishes rather than one failing, and reporting that as coverage would
  be a lie. It is reported separately;

  a run that leaves a mutated source or a stale DAR behind corrupts every run
  after it, so sources are restored in a finally and the DAR is rebuilt from
  the restored source before exit.
"""
import argparse
import os
import re
import shutil
import subprocess  # nosec B404 - running daml IS what this tool does
import sys
import tempfile

FENCE = re.compile(r"^\s*(assertMsg|ensure)\b")


def daml(args, cwd):
    """(ok, output). Never raises: a build that explodes is a result."""
    try:
        p = subprocess.run(  # nosec B603 B607 - literal argv; daml is on PATH
            ["daml"] + args + ["--no-legacy-assistant-warning"],
            cwd=cwd, capture_output=True, text=True, timeout=1800)
        return p.returncode == 0, p.stdout + p.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, "could not run daml: %s" % e


def sources(pkg, under=None):
    """Every .daml file to consider, skipping build output.

    `under` separates WHERE THE PROJECT BUILDS from WHAT GETS MUTATED, and it
    exists because daml-finance needed it. Its root builds the whole thing, so
    --src must point there, but the tree also holds 28 fences inside test
    scripts and 22 in vendored packages. Making a test's own assertion vacuous
    breaks the test rather than testing the fence, and the result would have
    been reported as a finding against somebody else's code. A layout with one
    package and one daml/ directory never shows this; a real library does.
    """
    root = os.path.join(pkg, under) if under else os.path.join(pkg, "daml")
    root = root if os.path.isdir(root) else pkg
    out = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d != ".daml"]
        out += [os.path.join(dp, f) for f in sorted(fn) if f.endswith(".daml")]
    return out


def fences(pkg, under=None):
    """(path, line number, text) for every assertMsg and ensure in the source."""
    found = []
    for path in sources(pkg, under):
        for n, line in enumerate(open(path).read().splitlines(), 1):
            if FENCE.match(line):
                found.append((path, n, line.strip()))
    return found


def passing(out):
    """Named scripts that reported ok, as a set, so two runs can be compared."""
    return set(re.findall(r"^([\w/.]+:\w+): ok,", out, re.M))


def build_and_test(src, test):
    """(compiled, passing scripts, output).

    `compiled` is the BUILD's exit code and nothing else. The first version of
    this function returned the TEST command's exit code under that name, and
    `daml test` exits non-zero when a test goes red -- which is the outcome we
    are hunting for. Four of OpenZeppelin's seven fences were therefore
    reported as "the module stopped compiling" when what had actually happened
    was that their tests caught the mutation exactly as they should. It came
    within one step of being filed against their repository as a finding.
    """
    ok, out = daml(["build"], src)
    if not ok:
        return False, set(), out
    _test_rc, out = daml(["test"], test)      # non-zero here means a test FAILED
    return True, passing(out), out


def verdict(base, after, compiled):
    """What one neutered fence actually proved."""
    if not compiled:
        # Only a real compile failure reaches here now. Neutering a condition
        # should never cause one; if it does, say so rather than counting it
        # as covered or uncovered.
        return "BROKE", "the module stopped compiling -- not testable, not covered"
    died = base - after
    if died:
        return "ok", "%s goes red" % sorted(died)[0]
    return "UNCOVERED", "every test still passes without it"


def span(lines, i):
    """[start, end) of the statement beginning at line i.

    Daml uses layout: a statement continues while the following lines are
    indented MORE than it. This matters because assertions are commonly
    written across two lines --

        assertMsg "Input holding instrumentId does not match transfer"
          (hv.instrumentId == expectedInstrumentId)

    -- and a single-line mutation turns that into `assertMsg "Input True`,
    which is a syntax error. Thirty of thirty-two fences in OpenZeppelin's
    canton-token-template came back "stopped compiling" for exactly that
    reason, and every one was an artefact of the operator rather than a fact
    about their tests.
    """
    base = len(lines[i]) - len(lines[i].lstrip())
    j = i + 1
    while j < len(lines) and lines[j].strip():
        if len(lines[j]) - len(lines[j].lstrip()) <= base:
            break
        j += 1
    return i, j


def neutered(lines, i):
    """The whole statement replaced by one that refuses nothing.

    Not a rewrite of the condition -- the condition can be an arbitrary Haskell
    expression across several lines, and a regex has no business parsing one.
    Replacing the statement keeps the arity and the type and always compiles.
    """
    indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
    if re.match(r"^\s*assertMsg\b", lines[i]):
        return indent + 'assertMsg "mutated" True'
    if re.match(r"^\s*ensure\b", lines[i]):
        return indent + "ensure True"
    return None


def check_one(path, lineno, text, src, test, base):
    """Neuter one fence, rebuild, run, restore. Returns (state, detail)."""
    original = open(path).read()
    lines = original.splitlines()
    if not FENCE.match(lines[lineno - 1]):
        return "STALE", "line %d is no longer a fence" % lineno
    dead = neutered(lines, lineno - 1)
    if dead is None:
        return "STALE", "line %d does not match a fence shape" % lineno
    start, end = span(lines, lineno - 1)
    try:
        open(path, "w").write("\n".join(lines[:start] + [dead] + lines[end:]) + "\n")
        compiled, after, _ = build_and_test(src, test)
        return verdict(base, after, compiled)
    finally:
        open(path, "w").write(original)


def caveats(stale, broke):
    """The results that are not findings, said before the findings are."""
    if stale:
        print("%d STALE -- the harness pointed at something that is not a fence." % len(stale))
    if broke:
        print("%d could not be tested: the module stopped compiling, so no test" % len(broke))
        print("  could go red. That is not coverage, and not a finding either.")


def how_to_verify():
    """The trap that nearly turned an artefact into a report against somebody
    else's repository. Printed with every finding, not buried in a docstring."""
    print()
    print("Each one can be made vacuous and the suite still passes. Verify any of")
    print("them BY HAND before reporting it to anyone: neuter the line, check the")
    print("build EXITS ZERO and the DAR hash actually CHANGES, then run the tests.")
    print("A failed build leaves the old DAR in place and the suite then passes")
    print("against code the mutation never reached -- which reads exactly like a")
    print("finding and is not one.")


def buckets(rows):
    """(uncovered, broke, stale). Three outcomes that must not be blurred: a
    fence no test noticed, a fence that could not be tested, and a harness that
    pointed at the wrong line."""
    return tuple([r for r in rows if r[0] == state]
                 for state in ("UNCOVERED", "BROKE", "STALE"))


def report(rows, baseline_n):
    uncovered, broke, stale = buckets(rows)
    print()
    print("%d fence(s) checked against %d passing script(s)." % (len(rows), baseline_n))
    caveats(stale, broke)
    if uncovered:
        print()
        print("%d FENCE(S) NO TEST NOTICED:" % len(uncovered))
        for _s, where, _d in uncovered:
            print("  -", where)
        how_to_verify()
        return 1
    if stale or broke:
        return 1
    print("every fence is covered: making it vacuous turns a named test red.")
    return 0


def run_all(found, src, test, base):
    """Every fence in turn, with the sources restored whatever happens and the
    DAR rebuilt from the restored source before returning. A run that leaves
    either behind corrupts every run after it."""
    rows, backups = [], {}
    try:
        for path in {f[0] for f in found}:
            fd, tmp = tempfile.mkstemp(suffix=".daml")
            os.close(fd)
            shutil.copy(path, tmp)
            backups[path] = tmp
        for path, lineno, text in found:
            state, detail = check_one(path, lineno, text, src, test, base)
            where = "%s:%d  %s" % (os.path.basename(path), lineno, text[:52])
            print("  %-10s %-64s %s" % (state, where, detail[:40]))
            rows.append((state, where, detail))
    finally:
        for path, tmp in backups.items():
            shutil.copy(tmp, path)
            os.unlink(tmp)
        daml(["build"], src)
    return rows


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", required=True, help="the Daml package holding the contracts")
    ap.add_argument("--test", required=True, help="the package holding the test scripts")
    ap.add_argument("--only", help="only fences whose text contains this")
    ap.add_argument("--under", help="mutate only files under this path inside --src "
                                    "(the project still builds from --src)")
    a = ap.parse_args(argv)

    found = [f for f in fences(a.src, a.under) if not a.only or a.only in f[2]]
    if not found:
        print("No fences found in %s. Nothing was tested." % a.src)
        return 1

    print("baseline: building %s, testing %s" % (a.src, a.test))
    compiled, base, out = build_and_test(a.src, a.test)
    if not compiled or not base:
        print("  the project does not build and test cleanly before any mutation.")
        print(out[-1500:])
        return 2
    print("  %d script(s) pass. Now deleting %d fence(s), one at a time.\n"
          % (len(base), len(found)))

    rows = run_all(found, a.src, a.test, base)
    return report(rows, len(base))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
