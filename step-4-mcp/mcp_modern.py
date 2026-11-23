"""The stateless (revision 2026-07-28) protocol layer, shared by the step-4 servers.

MCP 2026-07-28 retired the `initialize` handshake and the session header. Every request
carries its protocol version, capabilities and caller in `params._meta`, a server MUST
implement `server/discover`, a request missing a required `_meta` field is -32602, and an
unsupported version is -32022 listing what the server does support. Nothing may be
inferred from an earlier request.

These servers stay dual-era: a request with no protocol version in its `_meta` is a
legacy client that went through `initialize`, and is handled exactly as before.

The receipts package carries its own copy of this logic, because it ships on its own and
cannot import from a repository folder. tests/mcp_modern_smoke.py drives all three.

Stdlib only, per THE-RULES.md.
"""
MODERN = "2026-07-28"
SUPPORTED = ("2026-07-28", "2025-11-25", "2024-11-05")
META_VERSION = "io.modelcontextprotocol/protocolVersion"
META_CAPS = "io.modelcontextprotocol/clientCapabilities"
META_CLIENT = "io.modelcontextprotocol/clientInfo"
META_SERVER = "io.modelcontextprotocol/serverInfo"


def error(mid, code, message, data=None):
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": mid, "error": err}


def discover(mid, server_info):
    """The result of server/discover, which every server MUST implement."""
    return {"jsonrpc": "2.0", "id": mid, "result": {
        "resultType": "complete", "supportedVersions": list(SUPPORTED),
        "capabilities": {"tools": {}}, "_meta": {META_SERVER: server_info},
        "ttlMs": 3600000, "cacheScope": "public"}}


def gate(msg, mid):
    """(error to send or None, this request's _meta, is it a modern request)."""
    params = msg.get("params")
    meta = params.get("_meta") if isinstance(params, dict) else None
    version = meta.get(META_VERSION) if isinstance(meta, dict) else None
    if version is None:
        return None, None, False
    if version not in SUPPORTED:
        return error(mid, -32022, "Unsupported protocol version",
                     {"supported": list(SUPPORTED), "requested": version}), None, False
    if version == MODERN and not (isinstance(meta, dict) and isinstance(meta.get(META_CAPS), dict)):
        return error(mid, -32602, "Invalid params: _meta must carry %s and %s"
                     % (META_VERSION, META_CAPS)), None, False
    return None, meta, version == MODERN


def finish(resp, server_info, modern):
    """A modern result names the server in its _meta, so nothing depends on a handshake."""
    if modern and isinstance(resp, dict) and isinstance(resp.get("result"), dict):
        resp["result"].setdefault("_meta", {})[META_SERVER] = server_info
    return resp
