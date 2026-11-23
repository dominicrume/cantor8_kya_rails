#!/usr/bin/env python3
"""A pin catches the one case a hash chain cannot: delete the file and start again.

A fresh valid chain verifies, so a chain that holds proves nothing inside it was
edited and nothing about whether it is still the chain it was yesterday. This
test builds the failure first (no pin: the restart goes through, which is the
bug a QA engineer named on 23 Nov 2026), then shows each pin catching it.

Run: python3 tests/pin_smoke.py
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pkg", "src"))
from knowyouragenticai_receipts import GENESIS, Chain, check_pins, head_pin, mcp  # noqa: E402

FAILS = []


def check(ok, label):
    print("  %s %s" % ("PASS" if ok else "FAIL", label))
    if not ok:
        FAILS.append(label)


def chain_of(n, payee="acme"):
    c = Chain()
    for i in range(n):
        c.stamp("pay", "1.00", "USD", payee, "cap", "ALLOWED")
    return c


def stamp(save, pin=None, payee="acme"):
    mcp.SESSION_CHAIN = Chain()          # a fresh process each time
    args = {"what": "pay", "amount": "1.00", "currency": "USD", "payee": payee,
            "rule": "cap", "outcome": "ACCEPTED", "save_path": save}
    if pin:
        args["pin_file"] = pin
    r = mcp.handle_stamp(args)
    return not r.get("isError"), json.loads(r["content"][0]["text"])


def verify(save, pin):
    r = mcp.handle_verify({"file_path": save, "pin_file": pin})
    return json.loads(r["content"][0]["text"])


def lines(path):
    with open(path) as f:
        return [ln for ln in f.read().splitlines() if ln.strip()]


print("the pin functions")
empty = head_pin([])
check(empty == {"n": 0, "seal": GENESIS}, "an empty chain pins n=0 at the genesis value")
three = chain_of(3).receipts
pin3 = head_pin(three)
check(pin3["n"] == 3 and pin3["seal"] == three[-1]["seal"], "a pin is the count and the final seal")
check(check_pins(three, [pin3])[0], "the chain it came from matches")
ext = chain_of(3)
ext.stamp("pay", "1.00", "USD", "acme", "cap", "ALLOWED")
check(check_pins(ext.receipts, [pin3])[0], "extending a chain keeps every pin true")
ok, why = check_pins(three[:2], [pin3])
check(not ok and "truncated" in why, "truncating the tail is caught: " + why)
ok, why = check_pins(chain_of(1).receipts, [pin3])
check(not ok and "truncated" in why, "deleting and restarting is caught: " + why)
other = chain_of(3, payee="somebody-else").receipts
check(Chain(other).verify()[0], "(control) a different three-receipt chain is itself valid")
ok, why = check_pins(other, [pin3])
check(not ok and "replaced" in why, "replacing history with another valid chain is caught: " + why)
ok, why = check_pins([], [pin3])
check(not ok, "an empty chain does not satisfy a pin that saw receipts")
bad = [dict(three[0], what="edited")] + three[1:]
ok, why = check_pins(bad, [pin3])
check(not ok and "does not verify" in why, "an edited chain fails before the pins are read")
for junk in ({"n": True, "seal": "x"}, {"n": -1, "seal": "x"}, {"n": "3", "seal": "x"},
             {"n": 1}, "pin", None, 7, []):
    ok, why = check_pins(three, [junk])
    check(not ok and "malformed" in why, "malformed pin refused: %r" % (junk,))
check(check_pins(three, [])[0], "no pins at all is not a failure (nothing was promised)")

print("through the MCP tools, in a temp directory")
with tempfile.TemporaryDirectory() as d:
    chain_file = os.path.join(d, "chain", "receipts.json")
    pin_file = os.path.join(d, "pins", "pins.jsonl")
    os.makedirs(os.path.dirname(chain_file))
    os.makedirs(os.path.dirname(pin_file))

    ok1, _ = stamp(chain_file, pin_file)
    ok2, _ = stamp(chain_file, pin_file)
    check(ok1 and ok2 and len(lines(pin_file)) == 2, "two stamps append two pins")
    check(json.loads(lines(pin_file)[1])["n"] == 2, "the second pin says 2 receipts")
    v = verify(chain_file, pin_file)
    check(v["verified"] and v["pin_check"]["matched"] and v["pin_check"]["pins"] == 2,
          "verify reports the chain matches both pins")
    check("assurance" not in json.dumps(v).replace("does not raise the assurance level", ""),
          "verify does not claim an assurance level from a pin")

    # CONTROL: without a pin the restart goes through. This is the bug.
    ctl_chain = os.path.join(d, "control.json")
    stamp(ctl_chain)
    stamp(ctl_chain)
    os.remove(ctl_chain)
    okc, resp = stamp(ctl_chain)
    check(okc and resp["total_receipts"] == 1,
          "CONTROL: with no pin, delete-and-restart is accepted and looks clean (1 receipt)")

    # with the pin, it is refused and nothing is written
    os.remove(chain_file)
    before = lines(pin_file)
    okr, resp = stamp(chain_file, pin_file)
    check(not okr and "pin log" in resp["error"], "with a pin, delete-and-restart is refused")
    check(not os.path.exists(chain_file), "and no chain file was written")
    check(lines(pin_file) == before, "and the pin log was not touched")

    # replace with a different valid two-receipt chain
    alt = chain_of(2, payee="somebody-else")
    with open(chain_file, "w") as f:
        json.dump(alt.receipts, f)
    okr, resp = stamp(chain_file, pin_file)
    check(not okr and "replaced" in resp["error"], "a different valid chain in its place is refused")
    v = verify(chain_file, pin_file)
    check(v["verified"] and not v["pin_check"]["matched"] and "replaced" in v["pin_check"]["reason"],
          "verify says the chain holds but is NOT the pinned one")

    # damaged pin log stops the writer
    bad_pin = os.path.join(d, "bad.jsonl")
    with open(bad_pin, "w") as f:
        f.write('{"n": 1, "seal": "abc"}\nnot json at all\n')
    okb, resp = stamp(os.path.join(d, "x.json"), bad_pin)
    check(not okb and "unreadable" in resp["error"], "a damaged pin log refuses the write, it is not skipped")
    v = verify(chain_file if os.path.exists(chain_file) else ctl_chain, bad_pin)
    check(not v["pin_check"]["matched"], "verify against a damaged pin log is not a match")
    v = verify(ctl_chain, os.path.join(d, "does-not-exist.jsonl"))
    check(not v["pin_check"]["matched"] and v["pin_check"]["pins"] == 0,
          "verify against a missing pin log says nothing was checked")

print()
if FAILS:
    print("FAILED: %d" % len(FAILS))
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("ALL GREEN")
