#!/usr/bin/env python3
"""KYA Receipts MCP Server.

Provides tools for AI agents, operators, and MCP clients (Claude Desktop,
Claude Code, Cursor) to manage, stamp, verify, and disclose tamper-evident
audit receipt chains directly over Model Context Protocol (MCP).

JSON-RPC 2.0 over stdio. Standard library only: zero external dependencies.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Mapping

from . import (
    GENESIS,
    Chain,
    __version__,
    canonical,
    check_disclosure,
    disclose,
    outcome_digest,
    refusals_only,
    seal,
    verify,
)

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {
    "name": "knowyouragenticai-receipts",
    "version": __version__,
}

# In-memory chain instance for interactive sessions
SESSION_CHAIN = Chain()

TOOLS = [
    {
        "name": "kya_stamp",
        "description": "Stamp an action (accepted or refused) into a tamper-evident KYA receipt chain. Each receipt cryptographically seals onto the previous one via SHA-256.",
        "inputSchema": {
            "type": "object",
            "required": ["what", "amount", "payee", "rule", "outcome"],
            "properties": {
                "what": {
                    "type": "string",
                    "description": "Short description of the action attempted (e.g. 'API call', 'supplier payout', 'model inference')."
                },
                "amount": {
                    "type": "string",
                    "description": "Decimal amount or count (e.g. '10.00', '1.0')."
                },
                "currency": {
                    "type": "string",
                    "description": "Currency or unit (e.g. 'USD', 'EUR', 'CC', 'TOKEN'). Defaults to 'USD'."
                },
                "payee": {
                    "type": "string",
                    "description": "The destination party, service, or tool receiving the call."
                },
                "rule": {
                    "type": "string",
                    "description": "The policy rule checked (e.g. 'within spend limit', 'allow-list', 'rate limit check')."
                },
                "outcome": {
                    "type": "string",
                    "description": "Whether the action was 'ACCEPTED' or 'REFUSED'.",
                    "enum": ["ACCEPTED", "REFUSED"]
                },
                "approved_by": {
                    "type": "string",
                    "description": "Optional authorizing entity or principal."
                },
                "ledger": {
                    "type": "string",
                    "description": "Optional ledger, network, or environment name (e.g. 'canton', 'production')."
                },
                "save_path": {
                    "type": "string",
                    "description": "Optional file path to persist the updated receipt chain to disk."
                }
            }
        }
    },
    {
        "name": "kya_verify",
        "description": "Verify the integrity of a receipt chain from a file path or JSON array. Proves whether any entry was edited, deleted, or reordered.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to a JSON file containing the receipt chain."
                },
                "receipts_json": {
                    "type": "string",
                    "description": "Optional raw JSON string of the receipts array to verify directly."
                }
            }
        }
    },
    {
        "name": "kya_disclose",
        "description": "Generate an audit disclosure that reveals refusals while safely withholding confidential accepted transactions, computing an immutable outcome digest.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the receipt chain file."
                },
                "save_path": {
                    "type": "string",
                    "description": "Optional path to save the redacted disclosure file."
                }
            }
        }
    },
    {
        "name": "kya_status",
        "description": "Get current status of the active session receipt chain: receipt count, head hash, and verification status.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]


def log(msg: str) -> None:
    print(f"[kya-receipts-mcp] {msg}", file=sys.stderr, flush=True)


def handle_stamp(arguments: dict[str, Any]) -> dict[str, Any]:
    global SESSION_CHAIN
    what = arguments["what"]
    amount = str(arguments["amount"])
    currency = arguments.get("currency", "USD")
    payee = arguments["payee"]
    rule = arguments["rule"]
    outcome = arguments["outcome"].upper()
    approved_by = arguments.get("approved_by")
    ledger = arguments.get("ledger")
    save_path = arguments.get("save_path")

    # If save_path points to existing chain, load it first
    if save_path and os.path.exists(save_path):
        try:
            SESSION_CHAIN = Chain.load(save_path)
        except Exception as e:
            log(f"Warning loading existing chain from {save_path}: {e}")

    receipt = SESSION_CHAIN.stamp(
        what=what,
        amount=amount,
        currency=currency,
        payee=payee,
        rule=rule,
        outcome=outcome,
        approved_by=approved_by,
        ledger=ledger
    )

    if save_path:
        SESSION_CHAIN.save(save_path)

    return {
        "content": [{
            "type": "text",
            "text": json.dumps({
                "receipt": receipt,
                "chain_head": SESSION_CHAIN.head,
                "total_receipts": len(SESSION_CHAIN),
                "saved_to": save_path
            }, indent=2)
        }]
    }


def handle_verify(arguments: dict[str, Any]) -> dict[str, Any]:
    file_path = arguments.get("file_path")
    receipts_json = arguments.get("receipts_json")

    receipts = None
    if file_path:
        with open(file_path, "r", encoding="utf-8") as f:
            receipts = json.load(f)
    elif receipts_json:
        receipts = json.loads(receipts_json)
    else:
        receipts = SESSION_CHAIN.receipts

    if not isinstance(receipts, list):
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({"verified": False, "error": "Receipts data must be a JSON array."}, indent=2)
            }]
        }

    ok, bad = verify(receipts)
    head = receipts[-1].get("seal", GENESIS) if receipts else GENESIS

    return {
        "content": [{
            "type": "text",
            "text": json.dumps({
                "verified": ok,
                "receipt_count": len(receipts),
                "head": head,
                "broken_at_receipt": bad if not ok else None,
                "message": "Every seal holds. Nothing was edited." if ok else f"Broken at receipt {bad}."
            }, indent=2)
        }]
    }


def handle_disclose(arguments: dict[str, Any]) -> dict[str, Any]:
    file_path = arguments.get("file_path")
    save_path = arguments.get("save_path")

    if file_path and os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            receipts = json.load(f)
    else:
        receipts = SESSION_CHAIN.receipts

    disclosure = disclose(receipts)
    digest = outcome_digest(receipts)

    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(disclosure, f, indent=2)

    return {
        "content": [{
            "type": "text",
            "text": json.dumps({
                "outcome_digest": digest,
                "total_receipts": len(receipts),
                "disclosed_entries": len(disclosure.get("entries", [])),
                "disclosure": disclosure,
                "saved_to": save_path
            }, indent=2)
        }]
    }


def handle_status(arguments: dict[str, Any]) -> dict[str, Any]:
    ok, bad = SESSION_CHAIN.verify()
    return {
        "content": [{
            "type": "text",
            "text": json.dumps({
                "receipt_count": len(SESSION_CHAIN),
                "chain_head": SESSION_CHAIN.head,
                "verified": ok,
                "broken_at": bad if not ok else None,
                "version": __version__
            }, indent=2)
        }]
    }


def dispatch(req: dict[str, Any]) -> dict[str, Any]:
    method = req.get("method")
    msg_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "serverInfo": SERVER_INFO,
                "capabilities": {"tools": {}}
            }
        }
    elif method == "notifications/initialized":
        return {}
    elif method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": TOOLS}
        }
    elif method == "tools/call":
        params = req.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})

        try:
            if tool_name == "kya_stamp":
                res = handle_stamp(args)
            elif tool_name == "kya_verify":
                res = handle_verify(args)
            elif tool_name == "kya_disclose":
                res = handle_disclose(args)
            elif tool_name == "kya_status":
                res = handle_status(args)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Tool not found: {tool_name}"}
                }
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": res
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32000, "message": str(e)}
            }
    else:
        if msg_id is not None:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method not supported: {method}"}
            }
        return {}


def main() -> int:
    log(f"Starting KYA Receipts MCP Server v{__version__}...")
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            req = json.loads(line)
            resp = dispatch(req)
            if resp:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f"Error handling request: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
