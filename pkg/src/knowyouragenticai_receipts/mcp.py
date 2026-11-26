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
from typing import Any, Mapping, NamedTuple

from . import _safe
from . import (
    GENESIS,
    BrokenChain,
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

# What this process last COMMITTED to each chain file, keyed by realpath. An entry is
# written only after the file write succeeded, and is a cache and a tripwire (kya_status
# can say "the file went missing"), never the source of truth: the file is read, verified
# and extended under a lock on every stamp.
STORE: dict[str, Chain] = {}

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
                "pin_file": {
                    "type": "string",
                    "description": "Optional. A pin log in use. Only guards it: save_path equal to it is refused."
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
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Optional. The chain file to report on. Defaults to 'receipts.json'."
                }
            }
        }
    }
]


def log(msg: str) -> None:
    print(f"[kya-receipts-mcp] {msg}", file=sys.stderr, flush=True)


def _atomic_write_json(path: str, data: Any) -> None:
    """Write data to path atomically (unpredictable temp name, O_EXCL, fsync, replace)."""
    _safe.atomic_write_json(path, data)


class Loaded(NamedTuple):
    """What load_verified found. `error` is set when nothing usable was read."""
    receipts: list[Any] | None
    ok: bool            # the chain verifies (meaningless when error is set)
    broken_at: int      # first bad receipt when ok is False
    error: str | None   # why nothing usable was read; None when receipts is a list


def check_receipts(data: Any, origin: str) -> Loaded:
    """Verify an already parsed value. Anything that is not a JSON array is an error."""
    if not isinstance(data, list):
        return Loaded(None, False, 0, f"{origin} does not contain a JSON array of receipts.")
    ok, bad = verify(data)
    return Loaded(data, ok, bad, None)


def load_verified(path: str) -> Loaded:
    """THE read: a chain file, bounded, parsed and verified, or an error. Never a default.

    A missing file, an unparseable one, a non-array, a FIFO or device, or one over
    the size cap each come back as `error`. kya_status, kya_disclose, kya_verify and
    kya_stamp all read through here, so none of them can invent an empty chain.
    """
    if not os.path.exists(path):
        return Loaded(None, False, 0, f"File not found: {path}")
    try:
        data = _safe.read_json(path)
    except (OSError, ValueError) as e:      # Rejected and decode errors are ValueErrors
        return Loaded(None, False, 0, f"Could not read receipts: {e}")
    return check_receipts(data, _safe._shown(path))


def _chain_if_good(loaded: Loaded) -> Chain | None:
    return Chain(loaded.receipts) if loaded.receipts is not None and loaded.ok else None


_PROTECTED: set[str] = set()   # realpaths of chain and pin files this process has used


def _remember(*paths: str | None) -> None:
    for p in paths:
        if p:
            _PROTECTED.add(os.path.realpath(p))


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
        for number, line in enumerate(_safe.read_text(path).splitlines(), start=1):
            if line.strip():
                pins.append(_safe.parse_json(line))
    except (OSError, ValueError) as e:      # Rejected and UnicodeDecodeError are ValueErrors
        return [], f"pin file {path} is unreadable near line {number}: {e}"
    return pins, None


def _append_pin(path: str, pin: dict[str, Any]) -> None:
    """Append one pin and force it to disk. Never rewrites an earlier line."""
    _safe.append_line(path, json.dumps(pin, sort_keys=True) + "\n")


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
    loaded = load_verified(path)
    chain = _chain_if_good(loaded)
    if chain is not None:
        return chain, None
    why = loaded.error or f"BROKEN at receipt {loaded.broken_at}"
    return None, (
        f"Refusing to stamp: existing file at '{path}' does not verify ({why}). "
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


def _pin_gate(pin_file: str | None, chain: Chain) -> str | None:
    """Error text if `chain` does not match the pin log, else None."""
    if not pin_file:
        return None
    pins, pin_err = _read_pins(pin_file)
    if pin_err:
        return pin_err
    pins_ok, why = check_pins(chain.receipts, pins)
    if pins_ok:
        return None
    return f"Refusing to stamp: this chain does not match the pin log ({why}). Nothing was written."


def _stamp_and_persist(arguments: dict[str, Any], agent_ref: Any, save_path: str, chain: Chain) -> Any:
    """Stamp onto `chain` (a private copy), write the file, and only THEN commit to STORE.

    If the write raises, STORE and the file are exactly as they were, and a retry
    builds the same receipt number again.
    """
    receipt = chain.stamp(
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
    _atomic_write_json(save_path, chain.receipts)
    STORE[os.path.realpath(save_path)] = chain
    return receipt


def _same_file(a: str | None, b: str) -> bool:
    return bool(a) and os.path.realpath(str(a)) == os.path.realpath(b)


def _stamp_preflight(arguments: dict[str, Any], meta: dict[str, Any] | None) -> tuple[Any, str, str | None]:
    """(agent_ref, save_path, error). Everything that can be refused before a file is read."""
    save_path = arguments.get("save_path") or DEFAULT_RECEIPTS_PATH
    val_err = _validate_stamp_fields(arguments)
    if val_err:
        return "", save_path, val_err
    agent_ref, ref_err = _agent_ref_for(arguments, meta)
    if ref_err:
        return "", save_path, ref_err
    if _same_file(arguments.get("pin_file"), save_path):
        return "", save_path, "Refusing to stamp: pin_file and save_path are the same file."
    return agent_ref, save_path, None


def _base_chain(save_path: str) -> tuple[Chain | None, str | None]:
    """The chain to extend: the file's (verified), else a COPY of what this process last
    committed to that path, else an empty one. Never another file's chain."""
    chain, err = _load_existing_chain_fail_closed(save_path)
    if err or chain is not None:
        return chain, err
    known = STORE.get(os.path.realpath(save_path))
    return (Chain(known.receipts) if known is not None else Chain()), None


def _stamp_reply(receipt: Any, chain: Chain, save_path: str) -> dict[str, Any]:
    return {
        "content": [{
            "type": "text",
            "text": json.dumps({
                "receipt": receipt,
                "chain_head": chain.head,
                "total_receipts": len(chain),
                "saved_to": save_path
            }, indent=2)
        }]
    }


def _append_pin_after_write(pin_file: str | None, chain: Chain, save_path: str) -> str | None:
    """Error text if the pin could not be appended. The receipt is already in the file."""
    if not pin_file:
        return None
    try:
        _append_pin(pin_file, head_pin(chain.receipts))
    except OSError as e:
        return f"The receipt WAS written to '{save_path}' but its pin could not be appended: {e}"
    return None


def _stamp_under_lock(arguments: dict[str, Any], agent_ref: Any, save_path: str) -> dict[str, Any]:
    """Read, verify, pin-check, append and write: all inside the lock."""
    chain, load_err = _base_chain(save_path)
    pin_file = arguments.get("pin_file")
    gate_err = load_err or (_pin_gate(pin_file, chain) if chain is not None else None)
    if gate_err or chain is None:
        return _err_res(gate_err or "no chain")
    try:
        receipt = _stamp_and_persist(arguments, agent_ref, save_path, chain)
    except Exception as e:
        return _err_res(f"Failed to stamp receipt: {e}")
    _remember(save_path, pin_file)
    pin_err = _append_pin_after_write(pin_file, chain, save_path)
    return _err_res(pin_err) if pin_err else _stamp_reply(receipt, chain, save_path)


def handle_stamp(arguments: dict[str, Any], meta: dict[str, Any] | None = None) -> dict[str, Any]:
    agent_ref, save_path, pre_err = _stamp_preflight(arguments, meta)
    if pre_err:
        return _err_res(pre_err)
    try:
        with _safe.file_lock(save_path):
            return _stamp_under_lock(arguments, agent_ref, save_path)
    except (OSError, _safe.Rejected) as e:      # the lock could not be taken
        return _err_res(f"Failed to stamp receipt: {e}")


def _verify_source(file_path: str | None, receipts_json: str | None) -> Loaded:
    if file_path:
        return load_verified(file_path)
    if receipts_json:
        try:
            return check_receipts(_safe.parse_json(receipts_json), "receipts_json")
        except ValueError as e:
            return Loaded(None, False, 0, f"Invalid JSON string: {e}")
    return load_verified(DEFAULT_RECEIPTS_PATH)


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
    loaded = _verify_source(arguments.get("file_path"), arguments.get("receipts_json"))
    if loaded.error or loaded.receipts is None:
        return _err_res(loaded.error or "No receipts to verify.")
    receipts, ok, bad = loaded.receipts, loaded.ok, loaded.broken_at
    head = receipts[-1].get("seal", GENESIS) if receipts else GENESIS
    msg = f"{len(receipts)} receipts, every seal holds." if ok else f"BROKEN at receipt {bad}."
    _remember(arguments.get("pin_file"))
    pin_check = _pin_check(receipts, arguments.get("pin_file"))

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
                "note": "Proves no entry was edited. Proving no tail deletion or backdating requires comparing the head seal against an external anchor. With a pin_file it also shows the chain still contains every pin it was given; a pin kept on the same disk as the chain is only as safe as that disk, and a pin never says who changed what. It does not raise the assurance level."
            }, indent=2)
        }]
    }


def _is_evidence_file(arguments: dict[str, Any], source: str, target: str) -> bool:
    """True if `target` (a realpath) is the chain being read, the default chain, or a pin log."""
    known = {os.path.realpath(source), os.path.realpath(DEFAULT_RECEIPTS_PATH)} | _PROTECTED
    pin = arguments.get("pin_file")
    if pin:
        known.add(os.path.realpath(pin))
    return target in known


def _disclose_refusal(arguments: dict[str, Any], source: str) -> str | None:
    """Why this disclosure must not be written, or None. Nothing is read or written yet."""
    save_path = arguments.get("save_path")
    if not save_path:
        return None
    if _is_evidence_file(arguments, source, os.path.realpath(save_path)):
        return (f"Refusing to write the disclosure over '{save_path}': it is the receipt chain or a "
                "pin log. The evidence is never overwritten by a view of itself.")
    if os.path.exists(save_path) and not arguments.get("overwrite"):
        return f"File already exists at '{save_path}'. Pass overwrite=true to explicitly allow replacing this file."
    return None


def _ok_receipts(loaded: Loaded) -> tuple[list[Any] | None, str | None]:
    """(receipts, None) only for a chain that was read and verifies; else (None, why)."""
    if loaded.error or loaded.receipts is None:
        return None, f"Refusing to disclose: {loaded.error or 'no receipts'}."
    if not loaded.ok:
        return None, (f"Refusing to disclose: the chain does not verify (BROKEN at receipt "
                      f"{loaded.broken_at}). A disclosure of a tampered chain would vouch for it.")
    return loaded.receipts, None


def handle_disclose(arguments: dict[str, Any], meta: dict[str, Any] | None = None) -> dict[str, Any]:
    save_path = arguments.get("save_path")
    source = arguments.get("file_path") or DEFAULT_RECEIPTS_PATH
    refusal = _disclose_refusal(arguments, source)
    if refusal:
        return _err_res(refusal)
    receipts, why = _ok_receipts(load_verified(source))
    if why or receipts is None:
        return _err_res(why or "no receipts")
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


def _status_result(body: dict[str, Any], is_error: bool) -> dict[str, Any]:
    res: dict[str, Any] = {"content": [{"type": "text", "text": json.dumps(body, indent=2)}]}
    if is_error:
        res["isError"] = True
    return res


def _status_view(path: str) -> tuple[list[Any] | None, bool, int, str | None]:
    """(receipts or None, verifies, broken_at, problem) for what kya_status reports on."""
    if os.path.exists(path):
        loaded = load_verified(path)
        broken = None if loaded.error or loaded.ok else f"BrokenChain: {path} does not verify: receipt {loaded.broken_at}."
        return loaded.receipts, loaded.ok, loaded.broken_at, loaded.error or broken
    known = STORE.get(os.path.realpath(path))
    if known is None:
        return [], True, 0, None            # nothing stamped to this path yet: an empty chain
    return known.receipts, False, 0, (
        f"File not found: {path}, but this process committed {len(known)} receipts to it. "
        "The file has been removed or moved since.")


def _count_and_head(receipts: list[Any] | None) -> tuple[int | None, str | None]:
    if receipts is None:
        return None, None
    return len(receipts), (receipts[-1].get("seal", GENESIS) if receipts else GENESIS)


def handle_status(arguments: dict[str, Any], meta: dict[str, Any] | None = None) -> dict[str, Any]:
    path = arguments.get("file_path") or DEFAULT_RECEIPTS_PATH
    receipts, ok, bad, problem = _status_view(path)
    # The file on disk is the record. If it cannot be read or does not verify, saying
    # nothing and reporting an in-memory chain instead would hide exactly what an
    # auditor needs to know: so a file problem is verified:false, and no count or head.
    count, head = _count_and_head(receipts)
    body = {
        "receipt_count": count,
        "chain_head": head,
        "verified": bool(ok and receipts is not None),
        "broken_at": bad if receipts is not None and not ok else None,
        "storage": f"persisting to {path} by default unless overridden by save_path",
        "active_file": path if os.path.exists(path) else None,
        "file_problem": problem,
        "note": "Agent MCP stamps are self-attested. Standalone verification proves no edits; anchor chain_head externally to prove non-truncation.",
        "version": __version__
    }
    return _status_result(body, problem is not None)


TOOL_HANDLERS = {
    "kya_stamp": handle_stamp,
    "kya_verify": handle_verify,
    "kya_disclose": handle_disclose,
    "kya_status": handle_status,
}


STR_FIELDS = {
    "kya_stamp": ("what", "currency", "payee", "rule", "outcome", "approved_by", "ledger",
                  "agent_ref", "save_path", "pin_file"),
    "kya_verify": ("file_path", "receipts_json", "pin_file"),
    "kya_disclose": ("file_path", "save_path", "pin_file"),
    "kya_status": ("file_path",),
}
BOOL_FIELDS = {"kya_disclose": ("overwrite",)}


def _bad_string(tool: str, args: dict[str, Any]) -> str | None:
    for key in STR_FIELDS[tool]:
        value = args.get(key)
        if value is not None and not isinstance(value, str):
            return f"Field '{key}' must be a string."
        if value is not None and len(value) > _safe.MAX_FIELD_CHARS:
            return f"Field '{key}' is longer than {_safe.MAX_FIELD_CHARS} characters."
    return None


def _bad_bool(tool: str, args: dict[str, Any]) -> str | None:
    for key in BOOL_FIELDS.get(tool, ()):
        if args.get(key) is not None and not isinstance(args[key], bool):
            return f"Field '{key}' must be true or false."
    return None


def _bad_amount(args: dict[str, Any]) -> str | None:
    """A string, or (as before) a plain number. Anything else, or a huge string, is refused."""
    amount = args.get("amount")
    if isinstance(amount, str):
        return None if len(amount) <= _safe.MAX_FIELD_CHARS else "Field 'amount' is too long."
    if amount is None or (isinstance(amount, (int, float)) and not isinstance(amount, bool)):
        return None
    return "Field 'amount' must be a string."


def _bad_argument(tool: str, args: dict[str, Any]) -> str | None:
    """Why `args` are not acceptable for `tool`, or None. Runs BEFORE any file is touched."""
    found = _bad_string(tool, args) or _bad_bool(tool, args)
    if found or tool != "kya_stamp":
        return found
    return _bad_amount(args)


def _execute_tool(tool_name: str | None, args: dict[str, Any],
                  meta: dict[str, Any] | None = None) -> dict[str, Any]:
    bad = _bad_argument(str(tool_name), args)
    if bad:
        return _err_res(bad)
    return TOOL_HANDLERS[str(tool_name)](args, meta)


def _call_shape(req: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    """(tool name, arguments) if tools/call params have the right shape, else None."""
    params = {} if req.get("params") is None else req.get("params")
    if not isinstance(params, dict):
        return None
    name, arguments = params.get("name"), params.get("arguments")
    if not isinstance(name, str) or not (arguments is None or isinstance(arguments, dict)):
        return None
    return name, arguments or {}


def _handle_tools_call(req: dict[str, Any], msg_id: Any, meta: dict[str, Any] | None) -> dict[str, Any]:
    shape = _call_shape(req)
    if shape is None:
        return _error(msg_id, -32602, "Invalid params: 'name' must be a string and 'arguments' an object")
    name, arguments = shape
    if name not in TOOL_HANDLERS:
        return _error(msg_id, -32602, f"Unknown tool: {name[:64]}")
    try:
        return {"jsonrpc": "2.0", "id": msg_id, "result": _execute_tool(name, arguments, meta)}
    except Exception as e:  # noqa: BLE001 - any failure becomes an isError result; the loop goes on
        log(f"tool {name} failed: {type(e).__name__}")
        return {"jsonrpc": "2.0", "id": msg_id, "result": _err_res(
            f"Internal error ({type(e).__name__}); the request was not completed.")}


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
    if not _safe.id_is_sane(msg_id):
        return _error(None, -32600, "Invalid request: id is too long or not strict JSON")
    if req.get("method") == "server/discover":
        return _discover(msg_id)
    failure, meta, modern = _gate(req, msg_id)
    if failure:
        return failure
    resp = _route(req, msg_id, meta)
    if modern and isinstance(resp.get("result"), dict):
        resp["result"].setdefault("_meta", {})[META_SERVER] = SERVER_INFO
    return resp


def _emit(resp: dict[str, Any]) -> bool:
    """Write one reply as strict JSON. False if stdout is gone."""
    try:
        text = json.dumps(resp, allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        text = json.dumps(_error(None, -32603, "Internal error: reply could not be encoded"))
    try:
        print(text, flush=True)
    except (BrokenPipeError, OSError):
        return False
    return True


def _parse_request(line: bytes) -> tuple[Any, dict[str, Any] | None]:
    """(request, error reply). Bytes that are not UTF-8 are replaced, never fatal."""
    try:
        return _safe.parse_json(line.decode("utf-8", errors="replace"), reject_duplicate_keys=True), None
    except ValueError as e:     # JSONDecodeError and Rejected
        return None, _error(None, -32700, f"Parse error: {e}")


def _serve_one(stream: Any) -> bool:
    """Read and answer one message. False at end of input or when stdout is gone."""
    line, too_long = _safe.read_message(stream)
    if line is None:
        return False
    if too_long:
        return _emit(_error(None, -32600, f"Invalid request: message longer than {_safe.MAX_LINE_BYTES} bytes"))
    if not line.strip():
        return True
    req, err = _parse_request(line)
    resp = err if err else dispatch(req)
    return _emit(resp) if resp else True


def main() -> int:
    log(f"Starting KYA Receipts MCP Server v{__version__}...")
    stream = sys.stdin.buffer
    while True:
        try:
            if not _serve_one(stream):
                return 0
        except Exception as e:  # noqa: BLE001 - the loop must outlive any one message
            log(f"message failed: {type(e).__name__}")
            if not _emit(_error(None, -32603, f"Internal error ({type(e).__name__})")):
                return 0


if __name__ == "__main__":
    sys.exit(main())
