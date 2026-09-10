#!/usr/bin/env python3
"""The seven things that had to be true before 1.1.0 could be published.

Each one was a real gap found by asking what would break in somebody else's
process rather than in ours, and each is asserted here so it cannot quietly
come back.

**Concurrency.** `check` reads the budget and `commit` writes it, with a
receipt sealed in between. Two callers could each be inside the cap on their
own reading and over it together. Eight threads never reproduced it, which is
CPython's GIL being kind rather than a guarantee -- free-threaded builds remove
even the luck.

**Argument shapes.** The guard reads `amount` and `payee` by name through
`inspect`. A tool written as `def run(**kw)` -- which is how most tool-calling
frameworks shape a handler -- had them collected into a nested dict, so the
guard saw a function with no `amount` at all and raised in production code.

**Quadratic stamping.** Every append re-verified the whole chain: 28 seconds
for four thousand receipts, and an agent in a loop reaches four thousand.

**Persistence.** There was no way to write a chain out or read one back that
did not involve shell redirection, and no check on the way in -- so a tampered
file could be loaded and extended, sealing every later receipt onto a lie.

Run: python3 tests/release_readiness.py
"""
import json
import os
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "pkg", "src"))

from knowyouragenticai_receipts import (                     # noqa: E402
    BrokenChain, Chain, Policy, Refused, guard, verify)

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


# --------------------------------------------------------------- concurrency
print("a cap holds when more than one caller is inside it")
worst = 0.0
for _ in range(10):
    p = Policy(cap="100.00", currency="USD", allow=["acme"])
    chain = p.open()
    paid = []
    gate = threading.Barrier(8)

    @guard(p, chain)
    def send(amount, payee):
        paid.append(amount)
        return "ok"

    def worker():
        gate.wait()
        try:
            send("60.00", "acme")
        except Refused:
            pass

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    worst = max(worst, sum(float(a) for a in paid))
check(worst <= 100.0,
      "8 threads x 60.00 against a 100.00 cap, 10 trials: most paid was %.2f" % worst)
check(verify(chain.receipts)[0], "  and the chain still verifies afterwards")
check(hasattr(p, "lock"), "the policy carries the lock that makes it atomic")

# The trial above proves nothing on its own. Under CPython the window between
# reading the budget and spending it is a few bytecodes wide, so a race that is
# certainly THERE reproduces essentially never -- and a test that cannot fail
# is the thing this whole repository exists to refuse. Removing the lock left
# the suite green, which the mutation harness reported as BLIND.
#
# So widen the window instead of hoping for a scheduler. Sealing a receipt is
# what sits between the check and the commit; make that slow and the race is
# not luck, it is arithmetic. With the lock the cap holds anyway.
print()
print("and holds when the window between check and commit is made wide")
slow = Policy(cap="100.00", currency="USD", allow=["acme"])
slow_chain = slow.open()
real_stamp = slow_chain.stamp


def dawdling_stamp(*a, **kw):
    time.sleep(0.02)                    # 20ms, where reality is microseconds
    return real_stamp(*a, **kw)


slow_chain.stamp = dawdling_stamp       # type: ignore[method-assign]
through = []


@guard(slow, slow_chain)
def slow_send(amount, payee):
    through.append(amount)
    return "ok"


gate2 = threading.Barrier(4)


def slow_worker():
    gate2.wait()
    try:
        slow_send("60.00", "acme")
    except Refused:
        pass


ts = [threading.Thread(target=slow_worker) for _ in range(4)]
for t in ts:
    t.start()
for t in ts:
    t.join()
paid_total = sum(float(a) for a in through)
check(paid_total <= 100.0,
      "4 threads x 60.00 with a 20ms seal in the window: paid %.2f, cap 100.00"
      % paid_total)
check(len(through) == 1,
      "  exactly one got through (%d), so the lock is doing the work" % len(through))
check(verify(slow_chain.receipts)[0], "  and the chain is still intact")

# ------------------------------------------------------------- argument shapes
print()
print("the guard finds the amount and the payee however the call is shaped")


def shaped(make, *call):
    p = Policy(cap="100.00", currency="USD", allow=["acme"])
    c = p.open()
    fn = make(p, c)
    fn(*call)
    return c.receipts[-1]


def plain(p, c):
    @guard(p, c)
    def f(amount, payee):
        return "ran"
    return f


def kwonly(p, c):
    @guard(p, c)
    def f(*, amount, payee):
        return "ran"
    return lambda a, b: f(amount=a, payee=b)


def method(p, c):
    class Desk:
        @guard(p, c)
        def pay(self, amount, payee):
            return "ran"
    return Desk().pay


def var_kw(p, c):
    @guard(p, c)
    def f(**kw):
        return "ran"
    return lambda a, b: f(amount=a, payee=b)


def mixed(p, c):
    @guard(p, c)
    def f(amount, **kw):
        return "ran"
    return lambda a, b: f(a, payee=b)


for label, make in [("plain positional", plain), ("keyword-only", kwonly),
                    ("a bound method", method), ("**kwargs only", var_kw),
                    ("named plus **kwargs", mixed)]:
    r = shaped(make, "10.00", "acme")
    check(r["outcome"] == "ACCEPTED" and r["amount"] == "10.00" and r["payee"] == "acme",
          "%s: recorded 10.00 -> acme" % label)

p = Policy(cap="1.00", currency="USD", allow=["acme"])
c = p.open()


@guard(p, c)
def toolcall(**kw):
    raise AssertionError("a refused call must never reach the function")


try:
    toolcall(amount="99.00", payee="acme")
    check(False, "a **kwargs tool is refused when it exceeds the cap")
except Refused as e:
    check("cap" in e.rule, "a **kwargs tool is refused too, not just plain ones")

p2 = Policy(cap="100.00", currency="USD", allow=["acme"])
c2 = p2.open()


@guard(p2, c2)
def wrong_names(total, to):
    return "ran"


try:
    wrong_names("10.00", "acme")
    check(False, "a function without the named arguments is refused")
except TypeError as e:
    check("guarded on" in str(e) and "no such argument" in str(e),
          "a function missing those names fails loudly, naming the argument")

# ------------------------------------------------------------------- async
print()
print("an async agent is recorded when it runs, not when it is called")

import asyncio                                                # noqa: E402

ap = Policy(cap="100.00", currency="USD", allow=["acme"])
ac = ap.open()
async_ran = []


@guard(ap, ac)
async def async_pay(amount, payee):
    async_ran.append(amount)
    return "sent"


# Calling an `async def` does not run it -- it builds a coroutine. The wrapper
# used to stamp ACCEPTED and spend the budget at CALL time, so a caller who
# never awaited left a receipt claiming a payment that never happened. It only
# ever lied in the flattering direction, which is the worst kind.
never_awaited = async_pay("40.00", "acme")
check(len(ac.receipts) == 1,
      "calling without awaiting records nothing (%d receipt, the policy)"
      % len(ac.receipts))
never_awaited.close()

check(asyncio.run(async_pay("40.00", "acme")) == "sent", "awaiting it runs and returns")
check(ac.receipts[-1]["outcome"] == "ACCEPTED", "  and is recorded ACCEPTED")
check(async_ran == ["40.00"], "  and the body ran exactly once")


async def _over_cap():
    try:
        await async_pay("90.00", "acme")
        return ""
    except Refused as e:
        return e.rule


check("cap" in asyncio.run(_over_cap()), "an async call over the cap is refused")
check(async_ran == ["40.00"], "  and the refused body never ran")


async def _swarm():
    p2 = Policy(cap="100.00", currency="USD", allow=["acme"])
    c2 = p2.open()
    got = []

    @guard(p2, c2)
    async def pay(amount, payee):
        await asyncio.sleep(0.01)
        got.append(amount)
        return "ok"

    async def one():
        try:
            await pay("60.00", "acme")
        except Refused:
            pass

    await asyncio.gather(*[one() for _ in range(8)])
    return got, c2


got, c2 = asyncio.run(_swarm())
check(sum(float(a) for a in got) <= 100.0,
      "8 concurrent asyncio tasks x 60.00 stay inside a 100.00 cap (paid %.2f)"
      % sum(float(a) for a in got))
check(verify(c2.receipts)[0], "  and the chain they wrote together verifies")

# ------------------------------------------------------------------ stamping
print()
print("stamping does not get slower as the chain grows")
per = []
for n in (500, 2000):
    ch = Chain(approved_by="x", ledger="y")
    t0 = time.time()
    for _ in range(n):
        ch.allowed(what="p", amount="1.00", currency="USD", payee="a", rule="ok")
    per.append((time.time() - t0) / n)
check(per[1] < per[0] * 3,
      "cost per receipt is flat: %.4f ms at 500, %.4f ms at 2000"
      % (per[0] * 1000, per[1] * 1000))
check(verify(ch.receipts)[0], "  and 2000 receipts still verify in full")

broken = Chain(approved_by="x", ledger="y")
broken.allowed(what="p", amount="1.00", currency="USD", payee="a", rule="ok")
broken.receipts[0]["amount"] = "999.00"
ok, _bad = broken.verify()
check(not ok, "a full verify still catches an entry edited in place")

# --------------------------------------------------------------- persistence
print()
print("a chain can be written out and read back, and a tampered one cannot")
path = os.path.join(tempfile.mkdtemp(), "chain.json")
src = Chain(approved_by="finance", ledger="stripe")
for i in range(5):
    src.allowed(what="payment %d" % i, amount="1.00", currency="USD",
                payee="acme", rule="ok")
src.save(path)
check(os.path.exists(path), "save() writes the file")
back = Chain.load(path)
check(len(back) == 5, "load() reads every receipt back (%d)" % len(back))
back.allowed(what="after reload", amount="1.00", currency="USD",
             payee="acme", rule="ok")
check(back.verify()[0], "  and the chain can be extended after loading")

rs = json.load(open(path))
rs[2]["amount"] = "999.00"
json.dump(rs, open(path, "w"))
try:
    Chain.load(path)
    check(False, "a tampered file is refused on load")
except BrokenChain as e:
    check("does not verify" in str(e),
          "a tampered file is refused on LOAD, not extended silently")

bad_path = os.path.join(tempfile.mkdtemp(), "notachain.json")
json.dump({"hello": "world"}, open(bad_path, "w"))
try:
    Chain.load(bad_path)
    check(False, "a file that is not a chain is refused")
except BrokenChain as e:
    check("list of receipts" in str(e),
          "a file that is not a list of receipts says so plainly")

# -------------------------------------------------------------- what we ship
print()
print("what the package promises about itself")
pkg = os.path.join(ROOT, "pkg", "src", "knowyouragenticai_receipts")
check(os.path.exists(os.path.join(pkg, "py.typed")),
      "py.typed is shipped -- so the types are a promise, checked in CI")
check(os.path.exists(os.path.join(pkg, "CHANGELOG.md")),
      "CHANGELOG.md ships inside the package, readable without the repo")
vectors = json.load(open(os.path.join(pkg, "vectors.json")))
repo_vectors = json.load(open(os.path.join(ROOT, "tests", "vectors.json")))
check(vectors == repo_vectors, "the packaged vectors are the repository's")
check(vectors["spec_version"] == "1.1",
      "the vectors declare spec 1.1 (open outcome vocabulary)")
spec = open(os.path.join(ROOT, "SPEC.md")).read()
check("Version **1.1**" in spec, "SPEC.md says 1.1")
check("alters none" in spec,
      "  and says the change alters no seal, which is why it is not 2.0")

print()
if fails:
    print("FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("the cap holds under concurrency, the guard reads any call shape, stamping")
print("is flat, and a tampered file is refused before it can be extended.")
