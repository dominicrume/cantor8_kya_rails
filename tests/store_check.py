#!/usr/bin/env python3
"""Inspect a desk journal: does it follow from itself, and what is in it?

The server refuses to start on a journal whose chain is broken, and points
here. This is the tool that says what happened rather than just that
something did.

    python3 tests/store_check.py               the default desk journal
    python3 tests/store_check.py path/to.db    a specific one

Exit code 0 if the journal verifies, 1 if it does not.
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "step-8-store"))
from store import Journal, Store


def summarise(journal):
    kinds, first, last = {}, None, None
    for n, at, kind, _data in journal.entries():
        kinds[kind] = kinds.get(kind, 0) + 1
        first = first or at
        last = at
    return kinds, first, last


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "kya-desk.db")
    if not os.path.exists(path):
        print("no journal at %s" % path)
        print("The desk has not been run with persistence, or this is the "
              "wrong path.")
        return 0

    journal = Journal(path)
    ok, bad = journal.verify()
    kinds, first, last = summarise(journal)
    print("journal: %s" % os.path.relpath(path, ROOT))
    print("  %d entries, %s to %s" % (journal.n, first or "-", last or "-"))
    for kind in sorted(kinds):
        print("    %-8s %d" % (kind, kinds[kind]))

    if not ok:
        report_broken(bad)
        return 1
    report_intact(path)
    return 0


def report_broken(bad):
    print()
    print("  BROKEN at entry %d." % bad)
    print("  Everything up to %d follows from itself. Entry %d does not, so"
          % (bad - 1, bad))
    print("  it or something before it was edited or removed after the fact.")
    print("  Entries after %d cannot be trusted either, because each one's" % bad)
    print("  seal is computed over the one before it.")
    print()
    print("  This does NOT tell you a payout was wrong. It tells you the")
    print("  desk's own record of it can no longer be relied on. The ledger")
    print("  is the authority: check the mandate and the quote on Canton.")


def report_intact(path):
    print()
    print("  INTACT. Every entry follows from the one before it, so nothing")
    print("  recorded has been altered or removed.")
    print("  Note what this does not say: an operator holding this file can")
    print("  still APPEND to it (threat model T22). Only the ledger stops that.")
    state, messages, receipts = Store(path).restore()
    deals = state.get("deals", {})
    print()
    print("  open deals: %d, messages: %d, receipts: %d"
          % (sum(1 for d in deals.values() if d.get("state") == "QUOTED"),
             len(messages), len(receipts)))


if __name__ == "__main__":
    sys.exit(main())
