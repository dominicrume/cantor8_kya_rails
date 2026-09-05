#!/usr/bin/env python3
"""The desk must survive the laptop closing between the quote and the deposit.

This is the failure this store was built for, so the first test is the fraud
itself: quote at 10:02, restart, deposit at 13:20, and at 14:05 a stranger
with a screenshot naming their own account. Before persistence the quote was
gone by 12:40 and there was nothing on the machine to contradict them.

The rest is what a persistent audit trail owes you: it must verify, it must
notice being edited, and it must be honest about the one thing it cannot stop.

Run: python3 tests/store_smoke.py
"""
import importlib.util, os, sqlite3, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in ("step-8-store", "step-7-providers", "step-6-whatsapp",
          "step-5-operator", "step-2-agent"):
    sys.path.insert(0, os.path.join(ROOT, p))
from store import Store, Journal, Tampered

ACCT = "GTB 0123456789 / CHIDI OKAFOR"
THIEF = "ZENITH 9988776655 / SOMEONE ELSE"
fails = []


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


def srv():
    """A fresh import, standing in for a fresh process."""
    spec = importlib.util.spec_from_file_location(
        "srv", os.path.join(ROOT, "step-5-operator", "server.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def rail_on(path):
    m = srv()
    r = m.Rail([], store=Store(path))
    return m, r


db = os.path.join(tempfile.mkdtemp(), "desk.db")
print("KYA Rails - does the desk survive the laptop closing?")

# --- the fraud, across a restart --------------------------------------------
_m, rail = rail_on(db)
rail.desk.approved = [ACCT]
deal = rail.cycle.open_deal("Chidi", "USDT", "TRC20", 10.0, 1250.0, ACCT,
                            None, rail.desk.approved)
ref, addr = deal["reference"], deal["depositAddress"]
rail.on_message("2348012345678", "hi")
rail.persist()
# os.path.exists was true the moment sqlite3.connect() ran, before anything
# was recorded -- it passed with Rail.persist() returning immediately. Count
# the rows instead.
import sqlite3 as _sq
_n = _sq.connect(db).execute("SELECT COUNT(*) FROM journal").fetchone()[0]
check(_n > 0, "10:02 the quote is written to disk as it is issued (%d entries)" % _n)

_m2, back = rail_on(db)                       # 12:40 the laptop sleeps
check(back.restored == 1, "12:40 after a restart the desk still holds 1 open deal")
check(ref in back.cycle.deals, "and it is the same deal reference")
check(back.cycle.deals[ref]["payoutAccount"] == ACCT,
      "14:05 the payout account bound at quote time survived the restart")
check(back.cycle.deals[ref]["depositAddress"] == addr,
      "and so did the address the customer was told to send to")
check(len(back.transcript) == 2, "the conversation survived too")

# The stranger. The desk can now contradict them, which is the entire point.
# `held != THIEF` compared the value against a string that is never written
# anywhere, so it survived the account being wiped to "". Assert what the
# quote actually still says, and that the desk refuses the stranger's claim.
held = back.cycle.deals[ref]["payoutAccount"]
check(held == ACCT, "the account on the restored quote is the one issued at 10:02")
check(back.cycle.pay(ref, THIEF, 10.0)["outcome"] == "REFUSED",
      "and the desk refuses a stranger naming their own account")

# --- the receipt chain survives and still verifies --------------------------
_m3, r3 = rail_on(db)
r3.chain.stamp("payout", 10.0, "Chidi", "inside the cap", "ACCEPTED",
               "principal", "MOCKED", "NGN", "naira")
r3.persist()
_m4, r4 = rail_on(db)
check(len(r4.chain.receipts) == 1, "a receipt written before the restart is still there")
ok, bad = r4.chain.verify()
check(ok, "and the restored chain still verifies end to end")

r4.chain.stamp("payout", 5.0, "Ngozi", "inside the cap", "ACCEPTED",
               "principal", "MOCKED", "NGN", "naira")
ok, bad = r4.chain.verify()
check(ok, "a receipt added AFTER the restore chains onto the restored one")

# --- the journal notices being edited ---------------------------------------
edit = os.path.join(tempfile.mkdtemp(), "edit.db")
_m5, r5 = rail_on(edit)
r5.desk.approved = [ACCT]
r5.cycle.open_deal("Chidi", "USDT", "TRC20", 10.0, 1250.0, ACCT, None, r5.desk.approved)
r5.persist()
r5.store.close()

con = sqlite3.connect(edit)
row = con.execute("SELECT n, data FROM journal WHERE kind='state' ORDER BY n LIMIT 1").fetchone()
con.execute("UPDATE journal SET data = REPLACE(data, ?, ?) WHERE n = ?",
            (ACCT, THIEF, row[0]))
con.commit(); con.close()

ok, bad = Journal(edit).verify()
check(not ok, "changing the payout account in the journal breaks the chain")
check(bad == row[0], "and verify names the exact entry that was edited")
try:
    Store(edit)
    opened = True
except Tampered:
    opened = False
check(not opened, "the store refuses to load an edited journal")

# --- deleting from the middle -----------------------------------------------
gap = os.path.join(tempfile.mkdtemp(), "gap.db")
_m6, r6 = rail_on(gap)
r6.desk.approved = [ACCT]
for who in ("Chidi", "Ngozi", "Emeka"):
    r6.cycle.open_deal(who, "USDT", "TRC20", 10.0, 1250.0, ACCT, None, r6.desk.approved)
    r6.persist()
r6.store.close()
con = sqlite3.connect(gap)
n_before = con.execute("SELECT COUNT(*) FROM journal").fetchone()[0]
con.execute("DELETE FROM journal WHERE n = 2"); con.commit(); con.close()
ok, bad = Journal(gap).verify()
check(not ok and n_before > 2, "deleting an entry from the middle is detected")

# --- the limit, proved rather than claimed ----------------------------------
# An operator holding the file can still APPEND. Nothing here stops that, and
# a test that pretends otherwise would be worse than no test. T22.
grow = os.path.join(tempfile.mkdtemp(), "grow.db")
_m7, r7 = rail_on(grow)
r7.desk.approved = [ACCT]
r7.cycle.open_deal("Chidi", "USDT", "TRC20", 10.0, 1250.0, ACCT, None, r7.desk.approved)
r7.persist()
forged = dict(r7.desk_state())
forged["deals"] = {k: dict(v, payoutAccount=THIEF) for k, v in forged["deals"].items()}
r7.store.snapshot(forged)                       # appended, correctly sealed
r7.store.close()
ok, bad = Journal(grow).verify()
check(ok, "a correctly sealed APPENDED entry still verifies -- this is T22, undefended")
state, _msgs, _r = Store(grow).restore()
check(list(state["deals"].values())[0]["payoutAccount"] == THIEF,
      "and the desk would load the appended account. The ledger is what stops this")

# --- ephemeral means ephemeral ----------------------------------------------
m8 = srv()
r8 = m8.Rail([], store=None)
r8.desk.approved = [ACCT]
r8.cycle.open_deal("Chidi", "USDT", "TRC20", 10.0, 1250.0, ACCT, None, r8.desk.approved)
r8.persist()
check(r8.restored == 0, "with no store, nothing is restored and nothing is written")
check(m8.build_store(["--ephemeral"]) is None, "--ephemeral disables the store")

# --- writes are not wasted --------------------------------------------------
quiet = os.path.join(tempfile.mkdtemp(), "quiet.db")
_m9, r9 = rail_on(quiet)
r9.persist(); r9.persist(); r9.persist()
con = sqlite3.connect(quiet)
n = con.execute("SELECT COUNT(*) FROM journal WHERE kind='state'").fetchone()[0]
con.close()
check(n == 1, "persisting an unchanged desk three times writes one entry")

# --- the operator can see which mode they are in ----------------------------
# An operator who does not know their deals are not being saved will find out
# at 13:20, which is too late.
m10 = srv()
eph = m10.Rail([], store=None).state()["storage"]
check(eph["mode"] == "EPHEMERAL", "the state API reports EPHEMERAL with no store")
check("NOT saved" in eph["warning"], "and carries a warning the screen can show")

_m11, r11 = rail_on(db)
saved = r11.state()["storage"]
check(saved["mode"] == "SAVED", "and reports SAVED when there is a journal")
check(saved["warning"] == "", "with no warning when the journal is intact")
check(saved["restored"] >= 1, "and says how many deals came back")

# A desk loaded from a tampered journal must SAY so on the screen, not just
# refuse at startup -- strict=False is how store_check.py inspects one.
_m12 = srv()
bad_store = Store(edit, strict=False)
r12 = _m12.Rail([], store=bad_store)
st = r12.state()["storage"]
check(st["intact"] is False, "a tampered journal reports intact=false to the screen")
check("do not trust" in st["warning"].lower(), "and the warning says not to trust it")

# --- a deal that came back from a restart, and died while away --------------
# The trap this closes: an operator opens a restarted desk, sees QUOTED and a
# "Deposit confirmed" button, and walks a dead quote all the way to DEPOSITED
# before pay refuses it -- by which point the customer's crypto has landed.
aged = os.path.join(tempfile.mkdtemp(), "aged.db")
_ma, ra = rail_on(aged)
ra.desk.approved = [ACCT]
old = ra.cycle.open_deal("Chidi", "USDT", "TRC20", 10.0, 1250.0, ACCT,
                         None, ra.desk.approved)
oref = old["reference"]
import time as _time
ra.cycle.deals[oref]["opened"] = _time.time() - 90000        # quoted yesterday
ra.cycle.deals[oref]["expiresAt"] = _time.time() - 3600      # ran out an hour ago
ra.persist()

_mb, rb = rail_on(aged)
card = [d for d in rb.state()["deals"] if d["reference"] == oref][0]
check(card["expired"] is True, "a quote that ran out while the desk was off comes back expired")
check(card["ageSeconds"] > 80000,
      "its age is measured from when it was QUOTED, not from the restart")
check(card["expiresInSeconds"] < 0, "and the time left is negative, not reset")

fresh_deal = rb.cycle.open_deal("Ngozi", "USDT", "TRC20", 5.0, 1250.0, ACCT,
                                None, rb.desk.approved)
live = [d for d in rb.state()["deals"] if d["reference"] == fresh_deal["reference"]][0]
check(live["expired"] is False, "a deal quoted after the restart is not expired")

# The screen refuses it because the desk does, and the desk because the Daml
# does. The fences fire in the contract's order, so walk the deal to where the
# expiry fence is the one that speaks.
check(rb.cycle.pay(oref, ACCT, 12500.0)["outcome"] == "REFUSED",
      "an expired deal cannot be paid straight from QUOTED")
rb.cycle.confirm_deposit(oref)
check(rb.cycle.deals[oref]["state"] == "DEPOSITED",
      "a late deposit can still be recorded -- the crypto arrived either way")
check(rb.cycle.pay(oref, ACCT, 12500.0)["rule"] == "quote expired",
      "and then the payout is refused in the contract's own words")

# --- no test may write into a real desk's journal ---------------------------
# Persistence is the server's default, so a test that spawns server.py without
# --ephemeral writes to kya-desk.db in the repository root -- the same file a
# real desk would be using. That happened: operator_smoke.py silently started
# restoring another test's deals.
#
# This reads the Popen CALL, not the file text. The first version searched the
# source for "--ephemeral" and passed on a comment that merely mentioned it,
# which is a test that cannot fail.
import ast as _ast, glob as _glob


def _spawn_args(src):
    """Every string constant passed to a subprocess.Popen(...) call."""
    out = []
    for node in _ast.walk(_ast.parse(src)):
        if not isinstance(node, _ast.Call):
            continue
        if getattr(node.func, "attr", None) != "Popen":
            continue
        for piece in _ast.walk(node):
            if isinstance(piece, _ast.Constant) and isinstance(piece.value, str):
                out.append(piece.value)
    return out


for _t in sorted(_glob.glob(os.path.join(ROOT, "tests", "*.py"))):
    _name = os.path.basename(_t)
    _src = open(_t).read()
    if "server.py" not in _src:
        continue
    _args = _spawn_args(_src)
    if not _args:
        continue                              # imports the module, spawns nothing
    check("--ephemeral" in _args or "KYA_STORE" in _args,
          "%s spawns the server without touching the real journal" % _name)

print()
if fails:
    print("STORE SMOKE FAILED - %d:" % len(fails))
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("the quote outlives the process, and editing its history is detectable.")
