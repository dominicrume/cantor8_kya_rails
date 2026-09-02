#!/usr/bin/env python3
"""Is the DevNet rail actually usable right now? Answer in a few seconds.

Written because the alternative is starting the whole desk and reading a
failure three layers down. On 29 August a stale secret surfaced as "cannot
find the instrument admin; no holdings visible", which sends you to look at
your wallet when the problem is your token.

Each step below fails with the thing to go and fix, and stops rather than
cascading -- a token failure makes every later check fail for the same reason,
and five red lines about one problem is four lines of noise.

    export C8_CLIENT_SECRET=...        # the real value, shell only
    python3 tests/devnet_check.py

Nothing here writes to the ledger. It is safe to run any time, and it is NOT
part of CI: CI has no secret and should not have one.
"""
import os, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "step-2-agent"))


def line(ok, what, detail=""):
    print("  %s %s%s" % ("OK  " if ok else "FAIL", what,
                         ("\n       " + detail) if detail else ""))
    return ok


def fail(what, detail):
    line(False, what, detail)
    return 1


def check_secret():
    secret = os.environ.get("C8_CLIENT_SECRET", "")
    if not secret:
        return None, ("C8_CLIENT_SECRET is not set.\n       "
                      "export it in this shell -- never in a file, never committed.")
    if secret.strip(".") == "" or len(secret) < 12:
        return None, ("it is %r, which is the placeholder from the docs.\n       "
                      "Paste the real value from the organisers." % secret[:12])
    return secret, None


def main():
    print("KYA Rails - DevNet preflight")
    secret, why = check_secret()
    if why:
        return fail("a usable C8_CLIENT_SECRET is present", why)
    line(True, "a usable C8_CLIENT_SECRET is present",
         "%d characters, not a placeholder" % len(secret))

    import devnet_ledger as dn                    # sets the C8_* defaults
    import c8lab

    started = time.time()
    try:
        c8lab.token(sub=dn.USER)
    except Exception as e:
        return fail("the identity provider issues a token",
                    "%s\n       Usually a wrong or expired secret. Check it "
                    "first; the network answered." % str(e)[:200])
    line(True, "the identity provider issues a token",
         "%s in %.1fs" % (os.environ["C8_IDP"], time.time() - started))

    try:
        offset = c8lab.ledger_end(sub=dn.USER)
    except Exception as e:
        return fail("the ledger answers",
                    "%s\n       The token worked, so this is the validator, "
                    "not your secret." % str(e)[:200])
    line(True, "the ledger answers", "ledger end at offset %s" % offset)

    return check_wallet(dn)


def check_wallet(dn):
    """Does the agent hold anything, and can we name the instrument admin?"""
    admin = None
    try:
        admin = dn.discover_admin()
    except Exception as e:
        return fail("a holding is visible", str(e)[:200])
    if not admin:
        return fail("a holding is visible",
                    "no holding came back. This is usually the secret rather "
                    "than an empty wallet -- but the token worked above, so "
                    "check that kya-agent-1 still holds Amulet.")
    line(True, "a holding is visible", "instrument admin %s" % admin[:40])
    return check_balance(dn)


# agent.py makes two charges the mandate allows: 2.0 then 1.5. With
# --move-coin each one is a real transfer, so the agent has to hold this much
# or the second settles short -- and a payout that is authorised but does not
# settle is the worst outcome in the whole system.
NEEDED = 3.5


def check_balance(dn):
    """Enough coin to actually settle, or only enough to record?"""
    held = dn._spendable(dn.PARTY["agent"])
    where = dn.PARTY["agent"].split("::")[0]
    line(True, "the agent's spendable balance", "%s holds %.4f CC" % (where, held))

    print()
    if held >= NEEDED:
        print("  DevNet is usable, and there is enough to move coin:")
        print("    python3 step-2-agent/agent.py --devnet")
        print("    python3 step-2-agent/agent.py --devnet --move-coin")
        return 0
    print("  DevNet is usable, but --move-coin needs %.1f CC and %s has %.4f."
          % (NEEDED, where, held))
    print("  A previous --move-coin run already sent this coin on to the")
    print("  recipient and partner parties; it was not lost, it moved.")
    print("  Run without --move-coin -- the fences are what the judges ask")
    print("  about, and they are proved either way:")
    print("    python3 step-2-agent/agent.py --devnet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
