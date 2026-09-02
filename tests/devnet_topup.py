#!/usr/bin/env python3
"""Move Canton Coin back to kya-agent-1 so the demo can be run again.

A --move-coin run really does send Amulet: the coin leaves the agent and
arrives at the recipient and partner parties. It is not spent or lost, it has
moved -- but the agent then has less, and eventually not enough to run the
demo again. This sends it back.

We hold act-as on all five demo parties, which is the only reason this is
possible; it is a demo housekeeping tool, not a feature of the product. On a
real desk you cannot reach into a counterparty's wallet, and nothing here
should be read as suggesting otherwise.

    python3 tests/devnet_topup.py              show balances, move nothing
    python3 tests/devnet_topup.py 0.5          bring the agent up to 0.5 CC

Needs C8_CLIENT_SECRET. Never in CI.
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "step-2-agent"))

DONORS = ("customer", "partner")      # where a --move-coin run sends it
LEAVE = 0.0                           # donors are demo parties; take it all


def balances(dn):
    return {r: dn._spendable(dn.PARTY[r]) for r in
            ("owner", "agent", "customer", "partner", "unverified")}


def show(dn, title):
    print("  %s" % title)
    for role, bal in balances(dn).items():
        print("    kya-%-12s %8.4f CC" % (role + "-1", bal))


def send(dn, c8lab, sender_role, amount):
    """One transfer, accepting the offer if that is how it lands."""
    sender, receiver = dn.PARTY[sender_role], dn.PARTY["agent"]
    ok, r = dn._retry(lambda: c8lab.transfer(sender, receiver, "%.4f" % amount,
                                             sub=dn.USER), tries=4)
    if not ok:
        return False, str(r)[:120]
    if r.get("transferKind") == "offer" and r.get("instructionCid"):
        ok2, r2 = dn._retry(lambda: c8lab.accept_transfer(
            r["instructionCid"], receiver, sub=dn.USER), tries=4)
        if not ok2:
            return False, "offer created but not accepted: " + str(r2)[:90]
    return True, "%.4f CC from kya-%s-1" % (amount, sender_role)


def collect(dn, c8lab, target):
    """Pull from each donor until the agent reaches the target."""
    moved = []
    for role in DONORS:
        short = target - dn._spendable(dn.PARTY["agent"])
        if short <= 1e-9:
            break
        available = max(dn._spendable(dn.PARTY[role]) - LEAVE, 0.0)
        take = min(short, available)
        if take <= 1e-9:
            continue
        ok, detail = send(dn, c8lab, role, take)
        print("    %s %s" % ("moved " if ok else "FAILED", detail))
        moved.append(ok)
    return moved


def main():
    if not os.environ.get("C8_CLIENT_SECRET"):
        print("C8_CLIENT_SECRET is not set. Run tests/devnet_check.py first.")
        return 1
    import devnet_ledger as dn
    import c8lab

    # c8lab.transfer() asks admin_party(), which falls through to dso_party()
    # when ADMIN_PARTY is unset -- and on the shared DevNet validator that scans
    # a party list paginated over thousands of entries, does not find the DSO,
    # and reports "could not find the DSO party", which reads like the network
    # is down. Every Amulet holding names its admin, so ask a holding instead.
    # DevNetLedger does this in __init__; a tool that transfers without going
    # through it has to do the same.
    admin = dn.discover_admin()
    if not admin:
        print("no holding is visible, so the instrument admin is unknown.")
        print("Run tests/devnet_check.py -- this is usually the secret.")
        return 1
    c8lab.ADMIN_PARTY = admin
    os.environ["C8_ADMIN_PARTY"] = admin

    show(dn, "before")
    if len(sys.argv) < 2:
        print("\n  Pass a target, e.g. `python3 tests/devnet_topup.py 0.5`,")
        print("  to bring kya-agent-1 up to that balance.")
        return 0

    target = float(sys.argv[1])
    print("\n  bringing kya-agent-1 up to %.4f CC" % target)
    collect(dn, c8lab, target)
    print()
    show(dn, "after")
    held = dn._spendable(dn.PARTY["agent"])
    print("\n  %s" % ("ready: python3 step-2-agent/agent.py --devnet --move-coin"
                      if held >= 0.3 else
                      "still under the 0.3 CC a --move-coin run sends."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
