#!/usr/bin/env python3
"""Grade ANY implementation of the receipt chain, in any language.

Until now, writing a fourth implementation meant writing a fourth conformance
harness -- impl/go/conformance.go is 115 lines, nearly as much work as the
format itself. That tax is paid before the implementer can find out whether
they got it right, which is exactly the wrong order: the thing that keeps
someone going is a green tick early.

So the harness lives here once, and your implementation only has to speak a
line-based protocol on stdin and stdout. Read a JSON object per line, write a
JSON object per line, in order. Four operations, all of them things SPEC.md
already requires you to have:

  {"op":"canonical","body":{...}}          -> {"out":"<the canonical string>"}
  {"op":"seal","body":{...},"prev":"..."}  -> {"out":"<64 lowercase hex>"}
  {"op":"verify","receipts":[...]}         -> {"out":<0 if the chain holds,
                                                     else the n that failed>}
  {"op":"reject","body":{...}}             -> {"out":"<field>" or {"out":null}}

Anything you do not implement: answer {"skip":true} and it is reported, not
counted as a pass. Anything that goes wrong: {"error":"..."} and we print it.

    python3 tests/conformance_any.py -- python3 impl/pipe/reference.py
    python3 tests/conformance_any.py -- ./target/release/my-rust-thing
    python3 tests/conformance_any.py -- node my.js

Exit 0 if every case passes. See impl/pipe/reference.py for the shape; it is
about forty lines and yours does not have to be Python.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
VECTORS = json.load(open(os.path.join(HERE, "vectors.json")))


def requests_for(case):
    """The one question each vector kind asks. Kept beside the grader so a new
    kind cannot be added to vectors.json without deciding what it asks."""
    if case["kind"] == "canonical":
        return [{"op": "canonical", "body": case["body"]}]
    if case["kind"] == "seal":
        return [{"op": "canonical", "body": case["body"]},
                {"op": "seal", "body": case["body"], "prev": case["prev"]}]
    if case["kind"] == "chain":
        return [{"op": "verify", "receipts": case["receipts"]}]
    if case["kind"] == "reject":
        return [{"op": "reject", "body": case["body"]}]
    raise SystemExit("vectors.json has a kind this grader does not know: %r"
                     % case["kind"])


def expected(case):
    if case["kind"] == "canonical":
        return [case["canonical"]]
    if case["kind"] == "seal":
        return [case["canonical"], case["seal"]]
    if case["kind"] == "chain":
        return [0 if case["verdict"] == "PASS" else case["fail_at"]]
    if case["kind"] == "reject":
        return [case["offending_field"]]
    # Never fall through to a guess: an unknown kind silently graded as some
    # other kind is how a grader passes an implementation it never tested.
    raise SystemExit("vectors.json has a kind this grader does not know: %r"
                     % case["kind"])


def ask(proc, payload):
    proc.stdin.write(json.dumps(payload) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        return {"error": "the implementation stopped answering"}
    try:
        return json.loads(line)
    except ValueError:
        return {"error": "not JSON: %r" % line[:120]}


def grade(proc, case):
    """(verdict, detail) for one vector. verdict is ok, SKIP or FAIL."""
    for want, req in zip(expected(case), requests_for(case)):
        got = ask(proc, req)
        if got.get("skip"):
            return "SKIP", "not implemented"
        if "error" in got:
            return "FAIL", str(got["error"])[:120]
        if got.get("out") != want:
            return "FAIL", "%s: wanted %r, got %r" % (req["op"], want, got.get("out"))
    return "ok", ""


def main():
    if "--" not in sys.argv:
        print(__doc__.strip().splitlines()[0])
        print("\nusage: python3 tests/conformance_any.py -- <command to run>")
        return 2
    command = sys.argv[sys.argv.index("--") + 1:]
    if not command:
        print("no command given after --")
        return 2

    print("KYA Receipt Chain %s - grading: %s"
          % (VECTORS["spec_version"], " ".join(command)))
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, bufsize=1)
    fails, skips = [], []
    try:
        for case in VECTORS["cases"]:
            verdict, detail = grade(proc, case)
            print("  %-4s %-34s %s" % (verdict, case["name"], case["kind"]))
            if detail:
                print("       " + detail)
            if verdict == "FAIL":
                fails.append(case["name"])
            elif verdict == "SKIP":
                skips.append(case["name"])
    finally:
        proc.stdin.close()
        proc.terminate()
    return report(fails, skips, proc)


def report(fails, skips, proc):
    total = len(VECTORS["cases"])
    print()
    if skips:
        print("%d case(s) skipped, so this is NOT conformant yet: %s"
              % (len(skips), ", ".join(skips[:4])))
    if fails:
        print("NOT CONFORMANT - %d of %d failed:" % (len(fails), total))
        for f in fails:
            print("  - " + f)
        err = proc.stderr.read()[:400] if proc.stderr else ""
        if err.strip():
            print("\nits stderr:\n  " + err.strip().replace("\n", "\n  "))
        return 1
    if skips:
        return 1
    print("CONFORMANT: %d/%d cases. Open a pull request -- see CONTRIBUTING.md."
          % (total, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
