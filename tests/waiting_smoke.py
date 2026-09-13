#!/usr/bin/env python3
"""Who is owed a reply, decided offline, from a recorded forum shape.

tools/waiting.py watched GitHub for its first week and reported "nothing yet"
truthfully for two days while two people waited on the Canton forum. Every
reply this project has ever received came from that forum; none came from a
GitHub issue.

The rule it now applies is one line: **the last post is theirs, so we owe a
reply.** That is the whole thing, and it is worth a test because it has two
failure modes that both look like success.

  * counting posts instead of looking at the last one. A thread where we
    posted last has plenty of replies in it and owes nothing.
  * treating our own post as somebody answering, which makes every thread we
    have ever spoken in look like an obligation, and teaches you to ignore it.

The live call needs the network and is not in the float. This drives the same
decision over recorded Discourse JSON, which is what the endpoint returns.

Run: python3 tests/waiting_smoke.py
"""
import importlib.util
import io
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

spec = importlib.util.spec_from_file_location(
    "waiting", os.path.join(ROOT, "tools", "waiting.py"))
waiting = importlib.util.module_from_spec(spec)
spec.loader.exec_module(waiting)

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def thread(*authors):
    """A Discourse topic whose posts are by these usernames, in order."""
    return {"post_stream": {"posts": [
        {"username": u, "created_at": "2026-09-1%dT09:00:00Z" % (i + 1),
         "cooked": "<p>post %d by %s</p>" % (i + 1, u)}
        for i, u in enumerate(authors)]}}


def owed_for(*authors):
    """Run topic() against a recorded thread; return (owed, printed text)."""
    payload = json.dumps(thread(*authors)).encode()

    class Fake(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    real = urllib.request.urlopen
    urllib.request.urlopen = lambda *a, **k: Fake(payload)
    out, real_stdout = io.StringIO(), sys.stdout
    sys.stdout = out
    try:
        n = waiting.topic(1, "a recorded thread")
    finally:
        sys.stdout = real_stdout
        urllib.request.urlopen = real
    return n, out.getvalue()


US = waiting.US

print("the last post decides, not the post count")
n, text = owed_for(US, "Mr_Tuddles")
check(n == 1, "they spoke last, so we owe a reply")
check("THE LAST WORD IS THEIRS" in text, "  and it says so, unmissably")
check("Mr_Tuddles" in text, "  naming who is waiting")

n, text = owed_for(US, "Mr_Tuddles", US)
check(n == 0, "we spoke last, so we owe nothing")
check("THE LAST WORD IS THEIRS" not in text,
      "  and it does not nag about a thread we have answered")

# The failure that would make the tool useless in the other direction.
n, text = owed_for(US, US, US)
check(n == 0, "a thread only we have posted in owes nothing")
check("0 from other people" in text or "0 post" in text or "3 post(s), 0 from" in text,
      "  and it says nobody else has spoken")

print()
print("and it survives a thread it cannot read")
# Offline is an answer. A tool that raises here is a tool nobody runs.
real = urllib.request.urlopen


def boom(*a, **k):
    raise OSError("network is down")


urllib.request.urlopen = boom
out, real_stdout = io.StringIO(), sys.stdout
sys.stdout = out
try:
    n = waiting.topic(9059, "unreachable")
finally:
    sys.stdout = real_stdout
    urllib.request.urlopen = real
check(n == 0, "an unreachable forum owes nothing rather than raising")
check("could not be read" in out.getvalue(), "  and says it could not be read")

print()
print("the topics it watches are the ones with people in them")
check(len(waiting.TOPICS) >= 2, "at least two forum topics are watched (%d)"
      % len(waiting.TOPICS))
numbers = [n for n, _ in waiting.TOPICS]
check(9059 in numbers, "  including 9059, where the stablecoin issuer replied")
check(9114 in numbers, "  and 9114, our own topic, where the design review came")

print()
print("and main() actually asks about every one of them")
# Testing topic() proves the decision is right. It does not prove anything
# calls it: deleting the line in main() that walks TOPICS left this suite green
# and the mutation harness reported BLIND, which is the same shape as the
# original bug -- a correct component nobody reaches.
asked = []
real_topic, real_show = waiting.topic, waiting.show
waiting.topic = lambda n, w: asked.append(n) or 0
waiting.show = lambda *a: 0
out, real_stdout = io.StringIO(), sys.stdout
sys.stdout = out
try:
    waiting.main()
finally:
    sys.stdout = real_stdout
    waiting.topic, waiting.show = real_topic, real_show
check(sorted(asked) == sorted(n for n, _ in waiting.TOPICS),
      "main() asks about every watched topic (%s)" % (asked or "none"))

print()
if fails:
    print("FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("a thread where somebody else spoke last is a thread we owe, and the")
print("tool says which and who.")
