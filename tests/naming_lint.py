#!/usr/bin/env python3
"""The name is "Know Your AgenticAI", in full, every time it is prose.

Pearl Digital has published "Know Your Agent (KYA)" since March 2026 and DIF has
KYA-OS, so the bare letters point at somebody else and cannot be defended. The
full phrase is ours. See docs/naming-context.md.

This fails on a bare KYA in the public prose documents. It does NOT look at code
identifiers (kya_chain.py, KyaMandate), which stay so a published package and an
upgrade-checked Daml version are not broken.

EXEMPT, a closed list, each one named in docs/naming-context.md as awaiting the
owner's decision: the project name "KYA Rails", the DIF framework "KYA-OS", the
spec's own title "KYA Receipt Chain", and a bare KYA that is quoted as a MENTION
of the letters ("KYA", the acronym KYA).

Has a positive control: a planted bare KYA must be caught, or the lint fails.

Run: python3 tests/naming_lint.py
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = ["README.md", "SPEC.md", "pkg/README.md"] + sorted(
    glob.glob(os.path.join(ROOT, "docs", "paper", "*.html")))
BARE = re.compile(r"(?<![\w_/-])KYA(?![\w_-])")
EXEMPT = (re.compile(r"KYA Rails"), re.compile(r"KYA Receipt Chain"),
          re.compile(r"\"KYA\""), re.compile(r"acronym KYA"),
          re.compile(r"KYA-OS"))


def hits(text):
    found = []
    for n, line in enumerate(text.splitlines(), 1):
        scrubbed = line
        for ok in EXEMPT:
            scrubbed = ok.sub(" ", scrubbed)
        if BARE.search(scrubbed):
            found.append((n, line.strip()[:90]))
    return found


def scan():
    bad = 0
    for p in DOCS:
        path = p if os.path.isabs(p) else os.path.join(ROOT, p)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for n, line in hits(f.read()):
                print("BARE KYA %s:%d  %s" % (os.path.relpath(path, ROOT), n, line))
                bad += 1
    return bad


def main():
    if not hits("KYA asks what an agent did.") or hits("Know Your AgenticAI asks."):
        print("CONTROL FAILED: the lint does not catch a planted bare KYA")
        return 1
    bad = scan()
    print("naming_lint: %s (%d files, control passed)" % (
        "FAIL, %d bare uses" % bad if bad else "ok", len(DOCS)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
