#!/usr/bin/env python3
"""SIGKILL the wallet mid-session. The refusals must still be there.

The MCP wallet used to say "one mandate, one receipt chain, for the life of
the process", and that was an honest description of a real hole. The chain
lived in memory. A crash, a kill, or a client that hung up took every receipt
with it -- including the refusals, which are the entries an audit actually
asks about. An audit trail that vanishes when the thing being audited falls
over is not an audit trail.

It lost the cap too. `spent` sat in the same memory, so a process that died
came back with the whole float available again: a cap reset obtained by
crashing rather than by asking the owner. On the real rail that could not
happen -- the mandate is a contract and `spent` is a field on it -- so the
mock was not mirroring the ledger, it was quietly weaker than it.

SIGKILL, not terminate, and not a clean exit: nothing gets a chance to flush.
That is the only version of this test worth running.

Run: python3 tests/mcp_survives_kill.py
"""
import json
import os
import signal
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, "..", "step-4-mcp", "kya_mcp.py")

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


class Session:
    """One run of the wallet, talked to over stdio the way a model would."""

    def __init__(self, db):
        self.p = subprocess.Popen(
            [sys.executable, SERVER], text=True,
            env=dict(os.environ, KYA_MCP_STORE=db, PYTHONDONTWRITEBYTECODE="1"),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.mid = 0

    def call(self, name, args):
        self.mid += 1
        self.p.stdin.write(json.dumps(
            {"jsonrpc": "2.0", "id": self.mid, "method": "tools/call",
             "params": {"name": name, "arguments": args}}) + "\n")
        self.p.stdin.flush()
        line = self.p.stdout.readline()
        if not line:
            raise AssertionError("the wallet stopped answering on " + name)
        return json.loads(json.loads(line)["result"]["content"][0]["text"])

    def kill(self):
        self.p.send_signal(signal.SIGKILL)
        self.p.wait()

    def close(self):
        self.p.stdin.close()
        self.p.wait(timeout=15)


def main():
    db = os.path.join(tempfile.mkdtemp(), "kya-mcp.db")
    print("a wallet is killed with SIGKILL half way through a session")

    one = Session(db)
    one.call("open_mandate", {"cap": 5.0})
    one.call("charge", {"amount": 4.0, "payee": "customer", "what": "paid before the kill"})
    refused = one.call("charge", {"amount": 9.0, "payee": "customer",
                                  "what": "over the cap, refused before the kill"})
    check(refused["outcome"] == "REFUSED", "a refusal is recorded before the kill")
    one.kill()

    two = Session(db)
    st = two.call("get_statement", {})
    check(len(st["receipts"]) == 2, "both receipts survive the kill (%d)" % len(st["receipts"]))
    check(st["refused"] == 1, "and the REFUSAL is one of them -- the entry an audit asks for")
    check(st["chain_verifies"] is True, "the chain still verifies after the restart")

    # THE ONE THAT MATTERS. 4.0 of a 5.0 cap was spent in a process that no
    # longer exists. If `spent` did not come back, this is accepted, and the
    # way to reset your own cap is to crash.
    after = two.call("charge", {"amount": 4.0, "payee": "customer",
                                "what": "can I reset the cap by crashing?"})
    check(after["outcome"] == "REFUSED" and "cap" in after["rule"],
          "the cap remembers what a dead process spent -- no reset by crashing")

    # And the new receipt has to follow the old one, not start a second chain.
    st = two.call("get_statement", {})
    check(len(st["receipts"]) == 3, "the next receipt continues the same chain")
    check(st["receipts"][2]["prev"] == st["receipts"][1]["seal"],
          "sealed onto the entry written before the process died")
    check(st["chain_verifies"] is True, "and the chain verifies across the restart boundary")
    two.close()

    # A journal somebody edited must stop the wallet, not be worked around.
    import sqlite3
    edited = os.path.join(tempfile.mkdtemp(), "edited.db")
    Session(edited).close()
    s = Session(edited)
    s.call("open_mandate", {"cap": 5.0})
    s.call("charge", {"amount": 1.0, "payee": "customer", "what": "honest"})
    s.close()
    db2 = sqlite3.connect(edited)
    db2.execute("UPDATE journal SET data = REPLACE(data, 'honest', 'edited') "
                "WHERE kind = 'receipt'")
    db2.commit()
    db2.close()
    bad = Session(edited)
    out = bad.p.communicate(timeout=20)[1]
    check(bad.p.returncode == 3, "an edited journal refuses to start (rc=%s)" % bad.p.returncode)
    check("REFUSING TO START" in out, "and says so, on stderr where it cannot corrupt the protocol")
    check("[kya]" in out and not out.startswith("{"),
          "nothing was written to stdout, which carries the JSON-RPC")

    print()
    if fails:
        print("MCP SURVIVAL FAILED - %d:" % len(fails))
        for f in fails:
            print("  -", f)
        return 1
    print("killing the wallet loses no receipts, and buys the agent no cap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
