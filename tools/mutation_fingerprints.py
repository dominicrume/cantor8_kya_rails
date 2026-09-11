#!/usr/bin/env python3
"""Is any mutation the suite knows how to make currently sitting in a file?

The mutation harness keeps its backups in a known directory, and the commit
hook refuses while that directory exists. That guards the case where a run
died. It does not guard the case where the directory is gone and a mutation is
still in a file -- which happened: the guard's own smoke test, executed as a
mutation row, shared the outer run's directory, deleted its backups, and the
outer run crashed before restoring. The hook's own guard line was left reading
`.never-exists`. The guard, disabled by its own test, one commit from shipping.

This asks the question the other way round. Every row in tests/mutation_suite.py
says exactly what it writes into which file. If that text is present and the
text it replaced is absent, a mutation is in the tree right now, whatever the
marker directory says.

    python3 tools/mutation_fingerprints.py        # silent, exit 0 = clean
    python3 tools/mutation_fingerprints.py -v     # say how many rows were checked

Rows that DELETE text (an empty replacement) cannot be fingerprinted by
presence and are skipped; the marker directory and heal() are what cover them.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tests"))


def rows():
    """The suite's own list of mutations, read as data rather than parsed."""
    import mutation_suite                                       # noqa: E402
    for value in vars(mutation_suite).values():
        if (isinstance(value, list) and value
                and isinstance(value[0], tuple) and len(value[0]) == 5):
            return value
    return []


def present(path, find, replace):
    """True if `replace` is in the file and `find` is not: the mutation is live."""
    try:
        cur = open(os.path.join(ROOT, path), encoding="utf-8", errors="replace").read()
    except OSError:
        return False
    if replace and replace in cur and find not in cur:
        return True
    return False


def leftovers():
    found = []
    for label, path, find, replace, _suite in rows():
        if present(path, find, replace):
            found.append((path, label))
    return found


def main(argv):
    found = leftovers()
    if "-v" in argv:
        print("checked %d mutation row(s); %d live" % (len(rows()), len(found)))
    for path, label in found:
        print("  - %s: %s" % (path, label))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
