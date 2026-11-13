#!/usr/bin/env python3
"""Make Canton refuse an over-cap charge, on a real Canton ledger, in one command.

    python3 tools/prove_refusal_on_sandbox.py

Why this exists, and what it replaces.

For 74 days STATUS.md said `TryCharge` had never executed on a real ledger,
and named the blocker as `C8_CLIENT_SECRET`, a DevNet credential asked of the
organisers on 31 August 2026 and never granted. That row named somebody else
as the reason. It was wrong. `daml sandbox` ships with the SDK that is already
installed to build this repository, and it starts a real Canton participant,
sequencer and mediator on this machine. No credential. No Docker. No download.
Nobody's permission.

WHAT THIS PROVES. The fences in KyaMandate.daml are enforced by Canton's
engine during interpretation, not by any Python in this repository. The script
it runs, KyaTest:testRefusalIsOnLedgerAndNothingMoved, charges 40.0 against a
mandate, then attempts 90.0 which would exceed the cap, and then asserts all
of this against the ledger itself:

  * a refusal record exists ON the ledger, naming the rule
    "charge would exceed the cap", the amount 90.0 and the payee;
  * the mandate survived with spent == 40.0, so the refusal moved nothing;
  * no payment record was created by the refusal.

WHAT THIS DOES NOT PROVE, and the sentence must travel with every use of it.
This is a single-participant local Canton. It is not DevNet, not TestNet and
emphatically not MainNet. It says nothing about a shared network, other
validators, other participants' traffic, or Canton Coin, because no Amulet
exists here. The honest write-up is "Canton's engine refused this", never
"this ran on the Canton network".

THE CONTROL IS THE POINT. A run that only ever reports success cannot tell you
whether it ran at all. So this asks the ledger for a script that does not
exist and REQUIRES that to fail before it believes the one that passes. If the
control passes, this tool refuses to report anything, because then a green
result would mean nothing. That is the same argument step-0-refusal makes
about ledgers, applied to this tool.

Stdlib only, per THE-RULES.md. The organisers' toolkit is never touched.
"""
import os
# B404 is suppressed below: driving the daml CLI is this tool's whole job.
import subprocess  # nosec B404
import sys

from canton_sandbox import (MANDATE_CHAIN, QUIET, Sandbox, build_chain,
                            have_daml, say)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAR = os.path.join(ROOT, "step-1-mandate", "test", ".daml", "dist",
                   "kya-mandate-test-0.0.1.dar")
REAL = "KyaTest:testRefusalIsOnLedgerAndNothingMoved"
CONTROL = "KyaTest:thisScriptDoesNotExist"


def run_script(name, port):
    """Exercise one Daml script against the running ledger. Returns the code."""
    # B603 and B607: literal argv, shell=False, every element a string.
    r = subprocess.run(  # nosec B603 B607
        ["daml", "script", QUIET, "--dar", DAR, "--script-name", name,
         "--ledger-host", "localhost", "--ledger-port", str(port)],
        capture_output=True, text=True)
    return r.returncode


def main():
    if not have_daml() or not build_chain(MANDATE_CHAIN):
        return 1
    if not os.path.exists(DAR):
        say("the build reported success but %s is missing" % DAR)
        return 1
    box = Sandbox(DAR)
    try:
        if not box.start():
            return 1
        port = box.ports["ledgerApi"]

        say("\ncontrol: a script that does not exist MUST fail")
        if run_script(CONTROL, port) == 0:
            say("  THE CONTROL PASSED, so this harness cannot see failure.")
            say("  Refusing to report the real result: it would mean nothing.")
            return 1
        say("  it failed, so a pass below is worth something")

        say("\nthe real run: an over-cap charge, on the ledger")
        if run_script(REAL, port) != 0:
            say("  FAILED. Canton did not enforce the cap as the test expects.")
            return 1

        say("  PASS. Canton refused a 90.0 charge against a mandate with 40.0")
        say("        already spent, wrote a refusal record naming the rule")
        say("        'charge would exceed the cap', and left the mandate's")
        say("        spent total at 40.0. The engine enforced it, not Python.")
        say("\n  This is a single-participant local Canton. Not DevNet, not")
        say("  TestNet, not MainNet, and no Canton Coin exists here. Say")
        say("  \"Canton's engine refused this\", never \"this ran on the")
        say("  Canton network\".")
        return 0
    finally:
        box.stop()


if __name__ == "__main__":
    sys.exit(main())
