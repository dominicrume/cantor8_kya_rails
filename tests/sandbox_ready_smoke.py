#!/usr/bin/env python3
"""The sandbox tools must wait for the DAR, and only for that.

    python3 tests/sandbox_ready_smoke.py

Found 17 November 2026: tools/who_sees_the_attempt_arguments.py passed in a
working tree and failed twice from a fresh clone. Canton writes its port file
before the DAR has been uploaded and vetted, and the tool sent its first command
the moment the file appeared. tools/canton_sandbox.when_packages_ready is the
fix. This tests it without a ledger, with a fake clock so nothing sleeps.

Stdlib only, per THE-RULES.md.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from canton_sandbox import NOT_READY, when_packages_ready  # noqa: E402

fails = []


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


class Fake:
    """An attempt that fails `n` times with `msg`, then succeeds."""
    def __init__(self, n, msg):
        self.n, self.msg, self.calls, self.now, self.slept = n, msg, 0, 0.0, 0

    def attempt(self):
        self.calls += 1
        if self.calls <= self.n:
            raise SystemExit(self.msg)
        return "created"

    def sleep(self, s):
        self.slept += 1
        self.now += s

    def clock(self):
        return self.now


def run(fake, timeout=120):
    return when_packages_ready(fake.attempt, timeout=timeout, pause=2,
                               sleep=fake.sleep, clock=fake.clock)


print("waits while the DAR is not ready, then goes ahead")
for marker in NOT_READY:
    f = Fake(3, "404 on /v2/commands ... ledger said: " + marker)
    check(run(f) == "created" and f.calls == 4 and f.slept == 3,
          "retries %r three times, then succeeds" % marker)

print("")
print("a real error is never hidden behind a wait")
f = Fake(99, "400 Bad Request: CONTRACT_NOT_FOUND")
try:
    run(f)
    check(False, "an unrelated error must propagate")
except SystemExit:
    check(f.calls == 1 and f.slept == 0,
          "an unrelated error fails on the first call, with no waiting")

print("")
print("the wait is bounded")
f = Fake(10 ** 6, "PACKAGE_NAMES_NOT_FOUND")
try:
    run(f, timeout=20)
    check(False, "a DAR that never arrives must fail")
except SystemExit as err:
    check("PACKAGE_NAMES_NOT_FOUND" in str(err.code) and f.now >= 20,
          "gives up after the timeout and shows the ledger's own answer")
    check(f.calls <= 12, "and does not spin: %d calls in 20 seconds" % f.calls)

print("")
print("both tools really use it (a fix nobody calls is not a fix)")
for rel in ("tools/who_sees_the_attempt_arguments.py",
            "tools/can_the_auditor_tell.py"):
    text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
    check("when_packages_ready(" in text and "lambda:" in text.split(
        "when_packages_ready(", 1)[1][:40], "%s wraps its first command" % rel)

print("")
if fails:
    print("FAILED: %d" % len(fails))
    sys.exit(1)
print("the sandbox tools wait for the DAR, only for the DAR, and not for ever.")
