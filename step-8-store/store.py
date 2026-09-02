#!/usr/bin/env python3
"""Persistence for the desk, so a quote outlives the process that issued it.

Until this existed, `Rail` said what it did in its own docstring: "one mandate,
one chain, for the life of the process." Every open deal, the whole receipt
chain and every conversation lived in a Python dict. Close the laptop between
the 10:02 quote and the 13:20 deposit and the payout account bound at quote
time was gone -- which is the exact fraud this system was built to stop,
reintroduced by a process restart.

WHAT THIS IS NOT. It is not a rule engine, and nothing here decides anything.
The rules live in the Daml (THE-RULES.md), the ledger enforces them, and this
is the desk's working copy plus its audit trail. A row in this file being
"correct" proves nothing on its own.

WHAT IT DOES GIVE YOU. The journal is append-only and seal-chained with the
same canonicalisation as the receipt chain -- `canonical()` and `seal()` are
imported from kya_chain rather than reimplemented, because two implementations
of one hash is how you get two answers. Editing history is therefore
detectable: `verify()` names the first entry that does not follow from the one
before it, and the server refuses to start on a tampered journal rather than
quietly trusting it.

It is a laptop database. An operator with the file can still append whatever
they like to the end, and there is no defence here against that -- see T22 in
the threat model. What it removes is the ability to change what was already
recorded without it showing.

Stdlib only: sqlite3 ships with Python (THE-RULES.md forbids pip).
"""
import json, os, sqlite3, sys, time

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "step-2-agent"))
from kya_chain import canonical, seal

SCHEMA = """
CREATE TABLE IF NOT EXISTS journal (
    n     INTEGER PRIMARY KEY,
    at    TEXT    NOT NULL,
    kind  TEXT    NOT NULL,
    data  TEXT    NOT NULL,
    prev  TEXT    NOT NULL,
    seal  TEXT    NOT NULL
);
"""


class Tampered(Exception):
    """The journal does not follow from itself. Someone edited history."""


class Journal:
    """An append-only, seal-chained log in SQLite."""

    def __init__(self, path):
        self.path = path
        # isolation_level=None: every statement commits as it runs. A desk
        # that loses the last write because the lid closed is the whole
        # problem this file exists to fix.
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript(SCHEMA)
        self.n, self.prev = self._tail()

    def _tail(self):
        row = self.db.execute(
            "SELECT n, seal FROM journal ORDER BY n DESC LIMIT 1").fetchone()
        return (row[0], row[1]) if row else (0, "GENESIS")

    @staticmethod
    def _body(n, at, kind, data_text, prev):
        """What gets sealed.

        `data` is the canonical TEXT as stored, not the reparsed object. Seal
        exactly the bytes on disk: a float that survives json round-tripping
        today may not on another interpreter, and the chain would then verify
        on the machine that wrote it and nowhere else. SPEC.md section 4 makes
        the same argument for why amounts are strings.
        """
        return {"n": n, "at": at, "kind": kind, "data": data_text, "prev": prev}

    def record(self, kind, data):
        """Append one entry. Returns its seal."""
        n = self.n + 1
        at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        text = canonical(data)
        s = seal(self._body(n, at, kind, text, self.prev), self.prev)
        self.db.execute(
            "INSERT INTO journal (n, at, kind, data, prev, seal) VALUES (?,?,?,?,?,?)",
            (n, at, kind, text, self.prev, s))
        self.n, self.prev = n, s
        return s

    def rows(self):
        return self.db.execute(
            "SELECT n, at, kind, data, prev, seal FROM journal ORDER BY n")

    def verify(self):
        """(ok, first_bad_n). 0 means the whole journal follows from itself."""
        prev, expect = "GENESIS", 1
        for n, at, kind, text, row_prev, row_seal in self.rows():
            if n != expect or row_prev != prev:
                return False, n
            if seal(self._body(n, at, kind, text, prev), prev) != row_seal:
                return False, n
            prev, expect = row_seal, n + 1
        return True, 0

    def entries(self, kind=None):
        """Every entry in order, decoded. Verify first: this does not."""
        for n, at, k, text, _prev, _seal in self.rows():
            if kind is None or k == kind:
                yield n, at, k, json.loads(text)

    def close(self):
        self.db.close()


class Store:
    """The desk's state, across restarts.

    Two shapes, because they have two lifetimes. Deals, quotes and settings
    are a SNAPSHOT: replay is one assignment and cannot drift from the logic
    that produced it. Messages and receipts are APPENDED: they only ever grow,
    and snapshotting them would rewrite the whole history on every keystroke.
    """

    SNAPSHOT, MESSAGE, RECEIPT = "state", "msg", "receipt"

    def __init__(self, path, strict=True):
        self.journal = Journal(path)
        ok, bad = self.journal.verify()
        if not ok and strict:
            raise Tampered(
                "journal entry %d does not follow from the one before it. "
                "This file has been edited. Refusing to load it: a desk that "
                "trusts an altered history is worse than one with none." % bad)
        self.intact = ok
        self.first_bad = bad
        self._last = None

    # -- writing -----------------------------------------------------------
    def snapshot(self, state):
        """Record the desk's state, but only when it actually changed."""
        text = canonical(state)
        if text == self._last:
            return None
        self._last = text
        return self.journal.record(self.SNAPSHOT, state)

    def message(self, entry):
        return self.journal.record(self.MESSAGE, entry)

    def receipt(self, entry):
        return self.journal.record(self.RECEIPT, entry)

    # -- reading -----------------------------------------------------------
    def restore(self):
        """(state, messages, receipts) as of the last thing recorded."""
        state, messages, receipts = {}, [], []
        for _n, _at, kind, data in self.journal.entries():
            if kind == self.SNAPSHOT:
                state = data
            elif kind == self.MESSAGE:
                messages.append(data)
            elif kind == self.RECEIPT:
                receipts.append(data)
        self._last = canonical(state) if state else None
        return state, messages, receipts

    def close(self):
        self.journal.close()
