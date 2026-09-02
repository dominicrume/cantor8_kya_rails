#!/usr/bin/env python3
"""Delete each fence in turn and prove a test goes red.

A green suite says the code passes its tests. It does not say the tests would
notice if a fence were removed -- and that is the only property that matters
for a contract whose whole job is refusing things.

This found a real gap: deleting the cap assertion left testOverCapRefused
passing, because `ensure spent <= cap` catches the same condition. The money
was safe; the test was not. Every fence below is now covered by a test that
distinguishes it.

Run: python3 tests/mutation.py        (slow: one daml test run per fence)
"""
import contextlib, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "..", "step-1-mandate")
TESTPKG = os.path.join(PKG, "test")
MANDATE = os.path.join(PKG, "daml", "KyaMandate.daml")
QUOTE = os.path.join(PKG, "daml", "KyaQuote.daml")
CYCLE = os.path.join(PKG, "daml", "KyaCycle.daml")
INBOUND = os.path.join(PKG, "daml", "KyaInbound.daml")

# (source file, fence text, a test that MUST fail when that line is deleted)
FENCES = [
    (MANDATE, "mandate expired",                      "testAfterExpiryRefused"),
    (MANDATE, "amount must be positive",              "testAmountMustBePositive"),
    (MANDATE, "charge would exceed the cap",          "testOverCapRefusedByTheCapAssertion"),
    (MANDATE, "payee is not on the allow-list",       "testPayoutRedirectionRefused"),
    (MANDATE, "charge would exceed the period limit", "testPeriodLimitRefusedWithinWindow"),
    (MANDATE, "new cap below what is already spent",  "testAdjustBelowSpentRefused"),
    # KyaQuote: the fences that stop the loss the desk actually took.
    (QUOTE, "quote expired",                          "testStaleQuoteCannotBeFulfilled"),
    (QUOTE, "deposit does not carry this quote",      "testDepositWithoutTheQuoteReferenceIsRefused"),
    (QUOTE, "amount does not match the quote",        "testAmountMustMatchTheQuote"),
    (QUOTE, "payout account does not match",          "testClaimantCannotRedirectToTheirOwnAccount"),
    (QUOTE, "payout account has not been approved",    "testOperatorCannotQuoteToTheirOwnAccount"),
    # KyaCycle: the two legs where the desk loses its own money.
    (CYCLE, "no approved address for that asset",      "testUnknownNetworkIsRefused"),
    (CYCLE, "requires a memo or tag",                  "testMemoRequiredNetworkRefusesAMissingMemo"),
    (CYCLE, "off-taker wallet is not approved",        "testCryptoCannotGoToAnUnapprovedOffTakerWallet"),
    (CYCLE, "short of the amount agreed",              "testShortNairaIsRefused"),
    # KyaInbound: naira in, crypto out. The more dangerous direction, because
    # a naira transfer can be reversed and a crypto send cannot.
    (INBOUND, "not one of the desk's approved naira accounts", "testOperatorCannotNominateTheirOwnNairaAccount"),
    (INBOUND, "cannot send that asset on that network",        "testCannotQuoteAnAssetTheDeskCannotSend"),
    (INBOUND, "a bank reference is required",                  "testConfirmationNeedsABankReference"),
    (INBOUND, "naira credited is short",                       "testShortNairaCreditIsRefused"),
    (INBOUND, "naira has not been confirmed credited",         "testReleaseWithoutTheBankConfirmationIsRefused"),
    (INBOUND, "receiving wallet does not match",               "testCustomerCannotChangeTheReceivingWalletAtRelease"),
    (INBOUND, "sending on a different network",                "testCannotReleaseOnADifferentNetwork"),
    (INBOUND, "rate is outside the band",                      "testInboundRateMustBeInsideTheBand"),
    (QUOTE,   "rate is outside the band",                      "testOperatorCannotQuoteOutsideTheRateBand"),
    (INBOUND, "no bank feed is configured",                     "testFeedChoiceIsUnusableWithoutAFeed"),
    (CYCLE,   "no deposit feed is configured",                  "testDepositFeedChoiceUnusableWithoutAFeed"),
    (CYCLE,   "a transaction reference is required",            "testDepositFeedNeedsATransactionReference"),
]


def run_suite():
    """Rebuild the mandate, then run the scripts from their own package.

    The test package takes the built DAR as a data-dependency, so a mutated
    mandate only reaches the tests after a rebuild. Skipping the rebuild would
    silently test the previous DAR and report every fence as covered.
    """
    b = subprocess.run(["daml", "build", "--no-legacy-assistant-warning"],
                       cwd=PKG, capture_output=True, text=True)
    if b.returncode != 0:
        return "BUILD FAILED\n" + b.stdout + b.stderr
    p = subprocess.run(["daml", "test", "--no-legacy-assistant-warning"],
                       cwd=TESTPKG, capture_output=True, text=True)
    return p.stdout + p.stderr


def delete_line(path, containing):
    src = open(path).read()
    kept = [l for l in src.splitlines() if containing not in l]
    if len(kept) == len(src.splitlines()):
        return False
    open(path, "w").write("\n".join(kept) + "\n")
    return True


def guard_is_ambiguous(guard):
    """Is this test name defined in more than one module?

    Two modules once shared a test name, so deleting a fence in one module
    left the OTHER module's test green and the harness reported the fence as
    covered. A blind spot in the thing whose only job is finding blind spots.
    """
    found = []
    testdir = os.path.join(TESTPKG, "daml")
    for f in sorted(os.listdir(testdir)):
        if f.endswith(".daml") and guard in open(os.path.join(testdir, f)).read():
            found.append(f)
    return found if len(found) > 1 else []


def check_fence(path, fence, guard):
    """Delete one fence and require its named guard test to go red.

    Returns a list of failures, empty when the fence is properly covered.
    """
    if not delete_line(path, fence):
        print("  SKIP  %-38s (assertion not found)" % fence[:38])
        return ["%s: assertion text not present" % fence]
    out = run_suite()
    if guard + ": ok" in out:
        print("  BLIND %-38s -> %s still passes" % (fence[:38], guard))
        return ["%s is not covered: %s stays green without it" % (fence, guard)]
    if guard not in out:
        # The module stopped compiling, so every test vanished rather than one
        # going red. That reads as "not covered" and is really "not testable".
        print("  ????  %-38s -> %s did not run" % (fence[:38], guard))
        return ["%s: guard test %s did not run" % (fence, guard)]
    print("  ok    %-38s -> %s goes red" % (fence[:38], guard))
    return []


def refuse_if_ambiguous():
    """A guard name defined in two modules can mask a mutation. Stop rather
    than report a fence as covered when it may not be."""
    ambiguous = {g: mods for _, _, g in FENCES
                 for mods in [guard_is_ambiguous(g)] if mods}
    if not ambiguous:
        return
    print("guard test names are ambiguous across modules; a mutation could")
    print("be masked by a same-named test elsewhere:")
    for g, mods in ambiguous.items():
        print("  %s -> %s" % (g, ", ".join(mods)))
    sys.exit(1)


@contextlib.contextmanager
def preserved(paths):
    """Hold the only copies of the contracts while fences are deleted.

    mkstemp, not mktemp: mktemp returns a path and leaves a window in which
    anything can create it first, and losing that race loses the source.
    Restores on the way out however we leave -- including Ctrl-C.
    """
    backups = {}
    for path in paths:
        fd, tmp = tempfile.mkstemp(suffix=".daml")
        os.close(fd)
        shutil.copy(path, tmp)
        backups[path] = tmp
    try:
        yield lambda: [shutil.copy(b, p) for p, b in backups.items()]
    finally:
        for path, tmp in backups.items():
            shutil.copy(tmp, path)
            os.unlink(tmp)
        rebuild_or_destroy()


def rebuild_or_destroy():
    """Restoring the source is not enough: the DAR is the artefact.

    A mutation run leaves .daml/dist holding a package built from source with
    a fence deleted. The source comes back; the artefact does not. Anything
    that then uses that DAR -- a manual upload-dar, a test package resolving
    its data-dependency -- is using a contract with a hole in it, and the
    suite goes red for a reason that is nowhere in the source. This was found
    by running the harness and watching testAfterExpiryRefused fail against
    clean source.

    Rebuild from the restored source. If that fails for any reason, delete the
    DAR outright: no artefact is safe, a stale one is not.
    """
    built = subprocess.run(["daml", "build", "--no-legacy-assistant-warning"],
                           cwd=PKG, capture_output=True, text=True)
    if built.returncode == 0:
        print("  (rebuilt the DAR from restored source)")
        return
    dist = os.path.join(PKG, ".daml", "dist")
    killed = [f for f in os.listdir(dist) if f.endswith(".dar")] if os.path.isdir(dist) else []
    for f in killed:
        os.unlink(os.path.join(dist, f))
    print("  REBUILD FAILED after restore; deleted %d DAR(s) rather than leave a\n"
          "  mutated artefact on disk. Run `daml build` in step-1-mandate." % len(killed))


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    refuse_if_ambiguous()
    failures = []
    with preserved((MANDATE, QUOTE, CYCLE, INBOUND)) as restore:
        baseline = run_suite()
        # Every test module, not just KyaTest: the suite grew to four and the
        # old pattern silently reported a third of the real baseline.
        n = len(re.findall(r"^daml/Kya\w*Test\.daml:.*: ok", baseline, re.M))
        print("baseline: %d scripts green\n" % n)
        for path, fence, guard in FENCES:
            if only and only not in fence:
                continue
            restore()
            failures.extend(check_fence(path, fence, guard))
    report(failures)


def report(failures):
    print()
    if failures:
        print("MUTATION TESTING FAILED - %d fence(s) not covered:" % len(failures))
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("every fence is covered: deleting any one of them turns a test red.")


if __name__ == "__main__":
    main()
