#!/usr/bin/env python3
"""The journal notices being edited, and a killed process loses nothing.

step-8-store is the sealed SQLite journal receipts are written to. It stayed in
this repository when the desk moved out on 2026-09-12, because losing receipts
when a process dies is an evidence problem, not a desk feature: the MCP wallet
writes through to it, and tests/mcp_survives_kill.py is the reason it exists.

The wider suite that used to cover this also drove the desk's server, so it
went with the desk. What it proved about the JOURNAL is here, standing on its
own: an entry cannot be edited, an entry cannot be removed from the middle, and
a path that cannot be used says which mistake it is rather than raising.

Run: python3 tests/journal_smoke.py
"""
import os
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "step-8-store"))

from store import Store, Tampered, Unusable                  # noqa: E402

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def receipts(n):
    return [{"n": i + 1, "what": "payout %d" % (i + 1), "amount": "1.00",
             "payee": "acme", "currency": "USD", "outcome": "ACCEPTED",
             "rule": "inside the cap"} for i in range(n)]


print("the journal survives the process that wrote it")
d = tempfile.mkdtemp()
path = os.path.join(d, "desk.db")
s = Store(path)
for r in receipts(4):
    s.receipt(r)
s.close()

again = Store(path)
_state, _messages, back = again.restore()
check(len(back) == 4, "four receipts written, four read back after a reopen (%d)"
      % len(back))
check([r["what"] for r in back] == ["payout %d" % i for i in range(1, 5)],
      "  in the order they were written")
again.close()

print()
print("and notices being edited")
# Editing a row directly in SQLite is the realistic attack: the operator owns
# the file. The seal chain is what makes it detectable rather than the file
# permissions, which they also own.
con = sqlite3.connect(path)
con.execute("UPDATE journal SET data = REPLACE(data, 'payout 2', 'payout 9')")
con.commit()
con.close()
try:
    Store(path)
    check(False, "an edited journal is refused")
except Tampered as e:
    check(True, "an edited journal is refused (%s)" % str(e)[:44])

print()
print("and notices an entry removed from the middle")
d2 = tempfile.mkdtemp()
p2 = os.path.join(d2, "desk.db")
s2 = Store(p2)
for r in receipts(4):
    s2.receipt(r)
s2.close()
con = sqlite3.connect(p2)
con.execute("DELETE FROM journal WHERE n = 2")
con.commit()
con.close()
try:
    Store(p2)
    check(False, "a deletion from the middle is refused")
except Tampered as e:
    check(True, "a deletion from the middle is refused (%s)" % str(e)[:44])

print()
print("and a path it cannot use says which mistake it is")
# Not a traceback. An operator who typed a directory where a file goes should
# read what they did, not a stack.
bad = os.path.join(tempfile.mkdtemp(), "a-directory")
os.makedirs(bad)
try:
    Store(bad)
    check(False, "a directory where a file belongs is refused")
except Unusable as e:
    check("director" in str(e).lower() or "file" in str(e).lower(),
          "a directory where a file belongs says so (%s)" % str(e)[:52])
except Exception as e:                                # noqa: BLE001
    check(False, "raised %s instead of Unusable" % type(e).__name__)

print()
if fails:
    print("FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("what was written is still there, and what was changed cannot hide.")
