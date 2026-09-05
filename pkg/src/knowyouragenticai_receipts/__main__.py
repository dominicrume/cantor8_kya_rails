"""Check a receipt chain, or prove this build implements the specification.

    python -m knowyouragenticai_receipts verify receipts.json
    python -m knowyouragenticai_receipts verify -            # read from stdin
    python -m knowyouragenticai_receipts selftest            # against the shipped vectors

`verify` exists because holding a receipts file and having to write code to
check it is a barrier at exactly the wrong moment -- the person checking is
usually not the person who built the thing.

Exit codes: 0 the chain holds, 1 it does not, 2 the input could not be read.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

from . import __version__, canonical, seal, verify, _first_non_ascii

VECTORS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vectors.json")


WRAPPERS = ("receipts", "RECEIPTS", "data", "entries", "chain", "items")


def _parsed_forms(text: str) -> list[Any]:
    """Every way this text might be JSON: the whole thing, and the array inside
    it. The second is what makes `const RECEIPTS = [...]` readable."""
    out, t = [], text.strip()
    bracketed = None
    start, end = t.find("["), t.rfind("]")
    if start >= 0 and end > start:
        bracketed = t[start:end + 1]
    for candidate in (t, bracketed):
        if candidate is None:
            continue
        try:
            out.append(json.loads(candidate))
        except ValueError:
            pass
    return out


def _receipts_from(text: str) -> tuple[bool, list[Any] | None]:
    """(was_json, receipts). Reads a bare array, a `const RECEIPTS = [...]`
    file, or a chain wrapped in an export.

    Returns the two failures separately because they are different things and
    a reader deserves to be told which: "I cannot read this" is not the same
    as "this is readable but is not a receipt chain", and neither is the same
    as "this chain was tampered with".
    """
    candidates = _parsed_forms(text)
    for parsed in candidates:
        if isinstance(parsed, list):
            return True, parsed
        if isinstance(parsed, dict):
            for key in WRAPPERS:
                if isinstance(parsed.get(key), list):
                    return True, parsed[key]
    return bool(candidates), None


def _looks_like_a_chain(receipts: list[Any]) -> bool:
    return any(isinstance(r, dict) and "seal" in r and "prev" in r
               for r in receipts)


def cmd_verify(source: str) -> int:
    try:
        text = sys.stdin.read() if source == "-" else open(source).read()
    except OSError as e:
        print("could not read %s: %s" % (source, e))
        return 2
    where = "-" if source == "-" else source
    was_json, receipts = _receipts_from(text)
    if receipts is None or not _looks_like_a_chain(receipts):
        return _report_not_a_chain(where, was_json)
    ok, bad = verify(receipts)
    return _report_holds(where, receipts) if ok else _report_broken(where, bad)


def _report_not_a_chain(where: str, was_json: bool) -> int:
    """Never "BROKEN". Nothing here was tampered with; it was not a receipt
    chain to begin with, and saying otherwise is an accusation."""
    print("%s: not a receipt chain." % where)
    print("It is %s." % ("valid JSON, just a different kind of file"
                         if was_json else "not JSON this tool can read"))
    print("A receipt chain is a list of entries, each carrying a `seal` and")
    print("a `prev`. Nothing here is wrong -- it is a different thing.")
    return 2


def _report_holds(where: str, receipts: list[Any]) -> int:
    head = receipts[-1].get("seal", "?") if receipts else "(empty)"
    print("%s: %d receipts, every seal holds." % (where, len(receipts)))
    print("head: %s" % head)
    print()
    print("This proves nothing was EDITED. It does not prove where the file")
    print("came from -- a forged chain verifies exactly like this one.")
    return 0


def _report_broken(where: str, bad: int) -> int:
    print("%s: BROKEN at receipt %s." % (where, bad))
    print("Everything before it follows; that one does not, so it or something")
    print("earlier was changed. Every seal after it is unreliable too.")
    print()
    print("What to do: ask whoever gave you this file for the original, and")
    print("check its chain head against wherever they published it.")
    return 1


def _check_case(case: dict) -> tuple[bool, str]:
    kind = case["kind"]
    if kind == "canonical":
        got = canonical(case["body"])
        return got == case["canonical"], "canonical: got %s" % got
    if kind == "seal":
        got = canonical(case["body"])
        if got != case["canonical"]:
            return False, "canonical: got %s" % got
        got = seal(case["body"], case["prev"])
        return got == case["seal"], "seal: got %s" % got
    if kind == "chain":
        _ok, bad = verify(case["receipts"])
        want = 0 if case["verdict"] == "PASS" else case["fail_at"]
        return bad == want, "verify: wanted fail_at=%s, got %s" % (want, bad)
    if kind == "reject":
        field, _ = _first_non_ascii(case["body"])
        return field == case["offending_field"], "reject: named %r" % field
    # An unknown kind is never a pass: it means this build is older than the
    # vectors it is being graded against.
    return False, "unknown vector kind %r -- this package is out of date" % kind


def cmd_selftest() -> int:
    data = json.load(open(VECTORS))
    print("KYA Receipt Chain %s - self-test (package %s)"
          % (data["spec_version"], __version__))
    fails = []
    for case in data["cases"]:
        ok, detail = _check_case(case)
        print("  %s %-34s %s" % ("ok  " if ok else "FAIL", case["name"], case["kind"]))
        if not ok:
            fails.append("%s -- %s" % (case["name"], detail))
    print()
    if fails:
        print("NOT CONFORMANT - %d of %d:" % (len(fails), len(data["cases"])))
        for f in fails:
            print("  - " + f)
        return 1
    print("CONFORMANT: %d/%d cases. This build implements the specification."
          % (len(data["cases"]), len(data["cases"])))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("selftest", "--selftest"):
        return cmd_selftest()
    if args[0] == "verify":
        if len(args) < 2:
            print("usage: python -m knowyouragenticai_receipts verify <file|->")
            return 2
        return cmd_verify(args[1])
    if args[0] in ("-h", "--help", "help"):
        print(__doc__.strip())
        return 0
    if args[0] in ("-V", "--version"):
        print(__version__)
        return 0
    print("unknown command %r. Try --help." % args[0])
    return 2


if __name__ == "__main__":
    sys.exit(main())
