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


def _receipts_from(text: str) -> list[Any]:
    """The receipts in a file, whether it is bare JSON or a JS assignment.

    receipts.js in the reference application is `const RECEIPTS = [...];`, and
    telling someone their own file is unreadable when the array is right there
    is not helpful.
    """
    text = text.strip()
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < start:
        raise ValueError("no JSON array found in the input")
    return json.loads(text[start:end + 1])


def cmd_verify(source: str) -> int:
    try:
        text = sys.stdin.read() if source == "-" else open(source).read()
        receipts = _receipts_from(text)
    except OSError as e:
        print("could not read %s: %s" % (source, e))
        return 2
    except ValueError as e:
        print("could not parse %s: %s" % (source, e))
        return 2
    if not isinstance(receipts, list):
        print("that is not a list of receipts")
        return 2

    ok, bad = verify(receipts)
    where = "-" if source == "-" else source
    if ok:
        head = receipts[-1].get("seal", "?") if receipts else "(empty)"
        print("%s: %d receipts, every seal holds." % (where, len(receipts)))
        print("head: %s" % head)
        print()
        print("This proves nothing was EDITED. It does not prove where the file")
        print("came from -- a forged chain verifies exactly like this one.")
        return 0
    print("%s: BROKEN at receipt %s." % (where, bad))
    print("Everything before it follows; that one does not, so it or something")
    print("earlier was changed. Every seal after it is unreliable too.")
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
