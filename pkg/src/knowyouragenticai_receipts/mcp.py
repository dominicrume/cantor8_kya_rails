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

DEFAULT_RECEIPTS_PATH = "receipts.json"

# In-memory chain instance for interactive sessions
SESSION_CHAIN = Chain()

TOOLS = [
    {
        "name": "kya_stamp",
        "description": "Stamp an action (accepted claim or policy refusal) into a tamper-evident KYA receipt chain. Each receipt cryptographically seals onto the previous one via SHA-256.",
        "inputSchema": {
            "type": "object",
            "required": ["what", "amount", "currency", "payee", "rule", "outcome"],
            "properties": {
                "what": {
                    "type": "string",
                    "description": "Short description of the action attempted (e.g. 'Answered CFO query', 'API call', 'supplier payout')."
                },
                "amount": {
                    "type": "string",
                    "description": "Decimal amount or count as a string (e.g. '10.00', '1')."
                },
                "currency": {
                    "type": "string",
                    "description": "Currency or unit of account (e.g. 'USD', 'EUR', 'GBP' for financial payments; 'QUERY', 'EVENT', 'ANSWER' for non-financial actions). Required."
                },
                "payee": {
                    "type": "string",
                    "description": "The destination party, service, or tool receiving the call."
                },
                "rule": {
                    "type": "string",
                    "description": "The policy rule or document clause relied on (e.g. 'contract Northwind.pdf, clause 4.2', 'unverified legal advice prohibited')."
                },
                "outcome": {
                    "type": "string",
                    "description": "Whether the action was 'ACCEPTED' or 'REFUSED'.",
                    "enum": ["ACCEPTED", "REFUSED"]
                },
                "approved_by": {
                    "type": "string",
                    "description": "Optional authorizing human principal or supervisor."
                },
                "ledger": {
                    "type": "string",
                    "description": "Optional ledger, network, or environment name (e.g. 'polygon', 'production')."
                },
                "save_path": {
                    "type": "string",
                    "description": "File path to persist the updated receipt chain to disk. Defaults to 'receipts.json' in the working directory."
                }
            }
        }
    },
    {
        "name": "kya_verify",
        "description": "Verify the integrity of a receipt chain from a file path or JSON array. Proves whether any entry was edited or reordered. Proving that no entries were removed from the end requires matching the head seal against an external anchor.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to a JSON file containing the receipt chain. Defaults to 'receipts.json' if omitted."
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
                    "description": "Path to the receipt chain file. Defaults to 'receipts.json' if omitted."
                },
                "save_path": {
                    "type": "string",
                    "description": "Optional path to save the redacted disclosure file."
                },
                "overwrite": {
                    "type": "boolean",
                    "description": "Set to true to explicitly allow replacing an existing file at save_path."
                }
            }
        }
    },
    {
        "name": "kya_status",
        "description": "Get current status of the active session receipt chain: receipt count, head hash, active file path, and verification status.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]


def log(msg: str) -> None:
    print(f"[kya-receipts-mcp] {msg}", file=sys.stderr, flush=True)


def _atomic_write_json(path: str, data: Any) -> None:
    """Write data to path atomically using a temporary file and replace."""
    tmp = f"{path}.tmp.{os.getpid()}"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass
        raise


def _err_res(msg: str) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps({"error": msg}, indent=2)}],
        "isError": True
    }


def _validate_stamp_fields(args: dict[str, Any]) -> str | None:
    if not args.get("what"):
        return "Field 'what' is required."
    if not args.get("amount"):
        return "Field 'amount' is required."
    if not args.get("currency"):
        return "Field 'currency' is required."
    if not args.get("payee"):
        return "Field 'payee' is required."
    if not args.get("rule"):
        return "Field 'rule' is required."
    if (args.get("outcome") or "").upper() not in ("ACCEPTED", "REFUSED"):
        return "Field 'outcome' must be 'ACCEPTED' or 'REFUSED'."
    return None


def _load_existing_chain_fail_closed(path: str) -> tuple[Chain | None, str | None]:
    """If file exists, load it. If verification fails, return error rather than overwriting."""
    if not (path and os.path.exists(path)):
        return None, None
    try:
        return Chain.load(path), None
    except Exception as e:
        return None, (
            f"Refusing to stamp: existing file at '{path}' does not verify ({e}). "
            "Stamping onto a broken or tampered chain is prohibited to preserve evidence."
        )


def handle_stamp(arguments: dict[str, Any]) -> dict[str, Any]:
    global SESSION_CHAIN
    val_err = _validate_stamp_fields(arguments)
    if val_err:
        return _err_res(val_err)

    save_path = arguments.get("save_path") or DEFAULT_RECEIPTS_PATH
    loaded_chain, load_err = _load_existing_chain_fail_closed(save_path)
    if load_err:
        return _err_res(load_err)
    if loaded_chain is not None:
        SESSION_CHAIN = loaded_chain

    try:
        receipt = SESSION_CHAIN.stamp(
            what=arguments["what"],
            amount=str(arguments["amount"]),
            currency=arguments["currency"],
            payee=arguments["payee"],
            rule=arguments["rule"],
            outcome=arguments["outcome"].upper(),
            approved_by=arguments.get("approved_by"),
            ledger=arguments.get("ledger")
        )
        if save_path:
            _atomic_write_json(save_path, SESSION_CHAIN.receipts)
    except Exception as e:
        return _err_res(f"Failed to stamp receipt: {e}")

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


def _load_verify_receipts(file_path: str | None, receipts_json: str | None) -> tuple[list[Any] | None, str | None]:
    if file_path:
        if not os.path.exists(file_path):
            return None, f"File not found: {file_path}"
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f), None
        except Exception as e:
            return None, f"Could not read JSON from {file_path}: {e}"
    if receipts_json:
        try:
            return json.loads(receipts_json), None
        except Exception as e:
            return None, f"Invalid JSON string: {e}"
    active = DEFAULT_RECEIPTS_PATH
    if os.path.exists(active):
        with open(active, "r", encoding="utf-8") as f:
            return json.load(f), None
    return SESSION_CHAIN.receipts, None


def handle_verify(arguments: dict[str, Any]) -> dict[str, Any]:
    receipts, err = _load_verify_receipts(arguments.get("file_path"), arguments.get("receipts_json"))
    if err:
        return _err_res(err)
    if not isinstance(receipts, list):
        return _err_res("Receipts data must be a JSON array.")

    ok, bad = verify(receipts)
    head = receipts[-1].get("seal", GENESIS) if receipts else GENESIS
    msg = f"{len(receipts)} receipts, every seal holds." if ok else f"BROKEN at receipt {bad}."

    return {
        "content": [{
            "type": "text",
            "text": json.dumps({
                "verified": ok,
                "receipt_count": len(receipts),
                "head": head,
                "broken_at_receipt": bad if not ok else None,
                "message": msg,
                "note": "Proves no entry was edited. Proving no tail deletion or backdating requires comparing head seal against an external anchor."
            }, indent=2)
        }]
    }


def _get_disclosure_input(file_path: str | None) -> list[Any]:
    if file_path and os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            from_file: list[Any] = json.load(f)
            return from_file
    active = DEFAULT_RECEIPTS_PATH
    if os.path.exists(active):
        with open(active, "r", encoding="utf-8") as f:
            from_active: list[Any] = json.load(f)
            return from_active
    return SESSION_CHAIN.receipts


def handle_disclose(arguments: dict[str, Any]) -> dict[str, Any]:
    save_path = arguments.get("save_path")
    if save_path and os.path.exists(save_path) and not arguments.get("overwrite"):
        return _err_res(
            f"File already exists at '{save_path}'. Pass overwrite=true to explicitly allow replacing this file."
        )

    receipts = _get_disclosure_input(arguments.get("file_path"))
    disclosure = disclose(receipts)
    digest = outcome_digest(receipts)

    if save_path:
        try:
            _atomic_write_json(save_path, disclosure)
        except Exception as e:
            return _err_res(f"Failed to save disclosure to '{save_path}': {e}")

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
    active_path = DEFAULT_RECEIPTS_PATH
    chain = SESSION_CHAIN
    file_problem = None
    if os.path.exists(active_path):
        try:
            chain = Chain.load(active_path)
        except Exception as e:  # noqa: BLE001 - reported to the caller, never swallowed
            # The file on disk is the record. If it cannot be loaded or does not verify,
            # saying nothing and reporting the in-memory chain instead would hide exactly
            # what an auditor needs to know.
            file_problem = "%s: %s" % (type(e).__name__, e)

    ok, bad = chain.verify()
    return {
        "content": [{
            "type": "text",
            "text": json.dumps({
                "receipt_count": len(chain),
                "chain_head": chain.head,
                "verified": ok,
                "broken_at": bad if not ok else None,
                "storage": f"persisting to {active_path} by default unless overridden by save_path",
                "active_file": active_path if os.path.exists(active_path) else None,
                "file_problem": file_problem,
                "note": "Agent MCP stamps are self-attested. Standalone verification proves no edits; anchor chain_head externally to prove non-truncation.",
                "version": __version__
            }, indent=2)
        }]
    }


TOOL_HANDLERS = {
    "kya_stamp": handle_stamp,
    "kya_verify": handle_verify,
    "kya_disclose": handle_disclose,
    "kya_status": handle_status,
}


def _execute_tool(tool_name: str | None, args: dict[str, Any]) -> dict[str, Any]:
    handler = TOOL_HANDLERS.get(tool_name or "")
    if not handler:
        raise KeyError(f"Tool not found: {tool_name}")
    return handler(args)


def _handle_tools_call(req: dict[str, Any], msg_id: Any) -> dict[str, Any]:
    params = req.get("params", {})
    try:
        res = _execute_tool(params.get("name"), params.get("arguments", {}))
        return {"jsonrpc": "2.0", "id": msg_id, "result": res}
    except KeyError as e:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": str(e)}}
    except Exception as e:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32000, "message": str(e)}}


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
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        return _handle_tools_call(req, msg_id)
    if method == "notifications/initialized":
        return {}

    if msg_id is not None:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Method not supported: {method}"}}
    return {}


def main() -> int:
    log(f"Starting KYA Receipts MCP Server v{__version__}...")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e}"}
            }
            print(json.dumps(err_resp), flush=True)
            continue

        resp = dispatch(req)
        if resp:
            print(json.dumps(resp), flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
