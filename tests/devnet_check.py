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

    print()
    print("  DevNet is usable. The rails that need it:")
    print("    python3 step-2-agent/agent.py --devnet")
    print("    python3 step-2-agent/agent.py --devnet --move-coin")
    print("    python3 step-5-operator/server.py --devnet --move-coin")
    return 0


if __name__ == "__main__":
    sys.exit(main())
