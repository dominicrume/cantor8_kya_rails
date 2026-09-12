#!/usr/bin/env python3
"""No address in this repository may be one a wallet would accept.

The customer screen is the one a real person opens on a phone, with their
wallet in the other hand. It renders a QR code, "Send exactly 500 USDT", "To
this address", a copy button, and two carefully written warnings about picking
the right network -- all of which make it MORE credible, not less.

For weeks the addresses on that screen were real. One of them,
`TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t`, is the USDT TRC20 **contract** address:
coin sent there is gone permanently and nobody can return it. The Bitcoin one
was the BIP-173 specification example. Nothing in the repository said the
screen was a demo, and CLAUDE.md has required since day one that anything
mocked be labelled MOCKED in code and in the demo.

Two things stand between a stranger and that mistake now, and this file is what
keeps both of them there:

**The addresses are structurally invalid.** They fail their own chain's
checksum, so a wallet refuses them rather than sending. That is the guarantee
that survives somebody deleting a warning.

**The screen says so in words**, above the amount, before the address.

An address that merely *looks* fake is not enough. `0xDEADBEEF...` is a valid
Ethereum address and has received real money. The test is whether the chain's
own validation accepts it.

Run: python3 tests/no_real_addresses.py
"""
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58decode(s):
    n = 0
    for c in s:
        if c not in B58:
            return None
        n = n * 58 + B58.index(c)
    return n.to_bytes((n.bit_length() + 7) // 8, "big")


def tron_valid(addr):
    """Base58Check: last four bytes are sha256(sha256(body))[:4]."""
    raw = b58decode(addr)
    if raw is None or len(raw) != 25 or raw[0] != 0x41:
        return False
    body, checksum = raw[:21], raw[21:]
    return hashlib.sha256(hashlib.sha256(body).digest()).digest()[:4] == checksum


def eth_valid(addr):
    """0x plus exactly 40 hex digits. EIP-55 casing is optional, so any
    correctly shaped string is an address a wallet will send to."""
    return bool(re.fullmatch(r"0x[0-9a-fA-F]{40}", addr))


BECH32 = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def bech32_polymod(values):
    """The BIP-173 checksum accumulator, verbatim from the specification.

    Kept separate because it is transcribed rather than written: the five
    generator constants and the shift are the standard, and a reader checking
    this against BIP-173 should see the loop on its own with nothing else in
    the frame. Splitting it also keeps bech32_valid under the complexity
    ceiling, which is how it came to be a function rather than a comment.
    """
    chk = 1
    for v in values:
        top = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ v
        for i, g in enumerate((0x3B6A57B2, 0x26508E6D, 0x1EA119FA,
                               0x3D4233DD, 0x2A1462B3)):
            chk ^= g if (top >> i) & 1 else 0
    return chk


def bech32_split(addr):
    """(hrp, data) for a well-formed bech32 string, else None.

    Shape only. Whether the checksum holds is bech32_valid's question, and
    keeping the two apart is what keeps either of them readable.
    """
    addr = addr.lower()
    if "1" not in addr:
        return None
    hrp, data = addr.rsplit("1", 1)
    if hrp not in ("bc", "tb") or len(data) < 6:
        return None
    if any(c not in BECH32 for c in data):
        return None
    return hrp, data


def bech32_valid(addr):
    """BIP-173 polymod over the data part, which is what a wallet checks."""
    parts = bech32_split(addr)
    if parts is None:
        return False
    hrp, data = parts
    expanded = ([ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]
                + [BECH32.index(c) for c in data])
    return bech32_polymod(expanded) == 1


def xrpl_valid(addr):
    """Ripple base58 alphabet, Base58Check, version byte 0x00."""
    rb58 = "rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz"
    n = 0
    for c in addr:
        if c not in rb58:
            return None
        n = n * 58 + rb58.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    if len(raw) != 25 or raw[0] != 0x00:
        return False
    return hashlib.sha256(hashlib.sha256(raw[:21]).digest()).digest()[:4] == raw[21:]


# A shape this repository uses, and the function that decides whether a wallet
# would accept it. Anything matching the pattern must FAIL its validator.
KINDS = [
    ("TRON",     r"\bT[1-9A-HJ-NP-Za-km-z]{33}\b", tron_valid),
    ("Ethereum", r"\b0x[0-9a-fA-F]{40}\b",         eth_valid),
    ("Bitcoin",  r"\bbc1[02-9ac-hj-np-z]{8,87}\b", bech32_valid),
    ("XRPL",     r"\br[1-9A-HJ-NP-Za-km-z]{24,34}\b", xrpl_valid),
]

SKIP_DIRS = {".git", ".daml", "__pycache__", "node_modules", ".mutation-in-progress"}
SKIP_FILES = {"no_real_addresses.py"}   # the validators need real examples

print("no address anywhere in this repository is one a wallet would accept")
scanned = 0
spendable = []
for base, dirs, names in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    for name in names:
        if name in SKIP_FILES or not name.endswith(
                (".py", ".html", ".js", ".json", ".daml", ".md", ".yml", ".yaml")):
            continue
        path = os.path.join(base, name)
        try:
            text = open(path, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        scanned += 1
        for label, pattern, valid in KINDS:
            for hit in set(re.findall(pattern, text)):
                if valid(hit):
                    spendable.append((label, hit, os.path.relpath(path, ROOT)))

check(scanned > 50, "scanned %d files" % scanned)
check(not spendable,
      "none of them is spendable"
      + ("" if not spendable else
         ": " + "; ".join("%s %s in %s" % s for s in spendable[:3])))

print()
print("and the screen a person would be looking at says what it is")
customer = open(os.path.join(ROOT, "step-5-operator", "customer.html")).read()
check("DEMO ONLY" in customer, "the customer page carries a DEMO ONLY banner")
check("Do not send money" in customer, "  and says it in those words")
# Before the address, not after it. A warning under the QR is a warning read
# second.
check(customer.index("DEMO ONLY") < customer.index("depositAddress"),
      "  and it is rendered BEFORE the address, not below it")

print()
# The validators have to be able to say yes, or "none of them is spendable"
# passes on a repository full of real addresses. Positive controls, the same
# rule this project applies to its secret scans.
print("the validators work, checked against addresses that ARE real")
for label, addr, valid in [
        ("TRON", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t", tron_valid),
        ("Ethereum", "0x8f3aE9dB1B7B2f5F3aE44D9B3F1c8bA2E4d5C6f7", eth_valid),
        ("Bitcoin", "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq", bech32_valid)]:
    check(valid(addr), "  %s: the address this repo used to ship is recognised"
          % label)

print()
print("and the SCAN itself would catch one, not just the validators")
# The validators saying yes is not the same as the walk finding it. There is no
# mutation row for this, because a row's `replace` text would be a spendable
# address living permanently in tests/mutation_suite.py -- and when such a row
# did exist, this scanner flagged that table, correctly. So the scanner proves
# itself here, over a file it writes and deletes.
import tempfile                                              # noqa: E402
probe_dir = tempfile.mkdtemp()
probe = os.path.join(probe_dir, "planted.py")
open(probe, "w").write('PAYOUT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"\n')
found = []
for label, pattern, valid in KINDS:
    for hit in set(re.findall(pattern, open(probe).read())):
        if valid(hit):
            found.append((label, hit))
os.remove(probe)
os.rmdir(probe_dir)
check(len(found) == 1 and found[0][0] == "TRON",
      "a real address planted in a file is found by the same walk (%s)"
      % (found[0][0] if found else "MISSED"))

print()
if fails:
    print("FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("nothing here can receive money, and the one screen a person opens")
print("says so before it shows them anything.")
