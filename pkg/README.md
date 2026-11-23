# knowyouragenticai-receipts

**Let an automated execution pay, and prove what it couldn't.**

A tamper-evident record of every payment attempt — including the refusals — for
automated Canton applications. Built for Canton Network; works anywhere. Zero
dependencies.

---

If you let software spend money on your behalf, someone will eventually ask you
a question your logs cannot answer: **"what did it try to do that you stopped?"**

Ordinary logs record what succeeded. That is the wrong half. The half that
matters to an auditor, a regulator, or the person whose money it was, is the
attempt that was refused — and whether anyone could have quietly removed it
afterwards.

This keeps both. Every attempt gets an entry, allowed or refused, and each entry
is sealed to the one before it. Change any entry and every seal after it breaks.

```bash
pip install knowyouragenticai-receipts
```

```python
from knowyouragenticai_receipts import Chain

chain = Chain(approved_by="finance", ledger="stripe")

chain.allowed(what="invoice 41", amount="250.00", currency="USD",
              payee="Acme Ltd", rule="under the cap")

chain.refused(what="invoice 42", amount="9000.00", currency="USD",
              payee="Unknown Co", rule="payee is not on the allow-list")

chain.verify()      # (True, 0)
chain.head          # the one value that stands for the whole chain
```

`allowed()` and `refused()` are the two things you do. Who authorised the
payments and which rail they ran on describe the desk, not the payment, so they
are set once when the chain is made. `stamp()` is there when you need full
control.

There is a runnable version of the whole idea in
`python -m knowyouragenticai_receipts example` — an application with a spending limit, four attempts, two
stopped, and the record being tampered with and caught:

```bash
python -m knowyouragenticai_receipts example
```

Change any field of any receipt and:

```python
chain.receipts[0]["amount"] = "9999.0"
chain.verify()      # (False, 1)  -- and every seal after it is broken too
```

## Checking a file with nothing installed

The person who most needs to check a payment record is the least likely to have
a terminal open. **Drag the file onto
[the verifier page](https://github.com/dominicrume/cantor8_kya_rails/blob/main/step-3-verify/verifier.html)** — it is read in your own
browser, nothing is uploaded, and it works with no network.

Or from a shell:

```bash
python -m knowyouragenticai_receipts verify receipts.json
```

Both give three answers, and the third one matters:

| | exit | |
| --- | --- | --- |
| **holds** | 0 | every seal recomputed; nothing was edited |
| **BROKEN at N** | 1 | that entry or one before it was changed after the fact |
| **not a receipt chain** | 2 | valid JSON, different kind of file — **not** an accusation |

Calling an ordinary export "tampered" is a false accusation of the most serious
kind this format makes. A wrapped chain (`{"receipts": [...]}`) is found and
checked; a config file is told apart from a forgery.

## Model Context Protocol (MCP) Server

Connect KYA Receipts directly to any tool that speaks MCP (Claude Desktop, Claude Code, Cursor):

```bash
# macOS / Linux:
claude mcp add kya-receipts -- python3 -m knowyouragenticai_receipts mcp

# Windows (PowerShell / Command Prompt):
claude mcp add kya-receipts -- python -m knowyouragenticai_receipts mcp

# Or via installed console script (cross-platform):
claude mcp add kya-receipts -- kya-receipts-mcp
```

> **Windows Tip:** On Windows developer machines, typing `python3` frequently triggers the Microsoft Store stub (*"Python was not found"*). Use `python` (or `py`, or `kya-receipts-mcp`), or disable the Windows Store alias in *Settings > Apps > Advanced app settings > App execution aliases*.

Or add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "kya-receipts": {
      "command": "python",
      "args": ["-m", "knowyouragenticai_receipts", "mcp"]
    }
  }
}
```
*(On macOS/Linux, set `"command": "python3"` or use your virtualenv Python path).*

Exposes tools:
- `kya_stamp`: Append an action (accepted or refused) and cryptographically seal onto previous seal. Fail-closed against tampered files; atomically writes state; defaults persistence to `receipts.json`.
- `kya_verify`: Verify chain integrity from a file or JSON payload (proves no edits/reordering; caveats external anchor requirement for tail deletion).
- `kya_disclose`: Redact and disclose refusals while withholding confidential payments (safe overwrite protection).
- `kya_status`: Inspect the active session chain head, verification state, and receipt counts. Reports `file_problem` if the receipts file on disk is tampered or unreadable, instead of quietly describing the in-memory chain.

**Stateless protocol.** The server speaks the MCP 2026-07-28 revision, where there is no `initialize` handshake: every request carries its protocol version and capabilities in `_meta`, and `server/discover` says what the server supports. A client that still performs the old handshake works as before. Nothing is remembered between requests.

**Pointing at an identity (`agent_ref`).** `kya_stamp` takes an optional `agent_ref`: a DID, an Agent Passport id, an OAuth client id, at most 256 ASCII characters. If you omit it, the client name and version from the request's `_meta` are recorded as `mcp-client:name/version`. That is a label the caller chose, not an authenticated identity. `agent_ref` is written by the caller and establishes nothing, so a verifier still reports `self-attested`; it exists so an identity system can point at a chain without this format competing with it (SPEC section 6e).

## Prove this build implements the specification

The conformance vectors ship inside the package, so this works offline:

```bash
python -m knowyouragenticai_receipts
# CONFORMANT: 16/16 cases. This build implements the specification.
```

## The format, in full

`seal = sha256(canonical(body) + prev)`, where `canonical` is JSON with keys
sorted by code point at every level, `,` and `:` as separators with no spaces,
and non-ASCII escaped to `\uXXXX`. `prev` is the previous receipt's seal, or the
literal string `GENESIS`.

That is the whole thing. It is about twenty lines in any language, and
[the specification](https://github.com/dominicrume/cantor8_kya_rails/blob/main/SPEC.md)
is one page. There are implementations in Python, JavaScript and Go, and a
grader that will tell you in one command whether yours is right:

```bash
python3 tests/conformance_any.py -- ./your-implementation   # from a clone of the repo
```

**A new implementation is the most valuable contribution this format can
receive.** Two of the sixteen vectors exist because someone asked which *wrong*
implementations still passed — and two did: one emitting raw UTF-8 where the
spec requires `\uXXXX`, and one that checked every seal but never compared the
`prev` link.

## What this does not do

A format that oversells itself is worse than none, so:

- **It is not signed.** It proves internal consistency, not origin. Anyone can
  produce a valid chain saying anything, and a forged one verifies. Bind the
  final seal to something you do not control if origin matters — the reference
  application publishes it as a contract on a Canton ledger.
- **It does not prove a rule was enforced.** `rule` is a string. The guarantee
  comes from wherever the decision was actually made.
- **It makes editing detectable, not deletion.** Publish the head somewhere else
  if discarding the whole chain matters.

## Why amounts are strings

A float that survives one language's JSON encoder is not a float that survives
all of them. The seal computed over `"1.0"` is not the seal computed over `"1"`,
and a chain that verifies only on the machine that wrote it is not a chain.

## Why no dependencies

The whole format is `json` and `hashlib`. A dependency here would be a
dependency in everyone's audit trail.

---

MIT. Built as part of [KYA Rails](https://github.com/dominicrume/cantor8_kya_rails),
a spend-limited deterministic settlement wallet for Canton.
