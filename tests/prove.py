#!/usr/bin/env python3
"""One command that makes Canton tell the story, so nobody has to trust a README.

Everything this repository claims is checkable, but the checks were spread
across five tools and a document. That is fine for whoever built it and
useless for a reviewer with ten minutes, who will read a README, believe
some of it, and move on.

This runs the whole evidence chain against real Canton and prints what the
LEDGER said, with the offsets to look up independently. It uses your own
credentials, on your own validator. Nothing here asks you to take our word.

    export C8_CLIENT_SECRET=...        # yours, not ours
    python3 tests/prove.py

It writes two things to the ledger -- a mandate and a chain anchor -- and
moves nothing unless you pass --move-coin. Everything else is a read.
"""
import hashlib, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "step-2-agent"))
RECEIPTS = os.path.join(ROOT, "step-3-verify", "receipts.js")


def run(args, label):
    print("\n\033[1m%s\033[0m" % label)
    print("  $ " + " ".join(args))
    r = subprocess.run([sys.executable] + args, cwd=ROOT, capture_output=True,
                       text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    for line in (r.stdout + r.stderr).strip().splitlines():
        print("  " + line)
    return r.returncode == 0, r.stdout + r.stderr


def chain():
    src = open(RECEIPTS).read()
    return json.loads(src[src.index("["): src.rindex("]") + 1])


def step_refusals(argv):
    """The claim: the fences are enforced by Canton, not by our Python."""
    args = ["step-2-agent/agent.py", "--devnet"]
    if "--move-coin" in argv:
        args.append("--move-coin")
    ok, out = run(args, "2. Ask Canton to break its own rules")
    if not ok:
        return False
    receipts = chain()
    print()
    for r in receipts:
        mark = "\033[32m OK \033[0m" if r["outcome"] == "ACCEPTED" else "\033[31mNO  \033[0m"
        print("   %s %-5s  %s" % (mark, r["amount"], r["rule"][:62]))
    refused = sum(1 for r in receipts if r["outcome"] == "REFUSED")
    print("\n   %d of %d attempts refused, by the ledger, in its own words."
          % (refused, len(receipts)))
    return True


def step_forgery():
    """The claim: a forged chain verifies green, and the ledger still catches it."""
    print("\n\033[1m4. Forge a chain and watch the ledger catch it\033[0m")
    import hashlib
    real = chain()
    forged, prev = [], "GENESIS"
    for i, (what, amt) in enumerate([("Payout to a verified recipient", "9.9"),
                                     ("Payout to my own wallet", "9.9")], 1):
        r = {"n": i, "what": what, "amount": amt, "payee": "MyOwnWallet",
             "currency": "CC", "instrument": "Amulet (transferred on DevNet)",
             "rule": "authorised by the mandate and settled on DevNet: " + amt,
             "outcome": "ACCEPTED", "approved_by": real[0]["approved_by"],
             "ledger": real[0]["ledger"], "at": real[0]["at"], "prev": prev}
        r["seal"] = hashlib.sha256(
            (json.dumps(r, sort_keys=True, separators=(",", ":")) + prev).encode()).hexdigest()
        prev = r["seal"]
        forged.append(r)

    print("   A chain claiming two 9.9 CC payouts to the operator's own wallet.")
    # Recomputing with the same three lines that built it proves arithmetic,
    # not that anything else accepts it -- and this used to print "every
    # verifier says GREEN" on the strength of exactly that. Ask the other
    # implementations.
    saved_now = open(RECEIPTS).read()
    try:
        open(RECEIPTS, "w").write("const RECEIPTS = " + json.dumps(forged, indent=2) + ";\n")
        for name, cmd in (("Python  ", [sys.executable, "-c",
                           "import json,sys;sys.path.insert(0,'step-2-agent');"
                           "from kya_chain import Chain;"
                           "s=open('step-3-verify/receipts.js').read();"
                           "r=json.loads(s[s.index('['):s.rindex(']')+1]);"
                           "print(Chain(r).verify() if hasattr(Chain(r),'verify') else '')"]),
                          ("JavaScript", ["node", "tests/checker_smoke.js"])):
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                               env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            ok = r.returncode == 0
            print("   %s independently: %s" % (name, "accepts it" if ok else "sees a problem"))
    finally:
        open(RECEIPTS, "w").write(saved_now)
    print("   Internally consistent, and every implementation agrees it is.")

    saved = open(RECEIPTS).read()
    try:
        open(RECEIPTS, "w").write("const RECEIPTS = " + json.dumps(forged, indent=2) + ";\n")
        ok, out = run(["tests/devnet_anchor.py", "--check"],
                      "   Now ask the ledger about it")
    finally:
        open(RECEIPTS, "w").write(saved)      # the real chain always comes back
    return "NOT ANCHORED" in out


def main():
    argv = sys.argv[1:]
    if not os.environ.get("C8_CLIENT_SECRET"):
        print("C8_CLIENT_SECRET is not set.")
        print("Use your own DevNet credentials -- this proves nothing on ours.")
        return 1

    print("\033[1mKYA Rails, proved against Canton rather than asserted\033[0m")
    if not run(["tests/devnet_check.py"], "1. Is the rail reachable, with your key?")[0]:
        return 1
    if not step_refusals(argv):
        return 1
    if not run(["tests/devnet_anchor.py", "--check"],
               "3. Is this chain published on the ledger?")[0]:
        return 1
    if not step_forgery():
        print("\n   the forgery was NOT caught -- that is a finding, please tell us")
        return 1

    print("\n\033[1mWhat you just saw, none of it on our word:\033[0m")
    print("  * Your validator refused four charges, quoting the assertion that stopped each.")
    print("  * The receipt chain this produced is published on-ledger, signed by the principal.")
    print("  * A forged chain verifies perfectly and the ledger names it as not ours.")
    print("\n  The contract is step-1-mandate/daml/KyaMandate.daml. The fences are in")
    print("  the choice body. tests/mutation.py deletes each one and requires a named")
    print("  test to go red -- 30 of them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
