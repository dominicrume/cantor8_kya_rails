#!/usr/bin/env python3
"""Every fence the mutation harness knows about must be present in the source.

This exists because of a specific accident that is easy to have. Running
`python3 tests/mutation.py` deletes one fence at a time from the contracts and
puts it back afterwards. While it runs -- and it runs for a long time -- the
working tree contains a contract with a spending rule missing. Committing at
that moment ships a hole, and the diff looks like a one-line deletion in a
file nobody was editing.

So this check reads the fence list out of the harness and requires every one
of them to be in its file. It takes no time and needs no build, so it runs
first in CI and can be run by hand before any commit:

    python3 tests/fence_lint.py

It also catches the quieter version of the same problem: a fence renamed or
reworded in the Daml while the harness still looks for the old text. The
harness would report SKIP for that fence and carry on, so a rule could stop
being tested without anything going red.
"""
import importlib.util, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "mut", os.path.join(ROOT, "tests", "mutation.py"))
mut = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mut)


def main():
    missing = []
    seen = {}
    for path, fence, guard in mut.FENCES:
        text = seen.get(path)
        if text is None:
            text = seen[path] = open(path).read()
        found = text.count(fence)
        if found == 0:
            missing.append("%s: %r is not in %s"
                           % (guard, fence, os.path.relpath(path, ROOT)))
        elif found > 1:
            # Present twice is not safer than present once, it is worse. The
            # harness proves a fence matters by deleting it and requiring a
            # named test to go red. Delete one of two identical copies and the
            # code still compiles, the test still passes, and the fence is
            # reported covered while nothing is testing it.
            #
            # This is not hypothetical. refusalReason repeats every rule of
            # Charge as text so the ledger record can name the rule that fired,
            # and for one commit "charge would exceed the cap" appeared twice
            # in KyaMandate.daml. Deleting the fence left fence_lint green.
            missing.append(
                "%s: %r appears %d times in %s, so deleting it proves nothing. "
                "Give this entry the whole line rather than the phrase."
                % (guard, fence, found, os.path.relpath(path, ROOT)))
    print("fence lint: %d fences across %d contracts" % (len(mut.FENCES), len(seen)))
    if missing:
        print("  FAIL")
        for m in missing:
            print("    - " + m)
        print("\n  If tests/mutation.py is running right now, that is why: it "
              "deletes\n  one fence at a time. Wait for it to finish and do "
              "not commit until\n  this passes. Otherwise a spending rule has "
              "been removed or reworded\n  and the harness is no longer "
              "testing it.")
        return 1
    print("  PASS every fence is present in the contract it belongs to")
    return 0


if __name__ == "__main__":
    sys.exit(main())
