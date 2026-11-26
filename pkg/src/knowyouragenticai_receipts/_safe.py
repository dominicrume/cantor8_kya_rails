"""Bounded, non-blocking I/O and strict JSON parsing for the MCP server.

Nothing an agent sends may end the server process or hang it. That is an
availability rule, and it lives here so every handler gets it the same way:

  * a file is opened O_NONBLOCK and fstat()ed, and refused unless it is a
    regular file (a FIFO would block open() forever, /dev/zero never ends);
  * at most MAX_FILE_BYTES are ever read from one file;
  * JSON is parsed with limits on nesting, integer digits and float range, and
    never accepts NaN or Infinity, so the server can never print them back;
  * strings that name a path or a field are limits-checked before use.

Standard library only.
"""
from __future__ import annotations

import json
import os
import re
import stat
from typing import Any, BinaryIO

MAX_FILE_BYTES = 64 * 1024 * 1024    # one input file (chain, pin log)
MAX_LINE_BYTES = 16 * 1024 * 1024    # one JSON-RPC message on stdin
MAX_FIELD_CHARS = 64 * 1024          # one string argument
MAX_DEPTH = 64                       # JSON nesting
MAX_INT_DIGITS = 40                  # any integer in a request
MAX_ID_CHARS = 256                   # a request id, as serialised

_STRINGS = re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"', re.S)
_BRACKETS = re.compile(r'[\[\]{}]')
_NONBLOCK = getattr(os, "O_NONBLOCK", 0)


class Rejected(ValueError):
    """Input refused for a stated reason. The message is safe to show the caller."""


# ------------------------------------------------------------------ JSON
def _no_constant(name: str) -> Any:
    raise Rejected("JSON constant %s is not accepted" % name)


def _parse_int(text: str) -> int:
    if len(text.lstrip("-")) > MAX_INT_DIGITS:
        raise Rejected("integer longer than %d digits" % MAX_INT_DIGITS)
    return int(text)


def _parse_float(text: str) -> float:
    value = float(text)
    if value != value or value in (float("inf"), float("-inf")):
        raise Rejected("number out of range")
    return value


def _depth_exceeds(text: str, limit: int) -> bool:
    """True if brackets nest deeper than `limit` outside of strings.

    A C-speed count rules out almost everything first; the slow scan only runs
    for text that has more than `limit` openers in total.
    """
    if text.count("[") + text.count("{") <= limit:
        return False
    depth = 0
    for ch in _BRACKETS.findall(_STRINGS.sub('""', text)):
        depth += 1 if ch in "[{" else -1
        if depth > limit:
            return True
    return False


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise Rejected("duplicate key %s" % json.dumps(key[:64]))
        out[key] = value
    return out


def parse_json(text: str, *, reject_duplicate_keys: bool = False) -> Any:
    """json.loads with limits. Raises Rejected or json.JSONDecodeError (both ValueError)."""
    if _depth_exceeds(text, MAX_DEPTH):
        raise Rejected("JSON nested deeper than %d levels" % MAX_DEPTH)
    try:
        return json.loads(
            text, parse_constant=_no_constant, parse_int=_parse_int, parse_float=_parse_float,
            object_pairs_hook=_no_duplicates if reject_duplicate_keys else None)
    except RecursionError:
        raise Rejected("JSON nested too deeply") from None


def id_is_sane(msg_id: Any) -> bool:
    """A request id we are willing to echo: short once serialised, and strict JSON."""
    try:
        return len(json.dumps(msg_id, allow_nan=False)) <= MAX_ID_CHARS
    except (TypeError, ValueError, RecursionError):
        return False


# ----------------------------------------------------------------- files
def _open_regular(path: str, flags: int) -> int:
    """A file descriptor for `path`, or Rejected if it is not a regular file.

    O_NONBLOCK makes opening a FIFO return at once instead of waiting for a
    writer, and fstat then refuses it. Never hands back a descriptor for a
    FIFO, socket or device.
    """
    try:
        fd = os.open(path, flags | _NONBLOCK, 0o666)
    except (OSError, ValueError) as e:      # ValueError: embedded NUL byte
        raise Rejected("cannot open %s: %s" % (_shown(path), _why(e))) from None
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise Rejected("%s is not a regular file" % _shown(path))
    return fd


def _shown(path: str) -> str:
    return json.dumps(path[:200])


def _why(e: BaseException) -> str:
    return getattr(e, "strerror", None) or type(e).__name__


def read_bytes(path: str) -> bytes:
    """At most MAX_FILE_BYTES of a regular file. Rejected if it is bigger or not regular."""
    fd = _open_regular(path, os.O_RDONLY)
    with os.fdopen(fd, "rb") as f:
        data = f.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise Rejected("%s is larger than %d bytes" % (_shown(path), MAX_FILE_BYTES))
    return data


def read_text(path: str) -> str:
    return read_bytes(path).decode("utf-8", errors="strict")


def read_json(path: str) -> Any:
    """A JSON file, bounded. Rejected for a non-regular file, an oversize file or bad JSON."""
    try:
        return parse_json(read_text(path))
    except UnicodeDecodeError:
        raise Rejected("%s is not valid UTF-8" % _shown(path)) from None
    except json.JSONDecodeError as e:
        raise Rejected("%s is not valid JSON: %s" % (_shown(path), e)) from None


def append_line(path: str, line: str) -> None:
    """Append one line and force it to disk. Never rewrites an earlier line."""
    fd = _open_regular(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT)
    with os.fdopen(fd, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


def atomic_write_json(path: str, data: Any) -> None:
    """Write JSON to `path` through an unpredictable, exclusively created temp file.

    The temp name carries 64 random bits and is opened O_EXCL, so nobody can plant
    a symlink there in advance (a predictable name made the write follow it).
    """
    tmp = "%s.tmp-%s" % (path, os.urandom(8).hex())
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, allow_nan=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ----------------------------------------------------------------- stdin
def read_message(stream: BinaryIO) -> tuple[bytes | None, bool]:
    """(line, too_long). line is None at end of input.

    A message longer than MAX_LINE_BYTES is drained to its newline without being
    held in memory, and reported as too_long so the caller can answer with an error.
    """
    line = stream.readline(MAX_LINE_BYTES + 1)
    if not line:
        return None, False
    if len(line) <= MAX_LINE_BYTES or line.endswith(b"\n"):
        return line, False
    while True:
        chunk = stream.readline(1 << 20)
        if not chunk or chunk.endswith(b"\n"):
            return b"", True
