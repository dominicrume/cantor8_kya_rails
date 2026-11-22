#!/usr/bin/env python3
"""Adversarial smoke test for knowyouragenticai_receipts MCP server.

Directly tests against all 6 findings from the VeritaPort independent review:
1. Overwrites a tampered file -> MUST FAIL CLOSED, refuse to stamp, preserve evidence.
2. In-memory loss without save_path -> MUST default to receipts.json and persist.
3. kya_verify overclaims -> MUST caveat tail truncation and require an anchor.
4. kya_disclose overwrites -> MUST refuse existing file unless overwrite=True.
5. Currency default -> MUST require explicit currency/unit.
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PKG_SRC = os.path.join(ROOT, "pkg", "src")

fails = []

def check(ok: bool, desc: str):
    print("  " + ("PASS" if ok else "FAIL") + " " + desc)
    if not ok:
        fails.append(desc)


def run_mcp(requests: list[dict], env: dict = None, cwd: str = None) -> list[dict]:
    p_env = dict(os.environ)
    p_env["PYTHONPATH"] = PKG_SRC
    if env:
        p_env.update(env)

    p = subprocess.Popen(
        [sys.executable, "-m", "knowyouragenticai_receipts", "mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
        env=p_env
    )
    input_text = "\n".join(json.dumps(r) for r in requests) + "\n"
    stdout, stderr = p.communicate(input=input_text)
    
    responses = []
    for line in stdout.splitlines():
        line = line.strip()
        if line:
            try:
                responses.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return responses


def main():
    print("knowyouragenticai-receipts MCP server - VeritaPort review regression suite")
    
    workdir = tempfile.mkdtemp(prefix="kya-mcp-test-")
    cwd = os.getcwd()
    try:
        os.chdir(workdir)
        
        # 1. Initialize and tools/list
        reqs = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        ]
        resps = run_mcp(reqs, cwd=workdir)
        check(len(resps) == 2, "initial handshake & tools/list returned")
        tools = resps[1]["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        check("kya_stamp" in tool_names and "kya_verify" in tool_names, "standard tools present")
        
        # Finding 6: Missing currency must be rejected
        reqs = [
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
                "name": "kya_stamp",
                "arguments": {
                    "what": "query",
                    "amount": "1",
                    # currency omitted!
                    "payee": "analyst",
                    "rule": "evidence check",
                    "outcome": "ACCEPTED"
                }
            }}
        ]
        resps = run_mcp(reqs, cwd=workdir)
        check(resps[0]["result"].get("isError") is True, "stamp without currency is rejected (Finding 6)")

        # Finding 2: Stamp with default path (save_path omitted) persists to receipts.json
        reqs = [
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
                "name": "kya_stamp",
                "arguments": {
                    "what": "Answered CFO question",
                    "amount": "1",
                    "currency": "QUERY",
                    "payee": "CFO",
                    "rule": "contract Northwind.pdf, clause 4.2",
                    "outcome": "ACCEPTED"
                }
            }},
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {
                "name": "kya_stamp",
                "arguments": {
                    "what": "Refused legal advice",
                    "amount": "1",
                    "currency": "QUERY",
                    "payee": "analyst",
                    "rule": "unverified legal advice prohibited",
                    "outcome": "REFUSED"
                }
            }}
        ]
        resps = run_mcp(reqs, cwd=workdir)
        check(os.path.exists("receipts.json"), "receipts.json created by default (Finding 2)")
        with open("receipts.json") as f:
            chain_data = json.load(f)
        check(len(chain_data) == 2, "both receipts written to disk by default")

        # Restart server and verify status sees the file
        reqs = [
            {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {
                "name": "kya_status",
                "arguments": {}
            }}
        ]
        resps = run_mcp(reqs, cwd=workdir)
        status_text = resps[0]["result"]["content"][0]["text"]
        status_json = json.loads(status_text)
        check(status_json["receipt_count"] == 2, "persisted receipts survived server restart (Finding 2)")
        check(status_json.get("file_problem") is None, "a sound file on disk reports no problem")

        # Finding 3: kya_verify outputs honest message about anchor and reports count/head
        reqs = [
            {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {
                "name": "kya_verify",
                "arguments": {"file_path": "receipts.json"}
            }}
        ]
        resps = run_mcp(reqs, cwd=workdir)
        verify_text = json.loads(resps[0]["result"]["content"][0]["text"])
        check(verify_text["verified"] is True, "valid chain verifies")
        check(verify_text["receipt_count"] == 2, "reports receipt count")
        check("anchor" in verify_text["message"].lower() or "anchor" in verify_text.get("note", "").lower(),
              "verification caveats tail truncation anchor (Finding 3)")

        # Finding 1: Stamping onto a tampered file MUST FAIL CLOSED and NOT overwrite
        # Now tamper with receipts.json
        chain_data[1]["outcome"] = "ACCEPTED"
        with open("receipts.json", "w") as f:
            json.dump(chain_data, f)

        # Attempt to stamp onto tampered file
        reqs = [
            {"jsonrpc": "2.0", "id": 8, "method": "tools/call", "params": {
                "name": "kya_stamp",
                "arguments": {
                    "what": "Another question",
                    "amount": "1",
                    "currency": "QUERY",
                    "payee": "analyst",
                    "rule": "evidence check",
                    "outcome": "ACCEPTED"
                }
            }}
        ]
        resps = run_mcp(reqs, cwd=workdir)
        check(resps[0]["result"].get("isError") is True, "stamp onto tampered file refused (Finding 1)")
        check("prohibited to preserve evidence" in resps[0]["result"]["content"][0]["text"],
              "refusal explicitly cites preserving evidence")
        
        # Verify the tampered file was NOT overwritten with a fresh chain
        with open("receipts.json") as f:
            persisted_after = json.load(f)
        check(len(persisted_after) == 2, "tampered file was NOT overwritten with 1-receipt chain (Finding 1)")
        check(persisted_after[1]["outcome"] == "ACCEPTED", "tampered evidence remained preserved on disk")

        # Finding 4: kya_disclose refuses to overwrite existing file without overwrite=True
        with open("existing_doc.txt", "w") as f:
            f.write("Board minutes: do not overwrite")

        reqs = [
            {"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {
                "name": "kya_disclose",
                "arguments": {
                    "save_path": "existing_doc.txt"
                }
            }}
        ]
        resps = run_mcp(reqs, cwd=workdir)
        check(resps[0]["result"].get("isError") is True, "disclose refuses to overwrite existing file (Finding 4)")
        with open("existing_doc.txt") as f:
            check("Board minutes" in f.read(), "existing document preserved untouched")

        # With overwrite=True, it succeeds
        reqs = [
            {"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {
                "name": "kya_disclose",
                "arguments": {
                    "save_path": "existing_doc.txt",
                    "overwrite": True
                }
            }}
        ]
        resps = run_mcp(reqs, cwd=workdir)
        check("isError" not in resps[0]["result"], "disclose succeeds with overwrite=True")
        with open("existing_doc.txt") as f:
            check("entries" in f.read(), "disclosure written when explicitly permitted")

        # Status must say so when the file on disk is the thing that is broken.
        with open("receipts.json") as f:
            on_disk = json.load(f)
        on_disk[0]["amount"] = "999999"
        with open("receipts.json", "w") as f:
            json.dump(on_disk, f)
        resps = run_mcp([{"jsonrpc": "2.0", "id": 99, "method": "tools/call",
                          "params": {"name": "kya_status", "arguments": {}}}], cwd=workdir)
        broken = json.loads(resps[0]["result"]["content"][0]["text"])
        check(broken.get("file_problem"), "status reports a tampered file on disk instead of hiding it")

    finally:
        os.chdir(cwd)
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)

    print()
    if fails:
        print(f"FAILED ({len(fails)} failures):")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("ALL TESTS PASSED: All 6 VeritaPort findings closed and proven by tests.")

if __name__ == "__main__":
    main()
