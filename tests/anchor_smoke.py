#!/usr/bin/env python3
"""The agent must anchor what it actually wrote, or say plainly that it did not.

Publishing needs DevNet and a secret, so CI cannot test that. What CI can test
is everything around it, and that is where the expensive mistakes live: which
seal gets published, how many receipts it claims to cover, and whether a run
that failed to anchor says so or lets you assume it did.

Anchoring the wrong head is worse than not anchoring. It puts a signed
statement on a public ledger pointing at a chain nobody has.

Run: python3 tests/anchor_smoke.py
"""
import importlib.util, io, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "step-2-agent"))
fails = []


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


# Never the repository's own receipts.js: a MOCKED run written over a real
# DevNet chain destroys the evidence, and the anchor published for it.
SCRATCH = os.path.join(tempfile.mkdtemp(), "receipts.js")
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", KYA_RECEIPTS=SCRATCH)


def run(args):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "step-2-agent", "agent.py")] + args,
                       capture_output=True, text=True, cwd=ROOT, env=ENV)
    return r.stdout + r.stderr


print("KYA Rails - does the agent anchor what it wrote?")

# --- the mock rail must not claim an origin it cannot give -------------------
from agent import MockLedger
published, detail = MockLedger().anchor("a" * 64, 6, "MOCKED")
check(published is False, "the MOCKED rail reports that it published nothing")
check("MOCKED" in detail, "and says MOCKED in the reason")

out = run([])
check("ANCHOR: NOT PUBLISHED" in out, "an offline run says NOT PUBLISHED, not nothing")
check("nothing ties them to this desk" in out,
      "and spells out what that costs, rather than leaving a bare warning")

out = run(["--no-anchor"])
check("ANCHOR: skipped" in out, "--no-anchor skips publishing")
check("claims no origin" in out, "and still says the chain claims no origin")

# --- what would be published is the head of what was written ----------------
# A wrong head here is the worst outcome available: a signed statement on a
# public ledger pointing at a chain that does not exist.
import json
recorded = []


class Spy(MockLedger):
    def anchor(self, seal, count, label):
        recorded.append((seal, count, label))
        return False, "spy"


os.environ["KYA_RECEIPTS"] = SCRATCH
import agent
quiet = io.StringIO()
real_stdout, sys.stdout = sys.stdout, quiet
try:
    agent.main.__globals__["build_ledger"] = lambda argv: Spy()
    agent.main([])
finally:
    sys.stdout = real_stdout

src = open(SCRATCH).read()
written = json.loads(src[src.index("["): src.rindex("]") + 1])
seal, count, label = recorded[-1]
check(seal == written[-1]["seal"], "it anchors the LAST receipt's seal, the chain head")
check(seal != written[0]["seal"], "not the first receipt's, which would verify nothing")
check(count == len(written), "and the count matches the receipts actually written")
check(label == Spy.label, "and names the rail that produced them")

print()
if fails:
    print("ANCHOR SMOKE FAILED - %d:" % len(fails))
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("the agent anchors the chain it wrote, or says it did not.")
