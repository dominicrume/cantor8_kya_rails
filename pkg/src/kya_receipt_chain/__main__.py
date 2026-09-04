"""Self-test: prove this installation matches the specification.

    python -m kya_receipt_chain

The vectors ship inside the package, so this works offline and on a machine
that has never seen the repository. If it ever fails, this build does not
implement the format and nothing it produces should be trusted.
"""
import json, os, sys

from . import canonical, seal, verify, _first_non_ascii

VECTORS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vectors.json")


def check_case(case):
    """(ok, detail) for one vector."""
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
        ok, bad = verify(case["receipts"])
        want = 0 if case["verdict"] == "PASS" else case["fail_at"]
        return bad == want, "verify: wanted fail_at=%s, got %s" % (want, bad)
    if kind == "reject":
        field, _ = _first_non_ascii(case["body"])
        return field == case["offending_field"], "reject: named %r" % field
    # An unknown kind is never a pass: it means this build is older than the
    # vectors it is being graded against.
    return False, "unknown vector kind %r -- this package is out of date" % kind


def main():
    data = json.load(open(VECTORS))
    print("KYA Receipt Chain %s - self-test" % data["spec_version"])
    fails = []
    for case in data["cases"]:
        ok, detail = check_case(case)
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


if __name__ == "__main__":
    sys.exit(main())
