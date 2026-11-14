#!/usr/bin/env python3
"""The package's failure paths: what it does when something is wrong.

    python3 tests/package_failure_paths_smoke.py

WHY THIS FILE EXISTS. tools/mutate_package.py makes one small change at a time
to the published package and counts how many the tests notice. On 14 November
2026 it reported 145 mutants, 126 noticed, 19 survived. The survivors were not
spread at random. Nearly all sat on a failure path: the code that runs when
the input is wrong, which a test written to show the package working never
reaches.

Each test below is aimed at a named survivor, and says which. They are written
against the original and must pass on it. Whether they kill the mutants is
decided by re-running tools/mutate_package.py, not by reading this file.

  __init__.py:272   an unserialisable receipt was returned as VALID (fail open)
  __init__.py:433   the incremental verifier's failure branch, used only on
  __init__.py:435   chains of 64 receipts or more, so no short test reaches it
  __init__.py:449   save() refusing to write a chain that does not verify
  __init__.py:398   a supplied timestamp being kept, and one being filled in
  __init__.py:186   the offending characters named in the error message
  disclose.py:135   a disclosure with no entries
  disclose.py:165   a declared `shown` count that is wrong
  disclose.py:242   an entry whose seal is not a string
  disclose.py:259   an outcomes digest that is not a hash
  disclose.py:273   the one-line summary, and its plural
  policy.py:135,136 who approved it and which ledger, passed through
  policy.py:181,182 a mandate that has expired
  guard.py:92,117   the default instrument and action labels

Stdlib only, per THE-RULES.md.
"""
import calendar
import os
import re
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pkg", "src"))

import knowyouragenticai_receipts as pkg  # noqa: E402
from knowyouragenticai_receipts import (  # noqa: E402
    BrokenChain, Chain, NonAsciiInReceipt, Policy, assert_ascii, verify)
from knowyouragenticai_receipts.disclose import (  # noqa: E402
    check_disclosure, disclose, summary)
from knowyouragenticai_receipts.guard import attempt, guard  # noqa: E402

GENESIS = getattr(pkg, "GENESIS", "GENESIS")
fails = []


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


def honest(n):
    """A chain of n accepted receipts the package wrote itself."""
    c = Chain(approved_by="test", ledger="self-attested")
    for _ in range(n):
        c.allowed("pay", "1.00", "USD", "alice", "under the cap")
    return c


def copy_of(chain):
    return [dict(r) for r in chain.receipts]


def stamp_raises(chain):
    """True if extending this chain refuses with BrokenChain."""
    try:
        chain.stamp("pay", "1.00", "USD", "alice", "under the cap", "ACCEPTED")
    except BrokenChain:
        return True
    return False


def when(text):
    return calendar.timegm(time.strptime(text, "%Y-%m-%dT%H:%M:%SZ"))


def fail_open():
    print("\nverify() must not call unreadable content valid  (__init__:272)")
    ok, _ = verify([{"prev": GENESIS, "seal": "x", "payload": {1, 2}}])
    check(ok is False, "a receipt holding a set, which JSON cannot carry, does "
                       "not verify")
    ok, _ = verify(honest(2).receipts)
    check(ok is True, "control: an honest chain still verifies")


def long_chain_tail():
    print("\nthe incremental verifier, 64 receipts or more  (__init__:433,435)")
    base = honest(70)
    check(not stamp_raises(Chain(copy_of(base))),
          "control: extending an honest 70 receipt chain is allowed")
    body = copy_of(base)
    body[68]["amount"] = "999.00"
    check(stamp_raises(Chain(body)),
          "a tampered BODY in a long chain refuses to be extended")
    link = copy_of(base)
    link[68]["prev"] = "0" * 64
    check(stamp_raises(Chain(link)),
          "a broken LINK in a long chain refuses to be extended")


def save_refuses():
    print("\nsave() must not write a chain that will not verify  (__init__:449)")
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "chain.json")
        tampered = copy_of(honest(3))
        tampered[1]["amount"] = "999.00"
        try:
            Chain(tampered).save(path)
            refused = False
        except BrokenChain:
            refused = True
        check(refused and not os.path.exists(path),
              "a tampered chain raises and no file is written")
        honest(3).save(path)
        check(os.path.exists(path), "control: an honest chain is written")


def timestamps():
    print("\nreceipt timestamps  (__init__:398)")
    c = Chain()
    r = c.allowed("pay", "1.00", "USD", "alice", "rule",
                  at="2026-01-02T03:04:05Z")
    check(r["at"] == "2026-01-02T03:04:05Z", "a supplied `at` is kept")
    r = c.allowed("pay", "1.00", "USD", "alice", "rule")
    check(bool(re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$", str(r["at"]))),
          "with none supplied, a UTC timestamp is filled in")


def non_ascii_message():
    print("\nthe non-ASCII error names what was wrong  (__init__:186)")
    try:
        assert_ascii({"payee": "caf\u00e9"})
        msg = ""
    except NonAsciiInReceipt as e:
        msg = str(e)
    check("\u00e9" in msg and "'c'" not in msg,
          "the message names the offending character and not the clean ones")


def disclosure_shapes():
    print("\nmalformed disclosures  (disclose:135,165,242,259)")
    c = honest(2)
    c.refused("pay", "9.00", "USD", "mallory", "over the cap")
    doc = disclose(c.receipts)
    ok, why = check_disclosure(doc)
    check(ok, "control: an honest disclosure checks out (%r)" % why)

    d = disclose(c.receipts)
    d["entries"] = []
    check(check_disclosure(d) == (False, "no entries"),
          "an empty entry list is refused as 'no entries'")
    d = disclose(c.receipts)
    d["entries"] = "abc"
    check(check_disclosure(d) == (False, "no entries"),
          "entries that are not a list are refused as 'no entries'")

    d = disclose(c.receipts)
    d["shown"] = d["shown"] + 1
    ok, why = check_disclosure(d)
    check(not ok and "shown" in why, "a wrong declared `shown` is refused")

    d = disclose(c.receipts)
    d["entries"][0]["seal"] = 7
    ok, why = check_disclosure(d)
    check(not ok and "no seal" in why,
          "an entry whose seal is not a string is refused as having no seal")

    d = disclose(c.receipts)
    d["outcomes"] = 123
    ok, why = check_disclosure(d)
    check(not ok and "not a hash" in why,
          "an outcomes digest that is not a hash is refused as such")


def summaries():
    print("\nthe one-line summary and its plural  (disclose:273,274,285)")
    c = honest(2)
    c.refused("pay", "9.00", "USD", "mallory", "over the cap")
    check(summary(disclose(c.receipts)).startswith(
        "3 entries, 1 shown in full, 2 withheld"),
        "counts of entries, shown and withheld are right")
    one = Chain()
    one.refused("pay", "9.00", "USD", "mallory", "over the cap")
    check("1 withheld entry is a refusal" in
          summary(disclose(one.receipts, show=lambda r: False)),
          "one withheld refusal reads 'entry is'")
    two = Chain()
    two.refused("pay", "9.00", "USD", "mallory", "over the cap")
    two.refused("pay", "8.00", "USD", "mallory", "over the cap")
    check("2 withheld entries are a refusal" in
          summary(disclose(two.receipts, show=lambda r: False)),
          "two withheld refusals read 'entries are'")


def policy_provenance():
    print("\nwho approved it, and which ledger  (policy:135,136)")
    p = Policy(cap="100", currency="USD", allow=["alice"])
    r = p.open(approved_by="Alice, treasurer", ledger="canton:abc").receipts[0]
    check(r["approved_by"] == "Alice, treasurer", "a named approver is kept")
    check(r["ledger"] == "canton:abc", "a named ledger is kept")
    r = Policy(cap="100", currency="USD", allow=["alice"]).open().receipts[0]
    check(r["approved_by"] == "the principal, before the agent ran",
          "with none given, the default approver is stated")
    check(r["ledger"] == "self-attested (no ledger)",
          "with none given, the receipt says it is self-attested")


def policy_expiry():
    print("\nan expired mandate  (policy:181,182)")
    p = Policy(cap="100", currency="USD", allow=["alice"],
               expires_at="2026-06-01T00:00:00Z")
    ok, _ = p.check("1", "alice", now=when("2026-05-31T23:59:59Z"))
    check(ok, "one second before expiry the payment is allowed")
    ok, rule = p.check("1", "alice", now=when("2026-06-01T00:00:00Z"))
    check(not ok and "expired" in rule, "at the expiry instant it is refused")
    ok, rule = p.check("1", "alice", now=when("2026-06-02T00:00:00Z"))
    check(not ok and "expired" in rule, "after expiry it is refused")


def guard_labels():
    print("\nthe labels a guarded action carries  (guard:92,117)")
    policy = Policy(cap="1000", currency="USD", allow=["alice"])
    chain = Chain()

    @guard(policy, chain)
    def pay_invoice(amount, payee):
        return "paid"

    pay_invoice(amount="1.00", payee="alice")
    check(chain.receipts[-1]["what"] == "pay invoice",
          "with no label, the function's own name is used")

    @guard(policy, chain, what="custom label")
    def other(amount, payee):
        return "paid"

    other(amount="1.00", payee="alice")
    check(chain.receipts[-1]["what"] == "custom label",
          "a supplied label is kept")
    attempt(policy, chain, "wire", "1.00", "alice")
    check(chain.receipts[-1]["instrument"] == "policy-governed action",
          "with no instrument, the default is stated")
    attempt(policy, chain, "wire", "1.00", "alice", instrument="swift")
    check(chain.receipts[-1]["instrument"] == "swift",
          "a supplied instrument is kept")


def main():
    for part in (fail_open, long_chain_tail, save_refuses, timestamps,
                 non_ascii_message, disclosure_shapes, summaries,
                 policy_provenance, policy_expiry, guard_labels):
        part()
    print("")
    if fails:
        print("FAILED: %d" % len(fails))
        return 1
    print("the package's failure paths each do what they say.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
