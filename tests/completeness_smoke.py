#!/usr/bin/env python3
"""SPEC 6c. The hole 6b could not close: how do I know this is all of them?

6b proved you cannot remove a refusal from a disclosure. It did not prove you
cannot hide one. A withheld entry still declares its outcome, but the body is
gone, so nothing contradicts the declaration. `disclosing` catches a withheld
entry that ADMITS it was refused. It never catches one relabelled accepted.

That is the only question an auditor asks about a population of exceptions.
An auditor does not want the exceptions, it wants to know the exceptions are
all of them. A hash chain answers sequence integrity, not completeness,
because the seal of a withheld entry covers a body the reader never sees.

So the outcomes get their own digest, with the same shape as a seal:
sha256(canonical(step) + previous), over every entry's position and outcome.

What that is worth is stated here as plainly as in the code, because this is
the easiest thing in the project to overclaim:

  * ALONE IT PROVES NOTHING. The producer writes the disclosure and could
    recompute the digest over the same lie.
  * Its value is that it makes completeness ANCHORABLE. One value, pinned to
    an origin the producer does not control, now covers the outcome of every
    entry as well as the integrity of the chain.
  * It cannot prove an attempt was recorded at all. Nothing can.

Everything below attacks that. The one that matters is test 2.

Run: python3 tests/completeness_smoke.py
"""
import copy
import json
import os
import subprocess  # nosec B404 - fixed argv, no shell
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "pkg", "src"))

from knowyouragenticai_receipts import (  # noqa: E402
    Chain, GENESIS, check_disclosure, disclose, outcome_digest)

fails = []


def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what)
    if not ok:
        fails.append(what)


def a_chain():
    c = Chain()
    c.allowed("a small one", "10.00", "USD", "acme", "within the cap")
    c.refused("over the cap", "999.00", "USD", "acme",
              "would exceed the cap: 10.00 + 999.00 > 100.00 USD")
    c.refused("not on the list", "5.00", "USD", "stranger",
              "payee is not on the allow-list")
    c.allowed("another", "20.00", "USD", "acme", "within the cap")
    return c.receipts


print("the digest is a function of the outcomes and nothing else")
check(outcome_digest([]) == GENESIS,
      "an empty chain digests to GENESIS, like an empty chain's prev")
one = [{"n": 1, "outcome": "ACCEPTED"}]
check(outcome_digest(one) == outcome_digest(one), "it is deterministic")
check(outcome_digest([{"n": 1, "outcome": "REFUSED"}]) != outcome_digest(one),
      "changing one outcome changes it")
check(outcome_digest([{"n": 1, "outcome": "ACCEPTED"},
                      {"n": 2, "outcome": "REFUSED"}])
      != outcome_digest([{"n": 1, "outcome": "REFUSED"},
                         {"n": 2, "outcome": "ACCEPTED"}]),
      "  and so does reordering them, because position is in the step")

print()
print("a disclosure carries it, and an honest one verifies")
receipts = a_chain()
doc = disclose(receipts)
check(doc.get("spec") == "1.3", "the disclosure declares spec 1.3")
check(isinstance(doc.get("outcomes"), str) and len(doc["outcomes"]) == 64,
      "it carries a 64-character outcomes digest")
ok, why = check_disclosure(doc)
check(ok, "an untouched disclosure verifies: %r" % why)

print()
print("THE ATTACK: withhold a refusal and relabel it accepted")
t = copy.deepcopy(doc)
hidden = None
for e in t["entries"]:
    if e.get("outcome") == "REFUSED":
        hidden = e["n"]
        e.pop("body", None)
        e["withheld"] = True
        e["outcome"] = "ACCEPTED"
        break
t["shown"] = sum(1 for e in t["entries"] if "body" in e)
ok, why = check_disclosure(t)
check(not ok, "refusal %s hidden as an accepted payment is REFUSED: %s"
      % (hidden, why[:72]))
check("outcomes digest" in why,
      "  and the reason names the digest, not something vaguer")

print()
print("the usual tampering still fails, and fails for its own reason")
t = copy.deepcopy(doc)
t["outcomes"] = "0" * 64
check(not check_disclosure(t)[0], "a swapped digest is refused")
t = copy.deepcopy(doc)
t["outcomes"] = 12345
check(not check_disclosure(t)[0], "a digest that is not a string is refused")
t = copy.deepcopy(doc)
t["entries"].pop()
t["count"] = len(t["entries"])
check(not check_disclosure(t)[0], "dropping the last entry is still refused")

print()
print("old disclosures are not broken by a claim they never made")
old = copy.deepcopy(doc)
old.pop("outcomes")
old["spec"] = "1.2"
ok, why = check_disclosure(old)
check(ok, "a pre-6c disclosure with no digest still verifies: %r" % why)
live = os.path.join(ROOT, "docs", "examples", "settlement-refusals.json")
if os.path.exists(live):
    with open(live) as f:
        shipped = json.load(f)
    ok, why = check_disclosure(shipped)
    check(ok, "the example file we hand people still verifies: %r" % why)

print()
print("Python and JavaScript agree, which is the whole point of having two")
NODE = """
%s
async function outcomeDigest(entries){
  let od='GENESIS';
  for(let i=0;i<entries.length;i++){
    const e=entries[i], o=e.outcome;
    od = await sha256(stableStringify({
      n: Number.isInteger(e.n) ? e.n : i+1,
      outcome: (o===null||o===undefined) ? '' : String(o)
    }) + od);
  }
  return od;
}
const cases=JSON.parse(process.argv[2]);
const out=[]; for(const c of cases) out.push(await outcomeDigest(c));
console.log(JSON.stringify(out));
"""


def lifted(names):
    """The real functions out of verifier.html, not a copy of them.

    A parity test written against a transcription proves the transcription
    agrees with Python. It says nothing about the file people actually use.
    """
    src = open(os.path.join(ROOT, "step-3-verify", "verifier.html")).read()
    out = []
    for name in names:
        i = src.index("function %s(" % name)
        if src[max(0, i - 6):i] == "async ":
            i -= 6
        ends = [src.index(m, i + 1) for m in ("\nfunction ", "\nasync function ")
                if m in src[i + 1:]]
        out.append(src[i:min(e for e in ends if e > i)])
    return "\n".join(out)


CASES = [
    [],
    [{"n": 1, "outcome": "ACCEPTED"}],
    [{"n": 1, "outcome": "ACCEPTED"}, {"n": 2, "outcome": "REFUSED"}],
    [{"n": 1, "outcome": "POLICY"}, {"n": 2, "outcome": "REFUSED"},
     {"n": 3, "outcome": "ACCEPTED"}],
    [{"n": 1, "outcome": None}],
    [{"n": 1}],
    [{"outcome": "ACCEPTED"}, {"outcome": "REFUSED"}],
    [{"n": 1, "outcome": "REFUSED é₦"}],
    [{"n": 7, "outcome": "COVERED"}, {"n": 8, "outcome": "ERROR"}],
    [{"n": i, "outcome": "ACCEPTED" if i % 3 else "REFUSED"}
     for i in range(1, 40)],
]
try:
    script = NODE % lifted(("escapeNonAscii", "stableStringify", "sha256"))
    path = os.path.join(HERE, ".parity.mjs")
    with open(path, "w") as f:
        f.write(script)
    try:
        p = subprocess.run(  # nosec B603 B607 - literal argv
            ["node", path, json.dumps(CASES)],
            capture_output=True, text=True, timeout=60)
        if p.returncode:
            check(False, "node could not run the lifted functions: %s"
                  % (p.stderr or "")[-110:])
        else:
            js = json.loads(p.stdout)
            mine = [outcome_digest(c) for c in CASES]
            bad = [i for i, (a, b) in enumerate(zip(mine, js)) if a != b]
            check(not bad, "the two implementations agree on all %d cases%s"
                  % (len(CASES), "" if not bad else ", except %s" % bad))
            check(len(js) == len(CASES), "  and both answered every case")
    finally:
        if os.path.exists(path):
            os.remove(path)
except FileNotFoundError:
    check(False, "node is not installed, so parity was not checked")

print()
if fails:
    print("FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("A refusal can no longer be hidden by relabelling it, and the digest")
print("that proves it reads the same in Python and in the browser.")
print("Anchor it, or it is decoration. outcome_digest() says so too.")
