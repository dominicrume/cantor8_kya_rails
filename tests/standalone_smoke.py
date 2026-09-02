#!/usr/bin/env python3
"""The single file you hand a judge must open, and must be the current run.

step-3-verify/build-standalone.py folds receipts.js into verifier.html so the
result opens by double-click with no server and no network. It had no test,
which is a strange place to have none: it is the only artefact that leaves
this repository and gets opened by someone who will not run anything else.

Two ways it can be quietly wrong, and both have happened to the files here:
it can go STALE -- still showing 2.0 and 1.5 CC after the demo moved to 0.2
and 0.1 -- or it can still reference receipts.js externally, in which case it
shows nothing at all over file://.

Run: python3 tests/standalone_smoke.py
"""
import hashlib, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY = os.path.join(ROOT, "step-3-verify")
BUILD = os.path.join(VERIFY, "build-standalone.py")
OUT = os.path.join(VERIFY, "kya-rails-standalone.html")
SRC = os.path.join(VERIFY, "receipts.js")
fails = []


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


def receipts_from(text):
    """The RECEIPTS array, found by its declaration rather than by the first
    bracket in the file. An HTML page is full of brackets; anchoring on
    text.index("[") works on receipts.js and silently grabs a stylesheet on
    the built page."""
    start = text.index("const RECEIPTS")
    start = text.index("[", start)
    depth, i = 0, start
    while i < len(text):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
        i += 1
    raise ValueError("RECEIPTS array is not closed")


print("KYA Rails - the file you hand a judge")

r = subprocess.run([sys.executable, BUILD], capture_output=True, text=True, cwd=ROOT,
                   env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
check(r.returncode == 0, "the builder runs")
page = open(OUT).read()

# -- it must not need anything else -----------------------------------------
check('src="receipts.js"' not in page and "src='receipts.js'" not in page,
      "nothing is loaded from receipts.js -- it opens over file://")
check(not re.search(r'<script[^>]+src=[\'"]https?://', page),
      "no script is fetched from the network")
check(not re.search(r'<link[^>]+href=[\'"]https?://', page),
      "no stylesheet is fetched from the network")

# -- it must be the CURRENT run, not a stale snapshot -----------------------
live = receipts_from(open(SRC).read())
built = receipts_from(page)
check(len(built) == len(live), "it carries the same number of receipts as the live chain")
check([b["seal"] for b in built] == [l["seal"] for l in live],
      "and every seal matches -- it is this run, not a snapshot of an old one")
check(built[0]["ledger"] == live[0]["ledger"],
      "and names the same ledger the live chain names")

# -- the seals in it must actually verify -----------------------------------
prev, bad = "GENESIS", 0
for x in built:
    body = {k: v for k, v in x.items() if k != "seal"}
    canon = json.dumps(body, sort_keys=True, separators=(",", ":"))
    if hashlib.sha256((canon + prev).encode()).hexdigest() != x["seal"] or x["prev"] != prev:
        bad += 1
    prev = x["seal"]
check(bad == 0, "the chain inside it verifies end to end")

# -- the controls the demo depends on ---------------------------------------
for control in ("verifyBtn", "tamperBtn", "playBtn"):
    check(control in page, "the %s control survived the fold" % control)

print()
if fails:
    print("STANDALONE SMOKE FAILED - %d:" % len(fails))
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("the handed-out file is self-contained and is the current run.")
