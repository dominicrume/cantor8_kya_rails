#!/usr/bin/env python3
"""One command: put a refusal on Canton DevNet and bring back its contract id.

Everything about the on-ledger refusal is built, tested and disconnected from
a ledger. `TryCharge` compiles, 100 Daml scripts pass, the Python reads the
rule off the contract -- and no receipt anywhere carries a `ledger_ref`,
because nothing has ever run against DevNet. Until it does, "a refused action
leaves something behind" is a design, not a fact, and SHORTCUTS.md says so.

This is the command that closes it. It needs `C8_CLIENT_SECRET` and the three
other C8_ variables in the shell, and nothing else.

    python3 tools/prove_refusal_on_devnet.py --dry-run   # no network at all
    python3 tools/prove_refusal_on_devnet.py             # the real thing

WHY THERE IS A DRY RUN. The secret is not in this shell and will be present
for a short window when it comes back. A tool first exercised in that window
fails on a typo and burns the window. `--dry-run` drives every step through
the same code with a fake ledger: the same receipt stamping, the same rule
extraction, the same chain verification, the same disclosure, the same output
file. Only the HTTP calls are replaced. What it cannot check is whether Canton
returns transactions shaped the way `_created_event` expects -- that is the
whole point of the real run, and it is stated here rather than left implied.

WHAT THE REAL RUN DOES, in order, stopping at the first thing that is wrong:

  1. refuses to run on a dirty tree, because a receipt produced from
     uncommitted code cannot be reproduced by anyone reading this repository
  2. builds the DAR from the committed source
  3. uploads it, which is when Canton runs the upgrade check against the
     vetted 1.1.0. A NOT_VALID_UPGRADE_PACKAGE here names the type that
     changed and nothing has been written to the ledger
  4. opens a mandate with a small cap
  5. spends inside the cap, so the refusal that follows cannot be dismissed as
     the rail being broken
  6. attempts a charge OVER the cap through TryCharge
  7. requires a ChargeRefused contract id to come back, and the rule on it to
     be the cap rule, read off the contract rather than parsed from an error
  8. stamps that into a receipt with `ledger_ref`, verifies the chain, and
     builds the disclosure a regulator would be handed
  9. anchors the head, so the chain cannot be swapped afterwards
 10. writes docs/devnet-refusal.json and prints the contract id

Nothing here spends real money beyond the DevNet Amulet the demo already
holds, and the refusal path moves none by construction.
"""
import argparse
import json
import os
import subprocess  # nosec B404 - fixed argv, no shell
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "step-2-agent"))
sys.path.insert(0, os.path.join(ROOT, "pkg", "src"))

OUT = os.path.join(ROOT, "docs", "devnet-refusal.json")
CAP = 0.5
UNDER, OVER = 0.1, 5.0          # 5.0 against a cap of 0.5 cannot be a rounding


class Stop(SystemExit):
    """Fail with the thing to go and fix, not a traceback."""


def step(n, what):
    print("\n%d. %s" % (n, what))


def ok(detail):
    print("   ok   %s" % detail)


def clean_tree():
    """A receipt made from uncommitted code is not reproducible by a reader.

    The whole claim is that somebody else can check this. They will clone the
    repository at the commit named in the output file; if the code that
    produced the receipt was never committed, they cannot.
    """
    r = subprocess.run(["git", "status", "--porcelain"],  # nosec B603 B607
                       cwd=ROOT, capture_output=True, text=True)
    dirty = [ln for ln in r.stdout.splitlines()
             if ln.strip() and not ln.startswith("??")]
    if dirty:
        raise Stop(
            "the working tree has uncommitted changes:\n    "
            + "\n    ".join(dirty[:6])
            + "\n\n  Commit them first. A receipt produced from code that is "
              "not in\n  the history cannot be reproduced by whoever you send "
              "it to, which\n  is the only reason any of this is worth doing.")
    head = subprocess.run(["git", "rev-parse", "HEAD"],  # nosec B603 B607
                          cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return head


def fake_ledger():
    """A DevNetLedger whose only network call is replaced.

    Deliberately the real class with the real charge(), so the dry run
    exercises the rule extraction, the ledger_ref capture and the "a failed
    submission claims no reference" branch. Only _submit is fake.
    """
    import devnet_ledger as dn
    led = dn.DevNetLedger.__new__(dn.DevNetLedger)
    led.cid, led.revoked, led.move_coin = "mandate-0", False, False
    led.last_ledger_ref = ""
    state = {"spent": 0.0, "n": 0}

    def created(entity, cid, payload=None):
        return {"CreatedTreeEvent": {"value": {
            "templateId": "deadbeef:KyaMandate:" + entity,
            "contractId": cid, "createArgument": payload or {}}}}

    def submit(commands, **kw):
        state["n"] += 1
        cmd = commands[0]
        nxt = "mandate-%d" % state["n"]

        # open_mandate proposes with a CreateCommand and then exercises Accept.
        # The first dry run assumed every command was an ExerciseCommand and
        # died on a KeyError at step 4, which is exactly the typo this mode
        # exists to find before the secret window opens.
        if "CreateCommand" in cmd:
            return True, {"transaction": {"events": [
                created("KyaMandateProposal", "proposal-%d" % state["n"])]}}

        ex = cmd["ExerciseCommand"]
        if ex.get("choice") != "TryCharge":
            return True, {"transaction": {"events": [created("KyaMandate", nxt)]}}

        arg = ex["choiceArgument"]
        amount = float(arg["amount"])
        if state["spent"] + amount > CAP:
            return True, {"transaction": {"events": [
                created("ChargeRefused", "00dryrun%02d::ChargeRefused" % state["n"],
                        {"rule": "charge would exceed the cap",
                         "amount": arg["amount"], "payee": arg["payee"]}),
                created("KyaMandate", nxt)]}}
        state["spent"] += amount
        return True, {"transaction": {"events": [
            created("ChargeRecord", "record-%d" % state["n"]),
            created("KyaMandate", nxt)]}}

    dn._submit = submit
    return led


def deploy(dry):
    """Steps 1 to 3: committed, built, and accepted by Canton as an upgrade.

    Split from run() at the seam that matters: everything here happens before
    a single contract exists, and every failure in it leaves the ledger
    untouched. Past this point things are on a ledger and cannot be undone.
    """
    step(1, "the working tree is committed, so this is reproducible")
    head = "DRY-RUN-NOT-A-COMMIT" if dry else clean_tree()
    ok("HEAD %s" % head[:12])

    step(2, "the DAR is built from that committed source")
    if dry:
        ok("skipped: --dry-run touches nothing outside this process")
        step(3, "Canton checks it is a valid upgrade of the vetted 1.1.0")
        ok("skipped: this is the step that needs the network")
        return head

    b = subprocess.run(  # nosec B603 B607
        ["daml", "build", "--no-legacy-assistant-warning"],
        cwd=os.path.join(ROOT, "step-1-mandate"), capture_output=True, text=True)
    if b.returncode != 0:
        raise Stop("the mandate package does not compile:\n"
                   + (b.stdout + b.stderr)[-800:])
    ok("built")

    step(3, "Canton checks it is a valid upgrade of the vetted 1.1.0")
    u = subprocess.run(  # nosec B603 B607
        [sys.executable, "tests/devnet_upload.py"],
        cwd=ROOT, capture_output=True, text=True)
    print("".join("   | " + ln + "\n" for ln in
                  (u.stdout + u.stderr).strip().splitlines()[-12:]))
    if u.returncode != 0:
        raise Stop(
            "Canton refused the upload. If it says NOT_VALID_UPGRADE_PACKAGE it\n"
            "  names the data type that changed, and NOTHING has been written to\n"
            "  the ledger. See docs/upgrade-path.md.")
    ok("vetted")
    return head


def refuse_on_ledger(led):
    """Steps 5 to 6: spend inside the cap, then over it. Returns (rule, ref).

    Every check in here is a reason to stop rather than a reason to continue,
    because each one turns a different failure into the same headline. A rail
    that is broken, a mandate that never committed, and a rule that drifted all
    produce "REFUSED" and only one of them is the thing being demonstrated.
    """
    step(5, "a charge INSIDE the cap, so the refusal cannot be blamed on the rail")
    outcome, rule = led.charge(UNDER, "customer")
    if outcome != "ACCEPTED":
        raise Stop("a charge inside the cap was refused (%s: %s).\n"
                   "  Fix the rail before reading anything into a refusal."
                   % (outcome, rule))
    ok("%.1f CC accepted" % UNDER)

    step(6, "a charge OVER the cap, through TryCharge")
    outcome, rule = led.charge(OVER, "customer")
    if outcome != "REFUSED":
        raise Stop("%.1f CC against a cap of %.1f was ACCEPTED. Stop and read "
                   "the Daml." % (OVER, CAP))
    ref = led.last_ledger_ref
    if not ref:
        raise Stop(
            "refused, but with NO ledger reference.\n\n"
            "  That means the transaction did not commit -- an auth problem, a\n"
            "  revoked mandate, a dropped connection -- and this is the case the\n"
            "  whole exercise is about. A refusal nothing recorded is exactly\n"
            "  what we had before. Rule reported: %s" % rule)
    if rule != "charge would exceed the cap":
        raise Stop("the ledger recorded the wrong rule: %r.\n"
                   "  Charge and refusalReason have drifted; see "
                   "tests/fence_parity.py." % rule)
    ok("refused on-ledger, rule read off the contract")
    ok("ChargeRefused %s" % ref)
    return rule, ref


def record(led, rule, ref):
    """Steps 7 and 8: the receipt, and the disclosure built from it.

    Three ways the contract id can be lost between the ledger and the person
    who needs it, each checked: the chain not verifying, the id not reaching
    the receipt, and the id not surviving into the disclosure. The last is the
    one that would be silent, because a disclosure with a missing field still
    verifies perfectly.
    """
    from knowyouragenticai_receipts import disclose
    from kya_chain import Chain

    step(7, "the refusal becomes a receipt that names the contract")
    chain = Chain()
    chain.stamp("payout inside the cap", UNDER, "VerifiedRecipient",
                "inside the cap", "ACCEPTED", "the mandate", led.label,
                led.currency, str(led.instrument))
    chain.stamp("ATTACK: payout over the cap", OVER, "VerifiedRecipient",
                rule, "REFUSED", "the mandate", led.label,
                led.currency, str(led.instrument), ref)
    good, bad = chain.verify()
    if not good:
        raise Stop("the chain does not verify at receipt %s" % bad)
    if "ledger_ref" not in chain.receipts[1]:
        raise Stop("the receipt lost the contract id between charge() and stamp()")
    ok("%d receipts, chain verifies" % len(chain.receipts))

    step(8, "and the disclosure a regulator would be handed")
    doc = disclose(chain.receipts)
    shown = [e for e in doc["entries"] if "body" in e]
    if not any(e["body"].get("ledger_ref") == ref for e in shown):
        raise Stop("the contract id did not survive into the disclosure")
    ok("%d entries, %d shown, the refusal carrying its contract id"
       % (doc["count"], doc["shown"]))
    return chain, doc


def run(dry):
    head = deploy(dry)

    step(4, "a mandate, with a small cap")
    if dry:
        led = fake_ledger()
    else:
        import devnet_ledger as dn
        led = dn.DevNetLedger()
    led.open_mandate(cap=CAP)
    ok("cap %.1f CC" % CAP)

    rule, ref = refuse_on_ledger(led)

    chain, doc = record(led, rule, ref)

    step(9, "the head is anchored, so the chain cannot be swapped afterwards")
    if dry:
        ok("skipped: needs the network")
        anchor = None
    else:
        anchor = led.anchor(chain.receipts[-1]["seal"], len(chain.receipts),
                            led.label)
        ok("ChainAnchor %s" % anchor)

    write_result(dry, head, led, rule, ref, anchor, chain, doc)
    return 0


def write_result(dry, head, led, rule, ref, anchor, chain, doc):
    """Step 10, and the closing words. Separated so run() reads as the story:
    deploy, mandate, refuse, record, disclose, anchor, write."""
    step(10, "written down")
    result = {
        "produced_by": "tools/prove_refusal_on_devnet.py",
        "dry_run": dry,
        "commit": head,
        "ledger": led.label,
        "cap": "%.1f" % CAP,
        "refused": {"amount": "%.1f" % OVER, "rule": rule, "contract": ref},
        "anchor": anchor,
        "chain": chain.receipts,
        "disclosure": doc,
    }
    if dry:
        print("   ok   not written: --dry-run never touches %s"
              % os.path.relpath(OUT, ROOT))
    else:
        with open(OUT, "w") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
        ok("%s" % os.path.relpath(OUT, ROOT))

    print()
    print("=" * 68)
    if dry:
        print("DRY RUN. Every step above ran through the real code with a fake")
        print("ledger. What it did NOT check: whether Canton returns")
        print("transactions shaped the way _created_event expects. Only the")
        print("real run answers that.")
    else:
        print("A refused action left something behind on Canton.")
        print()
        print("  contract : %s" % ref)
        print("  rule     : %s" % rule)
        print("  commit   : %s" % head)
        print()
        print("Add the contract id to SHORTCUTS.md, which currently records")
        print("that this had never been run.")
    print("=" * 68)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="drive every step with a fake ledger; no network")
    args = ap.parse_args()
    if not args.dry_run and not os.environ.get("C8_CLIENT_SECRET"):
        print("C8_CLIENT_SECRET is not set, so there is no DevNet to talk to.")
        print()
        print("  Put it in the shell, never in a file:")
        print("      export C8_CLIENT_SECRET=...")
        print()
        print("  Or see what this would do without it:")
        print("      python3 tools/prove_refusal_on_devnet.py --dry-run")
        return 1
    try:
        return run(args.dry_run)
    except Stop as e:
        print("\nSTOPPED: %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
