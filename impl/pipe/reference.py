#!/usr/bin/env python3
"""The whole receipt chain, in about forty lines, speaking the grading protocol.

This exists to show an implementer how small the job is. Read one JSON object
per line from stdin, write one per line to stdout. That is the entire contract
between your code and tests/conformance_any.py:

    python3 tests/conformance_any.py -- python3 impl/pipe/reference.py

Yours does not have to be Python, and should not be a translation of this --
translate it and you test nothing, because two copies of a mistake agree.
Write it from SPEC.md and let the vectors argue with you. That is how the Go
implementation found the ambiguity in section 4.

Three traps, all of which produce a chain that verifies in your language and
nowhere else:

  * Non-ASCII MUST be escaped to \\uXXXX. Python's json does this by default,
    JavaScript's JSON.stringify does not, Go's escapes < > and & as well.
  * Keys sort by code point at every level, and the separators are exactly
    "," and ":" with no spaces.
  * Amounts are strings in the receipt and must stay strings. A language that
    parses "1.0" into a float and re-serialises it as "1" has changed the seal.
"""
import hashlib, json, sys


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def seal(body, prev):
    return hashlib.sha256((canonical(body) + prev).encode()).hexdigest()


def verify(receipts):
    """0 if the chain holds, otherwise the n of the first receipt that does not."""
    prev = "GENESIS"
    for r in receipts:
        body = {k: v for k, v in r.items() if k != "seal"}
        if r["prev"] != prev or seal(body, prev) != r["seal"]:
            return r["n"]
        prev = r["seal"]
    return 0


def offending_field(body):
    """The first field carrying a character outside ASCII, or None."""
    for key, value in body.items():
        for text in (key, value):
            if isinstance(text, str) and not text.isascii():
                return key
    return None


OPS = {
    "canonical": lambda q: canonical(q["body"]),
    "seal":      lambda q: seal(q["body"], q["prev"]),
    "verify":    lambda q: verify(q["receipts"]),
    "reject":    lambda q: offending_field(q["body"]),
}

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    question = json.loads(line)
    op = OPS.get(question.get("op"))
    answer = {"skip": True} if op is None else {"out": op(question)}
    sys.stdout.write(json.dumps(answer) + "\n")
    sys.stdout.flush()
