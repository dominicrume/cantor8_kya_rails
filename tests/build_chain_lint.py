#!/usr/bin/env python3
"""Every local DAR a package needs must be built before it, in the chain.

    python3 tests/build_chain_lint.py

WHY THIS EXISTS. On 14 November 2026 the command in an application cover
letter, `python3 tools/prove_refusal_on_sandbox.py`, was run from a clean clone
for the first time and failed on its first step:

    damlc: ../.daml/dist/kya-rails-mandate-1.1.1.dar: openBinaryFile:
    does not exist

The test package named a DAR that the mandate package builds, and .daml/ is
build output that git ignores. The tool built one package of two. It had
passed on the author's machine every time, because that machine already held
the file.

Nothing in this repository could have caught it. tools/unpublished.py checks
that a promised file answers 200 on GitHub, and never that the promised
command runs. This checks the one thing that went wrong: tools/canton_sandbox.py
names the packages a tool builds, in order, and each package's daml.yaml names
the DARs it depends on. If a package depends on a local DAR that nothing
earlier in its chain produces, a stranger's clone cannot build it.

It reads the daml.yaml files and does not build anything, so it takes no time
and needs no Daml SDK.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import canton_sandbox  # noqa: E402

fails = []


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


def top_level(text, key):
    m = re.search(r"^%s:\s*(\S+)" % key, text, re.M)
    return m.group(1) if m else None


def local_dars(text):
    """DAR paths this package lists as dependencies, ignoring comments."""
    live = [l for l in text.splitlines() if not l.lstrip().startswith("#")]
    return re.findall(r"^\s*-\s*(\S+\.dar)\s*$", "\n".join(live), re.M)


def lint_chain(label, chain):
    """Walk a chain in order, tracking which DARs exist by each step."""
    print("%s: %s" % (label, " -> ".join(chain)))
    built = set()
    for rel in chain:
        path = os.path.join(ROOT, rel, "daml.yaml")
        if not os.path.exists(path):
            check(False, "%s has no daml.yaml, so it cannot be built" % rel)
            continue
        text = open(path).read()
        for dep in local_dars(text):
            want = os.path.normpath(os.path.join(ROOT, rel, dep))
            check(want in built,
                  "%s needs %s, built earlier in this chain"
                  % (rel, os.path.relpath(want, ROOT)))
        name, version = top_level(text, "name"), top_level(text, "version")
        built.add(os.path.normpath(os.path.join(
            ROOT, rel, ".daml", "dist", "%s-%s.dar" % (name, version))))


def main():
    lint_chain("MANDATE_CHAIN", canton_sandbox.MANDATE_CHAIN)
    lint_chain("REFUSAL_CHAIN", canton_sandbox.REFUSAL_CHAIN)
    print("")
    if fails:
        print("FAILED: %d. A stranger's clone cannot build this chain." % len(fails))
        return 1
    print("every chain builds from source, in an order a clean clone can follow.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
