#!/usr/bin/env python3
"""The receipts MCP server fails closed, and its chain state is per file.

Each group names the defect it closes (letters are the QA, testing and debugging
agents' finding ids, 26 Nov 2026) and is written to go RED on the code that had it:

  F2   kya_status said verified:true for a file that did not parse
  F3   kya_disclose invented a GENESIS digest for a missing or non-array file
  F4   kya_disclose never verified, so a tampered chain gave a normal disclosure
  F5   kya_disclose save_path could overwrite the chain file or the pin log
  A6   duplicate keys in a request were resolved last-wins

The positive controls (a good chain still verifies, discloses and reports) are in
the same file so a fix that refuses everything cannot pass.

Everything destructive happens in temp dirs. Run: python3 tests/mcp_failclosed_smoke.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from typing import Any, Callable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pkg", "src"))
sys.dont_write_bytecode = True
from knowyouragenticai_receipts import Chain, mcp  # noqa: E402

FAILS: list[str] = []


def check(ok: bool, label: str) -> None:
    print("  %s %s" % ("PASS" if ok else "FAIL", label))
    if not ok:
        FAILS.append(label)


def call(handler: Callable[..., Any], args: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    r = handler(args)
    return bool(r.get("isError")), json.loads(r["content"][0]["text"])


def stamp_args(path: str, what: str = "pay", **kw: Any) -> dict[str, Any]:
    a = {"what": what, "amount": "1.00", "currency": "USD", "payee": "acme",
         "rule": "cap", "outcome": "ACCEPTED", "save_path": path}
    a.update(kw)
    return a


def good_chain(path: str, n: int = 2) -> None:
    for i in range(n):
        err, _ = call(mcp.handle_stamp, stamp_args(path, "g%d" % i))
        assert not err


def tamper(path: str) -> None:
    with open(path) as f:
        data = json.load(f)
    data[0]["what"] = "EDITED"
    with open(path, "w") as f:
        json.dump(data, f)


def put(path: str, text: str) -> None:
    with open(path, "w") as f:
        f.write(text)


def read(path: str) -> str:
    with open(path) as f:
        return f.read()


# ------------------------------------------------------------- fail closed
def group_status(d: str) -> None:
    print("F2: kya_status never says verified:true for a file it could not read")
    os.chdir(d)
    put("receipts.json", "not json")
    err, out = call(mcp.handle_status, {})
    check(err and out["verified"] is False, "unparseable file: isError and verified false")
    check(bool(out.get("file_problem")), "the reason is given")
    put("receipts.json", "{}")
    err, out = call(mcp.handle_status, {})
    check(err and out["verified"] is False, "an empty object is not a chain: verified false")
    os.remove("receipts.json")
    good_chain("receipts.json")
    err, out = call(mcp.handle_status, {})
    check(not err and out["verified"] is True and out["receipt_count"] == 2, "control: a good chain reports 2, verified")
    tamper("receipts.json")
    err, out = call(mcp.handle_status, {})
    check(out["verified"] is False and out["broken_at"] == 1, "tampered chain: verified false, broken_at 1")


def group_disclose(d: str) -> None:
    print("F3/F4: kya_disclose refuses what it cannot vouch for")
    os.chdir(d)
    for label, setup in (("missing file", None), ("empty object", "{}"), ("non-array", '"x"')):
        p = os.path.join(d, label.replace(" ", "_") + ".json")
        if setup:
            put(p, setup)
        err, out = call(mcp.handle_disclose, {"file_path": p})
        check(err and "outcome_digest" not in out and bool(out.get("error")), "%s: refused with a reason" % label)
    err, out = call(mcp.handle_disclose, {})
    check(err and "outcome_digest" not in out, "no file anywhere and nothing stamped: refused, no GENESIS digest")
    group_disclose_tampered(d)


def group_disclose_tampered(d: str) -> None:
    p = os.path.join(d, "ok.json")
    good_chain(p, 3)
    err, out = call(mcp.handle_disclose, {"file_path": p})
    check(not err and out["total_receipts"] == 3, "control: a good chain discloses")
    tamper(p)
    err, out = call(mcp.handle_disclose, {"file_path": p})
    check(err and "outcome_digest" not in out and "verify" in out["error"], "F4: a tampered chain is refused")


def group_save_path(d: str) -> None:
    print("F5: kya_disclose cannot overwrite the chain or the pin log")
    os.chdir(d)
    chain = os.path.join(d, "c.json")
    pins = os.path.join(d, "pins.log")
    good_chain(chain)
    err, _ = call(mcp.handle_stamp, stamp_args(chain, "pinned", pin_file=pins))
    before_chain, before_pins = read(chain), read(pins)
    err, out = call(mcp.handle_disclose, {"file_path": chain, "save_path": chain, "overwrite": True})
    check(err and read(chain) == before_chain, "save_path == chain file, overwrite true: refused, chain intact")
    link = os.path.join(d, "link.json")
    os.symlink(chain, link)
    err, out = call(mcp.handle_disclose, {"file_path": chain, "save_path": link, "overwrite": True})
    check(err and read(chain) == before_chain, "save_path is a symlink to the chain: refused (realpath compared)")
    err, out = call(mcp.handle_disclose, {"file_path": chain, "save_path": "./c.json", "overwrite": True})
    check(err and read(chain) == before_chain, "save_path spelled ./c.json: refused")
    err, out = call(mcp.handle_disclose, {"file_path": chain, "save_path": pins, "overwrite": True})
    check(err and read(pins) == before_pins, "save_path == a pin log this session used: refused, pins intact")
    err, out = call(mcp.handle_stamp, stamp_args(chain, "x", pin_file=chain))
    check(err and read(chain) == before_chain, "stamp with pin_file == save_path: refused")
    other = os.path.join(d, "disclosure.json")
    err, out = call(mcp.handle_disclose, {"file_path": chain, "save_path": other})
    check(not err and os.path.exists(other), "control: a different save_path still works")


def group_duplicates() -> None:
    print("A6: duplicate keys are refused, not resolved last-wins")
    raw = (b'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"kya_stamp","arguments":'
           b'{"outcome":"REFUSED","outcome":"ACCEPTED"}}}')
    req, err = mcp._parse_request(raw)
    check(req is None and bool(err) and "duplicate" in json.dumps(err), "duplicate key in arguments: parse error naming it")
    req, err = mcp._parse_request(b'{"jsonrpc":"2.0","id":1,"method":"ping"}')
    check(err is None and req["method"] == "ping", "control: a normal request parses")


def fresh_process_state() -> None:
    """The server is a fresh process per test group: forget whatever chain state the last one left."""
    if hasattr(mcp, "SESSION_CHAIN"):
        mcp.SESSION_CHAIN = Chain()
    if hasattr(mcp, "STORE"):
        mcp.STORE.clear()


def main() -> int:
    mcp.log = lambda msg: None
    groups: list[Callable[..., None]] = [group_status, group_disclose, group_save_path]
    for g in groups:
        fresh_process_state()
        with tempfile.TemporaryDirectory(prefix="kya-fc-") as d:
            g(os.path.realpath(d))
    group_duplicates()
    os.chdir(ROOT)
    print()
    print("ALL GREEN" if not FAILS else "FAILED: %d\n  - %s" % (len(FAILS), "\n  - ".join(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
