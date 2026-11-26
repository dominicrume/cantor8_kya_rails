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
    check_pins,
    disclose,
    head_pin,
    outcome_digest,
    refusals_only,
    seal,
    verify,
)
from .witness import check_witnessed, fetch_pins, load_key, post_pin

PROTOCOL_VERSION = "2024-11-05"           # what the legacy `initialize` handshake answers
MODERN_VERSION = "2026-07-28"             # stateless: the caller rides in every request's _meta
SUPPORTED_VERSIONS = ("2026-07-28", "2025-11-25", "2024-11-05")
META_VERSION = "io.modelcontextprotocol/protocolVersion"
META_CAPS = "io.modelcontextprotocol/clientCapabilities"
META_CLIENT = "io.modelcontextprotocol/clientInfo"
META_SERVER = "io.modelcontextprotocol/serverInfo"
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
                "pin_file": {
                    "type": "string",
                    "description": "Optional. An append-only pin log kept OUTSIDE the chain's directory. When given, the receipt is refused if the chain no longer contains every earlier pin (it was deleted and restarted, truncated or replaced), and a new pin is appended after each write."
                },
                "witness_url": {
                    "type": "string",
                    "description": "Optional. The base URL of a separate witness process (SPEC 6g). When given, the receipt is refused if the witness cannot be reached or has seen a head this chain does not contain, and the new head is sent to the witness after each write. Fails closed: no witness, no write."
                },
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
                "agent_ref": {
                    "type": "string",
                    "description": "Optional pointer at the identity the agent acted under: a DID, an Agent Passport id, an OAuth client id. At most 256 ASCII characters. It is written by the caller and establishes nothing: an address, not evidence. If omitted, the MCP client name and version from the request's _meta are recorded as 'mcp-client:name/version', a label the caller chose and not an authenticated identity."
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
                },
                "pin_file": {
                    "type": "string",
                    "description": "Optional. A pin log written by kya_stamp. Reports whether the chain still contains every pin: this is what catches a deleted-and-restarted, truncated or replaced chain."
                },
                "witness_url": {
                    "type": "string",
                    "description": "Optional. A witness (SPEC 6g) to compare the chain against."
                },
                "witness_key_file": {
                    "type": "string",
                    "description": "Optional. The witness's key file, held by the VERIFIER and never by the agent. Without it the witnessed pins are compared but their MACs are not checked, and the result says so."
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


def _read_pins(path: str) -> tuple[list[Any], str | None]:
    """The pins in an append-only pin log, one JSON object per line.

    A missing file is no pins. A line that is not JSON is an error, not a skip:
    a pin log somebody damaged must stop the writer, not be quietly ignored.
    """
    if not os.path.exists(path):
        return [], None
    pins: list[Any] = []
    number = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for number, line in enumerate(f, start=1):
                if line.strip():
                    pins.append(json.loads(line))
    except (OSError, ValueError) as e:
        return [], f"pin file {path} is unreadable near line {number}: {e}"
    return pins, None


def _append_pin(path: str, pin: dict[str, Any]) -> None:
    """Append one pin and force it to disk. Never rewrites an earlier line."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(pin, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())


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


def _client_ref(meta: dict[str, Any] | None) -> str:
    """'mcp-client:name/version' from the request's _meta, or '' when there is none.

    Read from THIS request, never remembered from an earlier one: the protocol is
    stateless. It is a label the client chose, so it carries its own scheme.
    """
    info = (meta or {}).get(META_CLIENT)
    if not isinstance(info, dict) or not info.get("name"):
        return ""
    raw = "mcp-client:%s/%s" % (info.get("name"), info.get("version", ""))
    return "".join(c if (c.isalnum() and ord(c) < 128) or c in "._:/@+-" else "_" for c in raw)[:256]


def _agent_ref_for(arguments: dict[str, Any], meta: dict[str, Any] | None) -> tuple[str, str | None]:
    explicit = arguments.get("agent_ref")
    if explicit is None:
        return _client_ref(meta), None
    if not isinstance(explicit, str):
        return "", "Field 'agent_ref' must be a string."
    return explicit, None


def _pin_gate(pin_file: str | None) -> str | None:
    """Error text if the session chain does not match the pin log, else None."""
    if not pin_file:
        return None
    pins, pin_err = _read_pins(pin_file)
    if pin_err:
        return pin_err
    pins_ok, why = check_pins(SESSION_CHAIN.receipts, pins)
    if pins_ok:
        return None
    return f"Refusing to stamp: this chain does not match the pin log ({why}). Nothing was written."


def _witness_gate(witness_url: str | None) -> str | None:
    """Error text if the witness cannot be reached or has seen another chain."""
    if not witness_url:
        return None
    pins, err = fetch_pins(witness_url)
    if err or pins is None:
        return f"Refusing to stamp: {err}. Nothing was written."
    pins_ok, why = check_pins(SESSION_CHAIN.receipts, pins)
    if pins_ok:
        return None
    return f"Refusing to stamp: this chain does not match what the witness saw ({why}). Nothing was written."


def _witness_record(witness_url: str | None) -> str | None:
    """Error text if the witness did not record the new head, else None."""
    if not witness_url:
        return None
    err = post_pin(witness_url, head_pin(SESSION_CHAIN.receipts))
    return f"Stamped and saved, but NOT witnessed: {err}" if err else None


def _stamp_gates(pin_file: str | None, witness_url: str | None) -> str | None:
    return _pin_gate(pin_file) or _witness_gate(witness_url)


def _stamp_and_persist(arguments: dict[str, Any], agent_ref: Any,
                       save_path: str | None, pin_file: str | None) -> Any:
    receipt = SESSION_CHAIN.stamp(
        what=arguments["what"],
        amount=str(arguments["amount"]),
        currency=arguments["currency"],
        payee=arguments["payee"],
        rule=arguments["rule"],
        outcome=arguments["outcome"].upper(),
        approved_by=arguments.get("approved_by"),
        ledger=arguments.get("ledger"),
        agent_ref=agent_ref
    )
    if save_path:
        _atomic_write_json(save_path, SESSION_CHAIN.receipts)
    if pin_file:
        _append_pin(pin_file, head_pin(SESSION_CHAIN.receipts))
    return receipt


def _checked_stamp_input(arguments: dict[str, Any], meta: dict[str, Any] | None) -> tuple[Any, str | None]:
    """(agent_ref, error). The fields and the agent reference are both checked here."""
    val_err = _validate_stamp_fields(arguments)
    if val_err:
        return None, val_err
    return _agent_ref_for(arguments, meta)


def handle_stamp(arguments: dict[str, Any], meta: dict[str, Any] | None = None) -> dict[str, Any]:
    global SESSION_CHAIN
    agent_ref, input_err = _checked_stamp_input(arguments, meta)
    if input_err:
        return _err_res(input_err)

    save_path = arguments.get("save_path") or DEFAULT_RECEIPTS_PATH
    loaded_chain, load_err = _load_existing_chain_fail_closed(save_path)
    if load_err:
        return _err_res(load_err)
    if loaded_chain is not None:
        SESSION_CHAIN = loaded_chain

    pin_file = arguments.get("pin_file")
    witness_url = arguments.get("witness_url")
    gate_err = _stamp_gates(pin_file, witness_url)
    if gate_err:
        return _err_res(gate_err)

    try:
        receipt = _stamp_and_persist(arguments, agent_ref, save_path, pin_file)
    except Exception as e:
        return _err_res(f"Failed to stamp receipt: {e}")

    unwitnessed = _witness_record(witness_url)
    if unwitnessed:
        return _err_res(unwitnessed)

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


def _witness_verdict(receipts: list[Any], pins: list[Any], key_file: str | None) -> tuple[bool, str, bool]:
    """(matched, reason, macs_checked)."""
    if not key_file:
        pin_ok, why = check_pins(receipts, pins)
        return pin_ok, why, False
    try:
        key = load_key(key_file)
    except (OSError, ValueError) as e:
        return False, f"the witness key is unusable: {e}", False
    pin_ok, why = check_witnessed(receipts, pins, key)
    return pin_ok, why, True


def _witness_check(receipts: list[Any], url: str | None, key_file: str | None) -> dict[str, Any] | None:
    if not url:
        return None
    pins, err = fetch_pins(url)
    if err or pins is None:
        return {"matched": False, "reason": err, "pins": 0, "macs_checked": False}
    if not pins:
        return {"matched": False, "reason": "the witness holds no pins, so nothing was checked", "pins": 0, "macs_checked": False}
    matched, why, macs = _witness_verdict(receipts, pins, key_file)
    return {"matched": matched, "reason": why or "every witnessed pin is still in the chain",
            "pins": len(pins), "macs_checked": macs}


def _pin_check(receipts: list[Any], pin_file: str | None) -> dict[str, Any] | None:
    if not pin_file:
        return None
    pins, pin_err = _read_pins(pin_file)
    if pin_err:
        return {"matched": False, "reason": pin_err, "pins": 0}
    if not pins:
        return {"matched": False, "reason": "the pin file holds no pins, so nothing was checked", "pins": 0}
    pin_ok, why = check_pins(receipts, pins)
    return {"matched": pin_ok, "reason": why or "every pin is still in the chain", "pins": len(pins)}


def handle_verify(arguments: dict[str, Any], meta: dict[str, Any] | None = None) -> dict[str, Any]:
    receipts, err = _load_verify_receipts(arguments.get("file_path"), arguments.get("receipts_json"))
    if err:
        return _err_res(err)
    if not isinstance(receipts, list):
        return _err_res("Receipts data must be a JSON array.")

    ok, bad = verify(receipts)
    head = receipts[-1].get("seal", GENESIS) if receipts else GENESIS
    msg = f"{len(receipts)} receipts, every seal holds." if ok else f"BROKEN at receipt {bad}."
    pin_check = _pin_check(receipts, arguments.get("pin_file"))
    witness_check = _witness_check(receipts, arguments.get("witness_url"), arguments.get("witness_key_file"))

    return {
        "content": [{
            "type": "text",
            "text": json.dumps({
                "verified": ok,
                "receipt_count": len(receipts),
                "head": head,
                "broken_at_receipt": bad if not ok else None,
                "message": msg,
                "pin_check": pin_check,
                "witness_check": witness_check,
                "note": "Proves no entry was edited. Proving no tail deletion or backdating requires comparing the head seal against an external anchor. With a pin_file it also shows the chain still contains every pin it was given; a pin kept on the same disk as the chain is only as safe as that disk, and a pin never says who changed what. It does not raise the assurance level. A witness_url compares the chain against a separate witness; its MACs are checked only with witness_key_file, a key the agent must never hold, and a MAC is symmetric so it proves nothing to anyone without that key."
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


def handle_disclose(arguments: dict[str, Any], meta: dict[str, Any] | None = None) -> dict[str, Any]:
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


def handle_status(arguments: dict[str, Any], meta: dict[str, Any] | None = None) -> dict[str, Any]:
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


def _execute_tool(tool_name: str | None, args: dict[str, Any],
                  meta: dict[str, Any] | None = None) -> dict[str, Any]:
    handler = TOOL_HANDLERS.get(tool_name or "")
    if not handler:
        raise KeyError(f"Tool not found: {tool_name}")
    return handler(args, meta)


def _handle_tools_call(req: dict[str, Any], msg_id: Any, meta: dict[str, Any] | None) -> dict[str, Any]:
    params = req.get("params") or {}
    try:
        res = _execute_tool(params.get("name"), params.get("arguments") or {}, meta)
        return {"jsonrpc": "2.0", "id": msg_id, "result": res}
    except KeyError as e:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": str(e)}}
    except Exception as e:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32000, "message": str(e)}}


def _error(msg_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": msg_id, "error": err}


def _discover(msg_id: Any) -> dict[str, Any]:
    """server/discover, which the 2026-07-28 revision says every server MUST implement."""
    return {"jsonrpc": "2.0", "id": msg_id, "result": {
        "resultType": "complete",
        "supportedVersions": list(SUPPORTED_VERSIONS),
        "capabilities": {"tools": {}},
        "_meta": {META_SERVER: SERVER_INFO},
        "ttlMs": 3600000, "cacheScope": "public"}}


def _gate(req: dict[str, Any], msg_id: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None, bool]:
    """(error to send or None, this request's _meta, is it a modern request).

    Stateless: everything is decided from THIS request. A request with no protocol
    version in its _meta is a legacy client that went through `initialize`.
    """
    params = req.get("params")
    meta = params.get("_meta") if isinstance(params, dict) else None
    version = meta.get(META_VERSION) if isinstance(meta, dict) else None
    if version is None:
        return None, None, False
    if version not in SUPPORTED_VERSIONS:
        return _error(msg_id, -32022, "Unsupported protocol version",
                      {"supported": list(SUPPORTED_VERSIONS), "requested": version}), None, False
    if version == MODERN_VERSION and not (isinstance(meta, dict) and isinstance(meta.get(META_CAPS), dict)):
        return _error(msg_id, -32602, "Invalid params: _meta must carry %s and %s"
                      % (META_VERSION, META_CAPS)), None, False
    return None, meta, version == MODERN_VERSION


def _route(req: dict[str, Any], msg_id: Any, meta: dict[str, Any] | None) -> dict[str, Any]:
    method = req.get("method")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {
            "protocolVersion": PROTOCOL_VERSION, "serverInfo": SERVER_INFO,
            "capabilities": {"tools": {}}}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if method == "server/discover":
        return _discover(msg_id)
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        return _handle_tools_call(req, msg_id, meta)
    if method == "notifications/initialized":
        return {}
    if msg_id is not None:
        return _error(msg_id, -32601, f"Method not supported: {method}")
    return {}


def dispatch(req: Any) -> dict[str, Any]:
    if not isinstance(req, dict):
        return _error(None, -32600, "Invalid request: a JSON-RPC request must be an object")
    msg_id = req.get("id")
    if req.get("method") == "server/discover":
        return _discover(msg_id)
    failure, meta, modern = _gate(req, msg_id)
    if failure:
        return failure
    resp = _route(req, msg_id, meta)
    if modern and isinstance(resp.get("result"), dict):
        resp["result"].setdefault("_meta", {})[META_SERVER] = SERVER_INFO
    return resp


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
