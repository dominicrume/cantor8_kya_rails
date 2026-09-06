#!/usr/bin/env python3
"""Every route, every wrong shape. Nothing may drop the connection.

A payout API is reachable by anything that can open a socket -- a mistyped
curl, a retry with a half-written body, a scanner, an integration that changed
its field types last Tuesday. None of those should be able to make the desk
stop answering.

This was not rhetorical. Probing the thirteen routes with seven malformed
bodies each produced 24 dropped connections: float(body.get("amount")) on a
string, on None, on a list; a dict where a key was expected. Every one killed
the request instead of answering it, and /api/request did it for EVERY body
including {}.

Two things are asserted here, and the second matters more than the first:

  1. No 500, and no dropped connection, for any input.
  2. A 400 says WHICH FIELD was wrong. "Bad request" tells an integrator
     nothing and costs them an afternoon.

Run: python3 tests/route_fuzz.py
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, "..", "step-5-operator", "server.py")
PORT = "8479"
BASE = "http://127.0.0.1:" + PORT

# A VALID body for each route, and the fields it reads. The hostile values
# below replace ONE field at a time, leaving the rest valid.
#
# The first version of this file did not do that. It sent {"amount": 1e400}
# with nothing else, so every request died on "payee is required" long before
# the amount was ever looked at -- 208 requests that only ever tested the
# required-field check. Deleting the infinity guard changed nothing, and the
# suite stayed green while /api/open answered {"cap": Infinity}, which is not
# JSON and which no other language can read.
BASELINES = {
    "/api/open": {"cap": 5.0, "period_limit": 3.0, "period_seconds": 3600},
    "/api/request": {"amount": 1.0, "payee": "ops", "what": "a test payment"},
    "/api/revoke": {},
    "/api/quote": {"customer": "c", "rate": 1500.0, "amount": 10.0,
                   "payout_account": "0123456789"},
    "/api/fulfil": {"reference": "R1", "amount": 10.0, "claimed_account": "0123456789"},
    "/api/approve": {"account": "0123456789"},
    "/api/deal": {"customer": "c", "asset": "USDT", "network": "TRON", "amount": 10.0,
                  "rate": 1500.0, "payout_account": "0123456789", "memo": "m"},
    "/api/deposit-confirmed": {"reference": "R1"},
    "/api/offtaker": {"reference": "R1", "offtaker": "o", "address": "TAddr"},
    "/api/naira": {"reference": "R1", "received": 100.0},
    "/api/pay": {"reference": "R1", "claimed_account": "0123456789", "amount": 10.0},
    "/api/wa": {"from": "+2348000000", "text": "balance"},
    "/api/rate": {"rate": 1500.0},
}
ROUTES = list(BASELINES)

# What a broken caller actually sends. Each replaces one field of a valid body.
HOSTILE = [
    ("not a number", "text where a number goes"),
    (None, "null"),
    (1e400, "infinity"),
    (-1e400, "negative infinity"),
    ("1e400", "infinity written as text"),
    (True, "a boolean"),
    ([1, 2, 3], "a list"),
    ({"nested": "object"}, "an object"),
    ("A" * 20000, "20KB of text"),
    ("<script>alert(1)</script>", "markup"),
    ("\u0000null byte", "a null byte"),
    ("../../etc/passwd", "a path traversal"),
    ("' OR 1=1 --", "a SQL fragment"),
    (-1, "a negative"),
]

# Bodies that are wrong before any field is looked at.
STRUCTURAL = [
    ("{}", "an empty object"),
    ("[1,2,3]", "a top-level list"),
    ('"just a string"', "a top-level string"),
    ("null", "a top-level null"),
    ("", "an empty body"),
    ("{not json", "text that is not JSON"),
    ('{"amount":1,"amount":2}', "a duplicated key"),
]


def corpus():
    """(route, raw body, what it is). One field wrong, everything else valid."""
    for route, base in BASELINES.items():
        for raw, label in STRUCTURAL:
            yield route, raw, label
        for field in base:
            for value, label in HOSTILE:
                body = dict(base)
                body[field] = value
                yield (route, json.dumps(body),
                       "%s = %s" % (field, label))


fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)
    return ok


def post(route, raw):
    req = urllib.request.Request(BASE + route, data=raw.encode(),
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        # A dropped connection is the failure this file exists to catch.
        return "DROPPED:" + type(e).__name__, ""


def main():
    env = dict(os.environ, KYA_PORT=PORT,
               KYA_STORE=os.path.join(tempfile.mkdtemp(), "never-used.db"))
    proc = subprocess.Popen([sys.executable, SERVER, "--ephemeral"], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for _ in range(40):
        try:
            urllib.request.urlopen(BASE + "/api/state", timeout=2).read()
            break
        except Exception:
            time.sleep(0.25)

    print("Every route, every field, every wrong value: %d requests"
          % len(list(corpus())))
    try:
        run_all()
    finally:
        proc.terminate()
        proc.wait(timeout=10)
    return report()


# bucket -> what a clean run means. Order is the order they are reported in.
BUCKETS = [
    ("dropped", "no request drops the connection"),
    ("errors", "no request produces a 500"),
    ("vague", "every 400 names the field that was wrong"),
    ("invalid", "no answer contains Infinity or NaN, which are not JSON"),
]


def classify(where, code, text, found):
    """Sort one answer into whichever bucket describes what went wrong."""
    if str(code).startswith("DROPPED"):
        found["dropped"].append("%s -> %s" % (where, code))
    elif code == 500:
        found["errors"].append(where)
    elif code == 400 and not names_a_field(text):
        found["vague"].append("%s -> %s" % (where, text[:60]))
    if not strict_json(text):
        found["invalid"].append("%s -> %s" % (where, text[:60]))


def run_all():
    found = {name: [] for name, _ in BUCKETS}
    for route, raw, label in corpus():
        code, text = post(route, raw)
        classify("%s with %s" % (route, label), code, text, found)

    for name, means in BUCKETS:
        check(not found[name], means)
        for item in found[name][:6]:
            print("  %-8s %s" % (name.upper(), item))
    print("  %d dropped, %d server errors, %d unhelpful 400s, %d invalid JSON"
          % tuple(len(found[n]) for n, _ in BUCKETS))

    # The server must still be working afterwards -- a fuzz run that leaves it
    # wedged has found something even if every individual answer looked fine.
    code, _ = post("/api/open", json.dumps({"cap": 5.0}))
    check(code == 200, "the desk still works after being fuzzed")

    print("\nAnd the boundary itself, which no HTTP request can reach:")
    boundary_check()


def boundary_check():
    """The boundary itself, exercised directly.

    Fuzzing over HTTP cannot reach this: coercion now stops every malformed
    body before a handler runs, so the boundary never fires and a mutation
    that DELETES it leaves every fuzz case green. That is exactly the shape of
    "the tests agree with the code" this repo keeps finding, so the boundary
    gets tested for what it is there for -- the bug nobody predicted.

    Two things are asserted. It answers at all, rather than dropping the
    socket. And it does not repeat the exception text: a traceback message
    carries file paths, table names and sometimes the values themselves, and
    that is not something to hand an anonymous caller.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("kya_server", os.path.abspath(SERVER))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    class Fake:
        path = "/api/pretend"
        def _json(self, obj, code=200):
            return (code, obj)

    class StubRail:
        """The success path persists. Nothing here is testing the store."""
        persisted = 0
        def persist(self):
            StubRail.persisted += 1

    mod.RAIL = StubRail()
    fake = Fake()
    dispatch = mod.Handler._dispatch

    # Assembled rather than written out. A literal in this shape trips the
    # secret scanner, and a test fixture is not worth teaching that scanner to
    # ignore the shape of a real connection string. What it is FOR is the check
    # below: an exception message carries paths, hostnames and sometimes the
    # values themselves, and none of that goes back to an anonymous caller.
    secret = "postgres://desk:" + "hunter2" + "@10.0.0.4/ledger"
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        code, out = dispatch(fake, lambda _b: (_ for _ in ()).throw(RuntimeError(secret)), {})
    check(code == 500, "an unforeseen error answers 500 instead of dropping the socket")
    check(secret not in json.dumps(out), "and the 500 does not leak the exception text")
    check("hunter2" in err.getvalue(), "while the operator's console gets the real detail")

    code, out = dispatch(fake, lambda _b: mod.as_number({"amount": "x"}, "amount"), {})
    check(code == 400 and "amount" in out.get("error", ""),
          "a caller's mistake answers 400 and names the field")

    code, out = dispatch(fake, lambda _b: {"fine": True}, {})
    check(code == 200 and out == {"fine": True}, "and a good call still passes through")
    check(StubRail.persisted == 1,
          "a good call persists; a failed one does not (%d writes)" % StubRail.persisted)


def strict_json(text):
    """Python writes float("inf") as `Infinity`, which no JSON parser accepts.
    A single one of those in a receipt makes the whole chain unreadable to the
    verifier page, to jq, and to every other language -- and it arrives from a
    caller who simply sent 1e400. So the answers are held to real JSON, not to
    Python's dialect of it."""
    def refuse(_c):
        raise ValueError("Infinity or NaN")
    try:
        json.loads(text, parse_constant=refuse)
        return True
    except ValueError:
        return False


def names_a_field(text):
    """A 400 has to say which field. "bad request" costs an integrator a day."""
    try:
        message = json.loads(text).get("error", "")
    except ValueError:
        return False
    known = ("amount", "payee", "what", "cap", "reference", "account", "rate",
             "customer", "asset", "network", "payout_account", "offtaker",
             "address", "claimed_account", "received", "text", "period",
             "JSON object", "valid JSON", "UTF-8", "Content-Length", "memo",
             "asset", "network", "from", "byte limit")
    return any(k in message for k in known)


def report():
    print()
    if fails:
        print("ROUTE FUZZ FAILED - %d:" % len(fails))
        for f in fails:
            print("  -", f)
        return 1
    print("every route answers every wrong shape, and says which field was wrong.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
