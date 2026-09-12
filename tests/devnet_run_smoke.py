#!/usr/bin/env python3
"""The DevNet run stops on the right thing, and says which thing it was.

`tools/prove_refusal_on_devnet.py --dry-run` drives every step with a ledger
that behaves, so it proves the happy path works. It proves nothing about the
guards, and the guards are most of the value: four different failures all
produce the word REFUSED, and only one of them is the thing being
demonstrated.

  * the rail is broken, so even a charge inside the cap is refused
  * the transaction never committed, so there is no contract to point at
  * the ledger recorded a rule that is not the rule that fired
  * the over-cap charge was ACCEPTED, which is the worst case and reads as
    success if nobody checks

Reported as one headline, those are indistinguishable, and the one that gets
written into a receipt and sent to a stablecoin issuer is whichever happened.
So each is driven here with a ledger that misbehaves in exactly that way, and
the tool has to stop with the right explanation.

The mutation harness pointed this out: deleting the "no contract id" check and
the "wrong rule" check both left the dry run green, because a fake that always
behaves never reaches them.

Run: python3 tests/devnet_run_smoke.py
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "step-2-agent"))
sys.path.insert(0, os.path.join(ROOT, "pkg", "src"))

spec = importlib.util.spec_from_file_location(
    "prove", os.path.join(ROOT, "tools", "prove_refusal_on_devnet.py"))
prove = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prove)

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


class Ledger:
    """A ledger that answers however the test needs it to."""

    label, currency, instrument = "TEST", "CC", "test"

    def __init__(self, answers):
        self.answers = list(answers)
        self.last_ledger_ref = ""

    def charge(self, amount, payee):
        outcome, rule, ref = self.answers.pop(0)
        self.last_ledger_ref = ref
        return outcome, rule


def stops_with(answers, expect):
    """Run the refusal steps against a misbehaving ledger; return the message."""
    try:
        prove.refuse_on_ledger(Ledger(answers))
        return None
    except prove.Stop as e:
        got = str(e)
        return got if expect in got else "WRONG REASON: " + got[:90]


CAP_RULE = "charge would exceed the cap"
GOOD_UNDER = ("ACCEPTED", "inside the cap", "")
GOOD_OVER = ("REFUSED", CAP_RULE, "00abc::ChargeRefused")

print("the run that works, so the failures below mean something")
rule, ref = prove.refuse_on_ledger(Ledger([GOOD_UNDER, GOOD_OVER]))
check(rule == CAP_RULE and ref == "00abc::ChargeRefused",
      "a well-behaved ledger gets through and returns the contract id")

print()
print("and each way it can go wrong stops with its own reason")

why = stops_with([("REFUSED", "mandate expired", ""), GOOD_OVER],
                 "inside the cap was refused")
check(why is not None, "a rail that refuses an in-cap charge stops the run")
check(why and "Fix the rail" in why,
      "  and says to fix the rail, not to read the refusal (%s)"
      % (why or "")[:46])

why = stops_with([GOOD_UNDER, ("REFUSED", CAP_RULE, "")], "NO ledger reference")
check(why is not None,
      "a refusal with no contract id stops the run, rather than being written down")
check(why and "did not commit" in why,
      "  and explains that nothing committed, which is the old behaviour back")

why = stops_with([GOOD_UNDER, ("REFUSED", "a routine limit", "00abc::x")],
                 "wrong rule")
check(why is not None, "a rule the ledger recorded that is not the rule that fired")
check(why and "fence_parity" in why,
      "  and points at the check that would have caught the drift")

# The worst case, and the one that reads as success. 5.0 against a cap of 0.5
# cannot be a rounding: if the ledger accepts it, the fence is gone.
why = stops_with([GOOD_UNDER, ("ACCEPTED", "inside the cap", "")], "ACCEPTED")
check(why is not None, "an over-cap charge that is ACCEPTED stops the run")
check(why and "read the Daml" in why,
      "  and sends the reader to the contract, because the fence is gone")

print()
print("nothing is written when it stops")
# Each Stop above happens before record() and before write_result(), so no
# receipt is stamped and docs/devnet-refusal.json is never touched. A tool that
# writes a partial artefact on the way to failing leaves something that looks
# like evidence.
out = os.path.join(ROOT, "docs", "devnet-refusal.json")
before = os.path.exists(out)
stops_with([GOOD_UNDER, ("REFUSED", CAP_RULE, "")], "NO ledger reference")
check(os.path.exists(out) == before,
      "a stopped run leaves docs/devnet-refusal.json exactly as it was")

print()
if fails:
    print("FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("four failures that all say REFUSED are told apart, and only the one")
print("that is really a refusal on a ledger gets written down.")
