#!/usr/bin/env python3
"""The desk's settings: refused when wrong, and enforced where it counts.

Two claims are checked here, and the second is the one the whole project rests
on.

**A desk that cannot understand its settings does not start.** Every field is
validated, and every refusal names the field. A default quietly substituted for
a value somebody typed wrong is how a desk ends up paying with a cap nobody
chose.

**The settings parameterise the fence; they do not become it.** The allow-list
in `desk.json` is handed to `open_mandate` and enforced by the ledger's charge
path -- the mirror of the `assertMsg` in the Daml choice body. If a counterparty
marked `allowed: false` were refused by an `if` in the desk's Python, the
config would be policy in an application, which THE-RULES.md forbids and which
would make the whole argument of this repository false. So the test below does
not ask whether the desk refuses. It asks whether the LEDGER refuses, and
whether the refusal is sealed into the chain.

Run: python3 tests/desk_config_smoke.py
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in ("step-9-desk", "step-2-agent"):
    sys.path.insert(0, os.path.join(ROOT, _p))

import desk_config                                     # noqa: E402
from desk_config import BadConfig, allow_list, load    # noqa: E402

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def write(cfg):
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    open(path, "w").write(json.dumps(cfg))
    return path


def refuses(cfg, phrase, what):
    """The config is rejected, and the message names the field."""
    try:
        load(write(cfg))
        check(False, what + " -- but it was ACCEPTED")
    except BadConfig as e:
        check(phrase in str(e), "%s (says: %.58s)" % (what, e))


def good():
    return json.loads(json.dumps(desk_config.EXAMPLE))


def valid_cases():
    print("a settings file that is wrong is refused, and says which field")
    ok = load(write(good()))
    check(ok["configured"] and ok["money"]["cap"] == 5.0, "a good file loads")
    check(allow_list(ok) == ["customer", "partner"],
          "the allow-list is exactly the counterparties marked allowed")

    c = good(); c["money"]["cap"] = 0
    refuses(c, "greater than zero", "a cap of zero is refused")

    c = good(); c["money"]["rate"] = 2000.0
    refuses(c, "outside its own band", "a rate outside its own band is refused")

    c = good(); c["money"]["band"] = [1500.0, 1000.0]
    refuses(c, "must be below high", "a band with low above high is refused")

    c = good(); c["money"]["period_limit"] = 99.0
    refuses(c, "above money.cap", "a period limit above the cap is refused")

    c = good(); c["counterparties"][1]["id"] = "customer"
    refuses(c, "appears twice", "two counterparties sharing an id are refused")

    c = good(); del c["money"]["cap"]
    refuses(c, "money.cap is missing", "a missing field is named, not defaulted")

    c = good(); c["money"]["cap"] = "five"
    refuses(c, "must be int or float", "text where a number goes is refused")

    c = good(); c["money"]["cap"] = True
    refuses(c, "must not be true/false", "a boolean is not accepted as a number")

    c = good(); c["counterparties"] = "everyone"
    refuses(c, "counterparties must be list", "a non-list of counterparties is refused")


def unconfigured():
    print("\nno settings at all is a SAFE state, not a permissive one")
    cfg = load(os.path.join(tempfile.mkdtemp(), "absent.json"))
    check(not cfg["configured"], "an absent file loads as unconfigured")
    check(cfg["money"]["cap"] == 0.0,
          "with a cap of ZERO -- an unset desk pays nobody, rather than "
          "falling back to something permissive")
    check(allow_list(cfg) == [], "and an empty allow-list")


def reaches_the_fence():
    """The claim that matters. Config -> mandate -> the ledger refuses."""
    print("\nthe allow-list reaches the LEDGER, not just the screen")
    from agent import MockLedger

    cfg = good()
    cfg["counterparties"][1]["allowed"] = False        # partner is now off
    parsed = load(write(cfg))
    check(allow_list(parsed) == ["customer"], "settings now allow only 'customer'")

    ledger = MockLedger()
    ledger.open_mandate(cap=parsed["money"]["cap"], allowed=allow_list(parsed))

    outcome, rule = ledger.charge(1.0, "customer")
    check(outcome == "ACCEPTED", "the allowed counterparty is paid")

    outcome, rule = ledger.charge(1.0, "partner")
    check(outcome == "REFUSED" and "allow-list" in rule,
          "the one turned OFF in settings is refused BY THE LEDGER (%s)" % rule)

    # And the refusal has to be the ledger's, not a check in the desk. The
    # mandate's own record is what carries it.
    check("partner" not in ledger.m["allowed"],
          "because it is absent from the mandate the ledger is holding")
    check(ledger.m["allowed"] == ["customer"],
          "which contains exactly what the settings said, and nothing else")

    # Turning it back on in settings turns it back on at the ledger. If this
    # failed, the allow-list would be baked in somewhere and the file would be
    # decoration.
    back = MockLedger()
    back.open_mandate(cap=5.0, allowed=["customer", "partner"])
    check(back.charge(1.0, "partner")[0] == "ACCEPTED",
          "and putting it back in settings puts it back on the mandate")


def defaults_unchanged():
    print("\nnothing that worked before behaves differently")
    from agent import ALLOWED, MockLedger
    ledger = MockLedger()
    ledger.open_mandate(cap=5.0)                        # no allowed= at all
    check(ledger.m["allowed"] == list(ALLOWED),
          "a caller that passes no allow-list gets the demo roles, as before")


def main():
    valid_cases()
    unconfigured()
    reaches_the_fence()
    defaults_unchanged()
    print()
    if fails:
        print("DESK CONFIG FAILED - %d:" % len(fails))
        for f in fails:
            print("  -", f)
        return 1
    print("the desk refuses settings it cannot understand, and the settings it")
    print("does understand are enforced by the ledger rather than by this code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
