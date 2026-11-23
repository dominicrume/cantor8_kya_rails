#!/usr/bin/env python3
"""No public document may say we deliver compliance, certification or regulator approval.

    python3 tests/claims_lint.py

EU AI Act Article 50 applies from 2 August 2026 and does not require an attestation layer.
A regulator has not reviewed our work. "Compliant", "certified" and "regulator-ready" are
claims about a decision someone else makes, so a document that says them is selling
something we cannot deliver. This repository has already been caught overclaiming once
("the EU AI Act requires this", STATUS.md), and the rule is easier to keep as a gate than
as a memory.

It reads the public documents and fails on an affirmative claim. A sentence that denies the
claim ("not a compliance certificate", "never write that it is certified") is fine, and so
is a quoted overclaim being corrected, because those are the honest ones. A positive control
plants a real overclaim and requires the scan to find it, so a clean result means something.

Stdlib only, per THE-RULES.md.
"""
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_PARTS = ("docs/evidence/archive", "docs/findings/", "docs/drafts", "node_modules", ".git/",
              ".claude/skills")

CLAIMS = [re.compile(p, re.I) for p in (
    r"\bregulator[- ](ready|readiness|approved|endorsed)\b",
    r"\b(EU AI Act|GDPR|FCA|ISO ?27001|SOC ?2)[- ]compliant\b",
    r"\b(makes?|keeps?|gets?|ensures?|guarantees?) (you|your agent|it|them)\b[^.\n]{0,20}\bcompliant\b",
    r"\bguarantee[sd]? (compliance|that you (are|will be) compliant)\b",
    r"\bcompliance certificate\b",
    r"\bcertified (by|compliant|safe|secure)\b",
    r"\baudit[- ]ready\b",
)]

# What may sit just before a match for it to be a denial or a correction, not a claim.
DENIAL = re.compile(r"\b(not|never|no|nor|neither|cannot|can't|isn't|doesn't|does not|without|"
                    r"deliberately|omit(ted)?|overclaim|overclaimed|dead|wrong|false|rather than|"
                    r"nothing|none)\b", re.I)
ALLOWED_PHRASES = ("certified as kya assessors",)


def documents(root):
    for base, dirs, files in os.walk(root):
        rel = os.path.relpath(base, root).replace(os.sep, "/") + "/"
        if any(part in rel for part in SKIP_PARTS):
            dirs[:] = []
            continue
        for name in files:
            if name.endswith((".md", ".html")) and "build.html" not in name:
                yield os.path.join(base, name)


def findings(path):
    out = []
    try:
        text = open(path, errors="replace").read()
    except OSError:
        return out
    low = text.lower()
    for rx in CLAIMS:
        for m in rx.finditer(text):
            before = low[max(0, m.start() - 60):m.start()]
            around = low[max(0, m.start() - 30):m.end() + 30]
            if DENIAL.search(before) or any(a in around for a in ALLOWED_PHRASES):
                continue
            line = text.count("\n", 0, m.start()) + 1
            out.append((line, m.group(0)))
    return out


def scan(root):
    return [(os.path.relpath(p, root), n, w) for p in documents(root) for n, w in findings(p)]


PLANTS = ["Our assessment is regulator-ready.", "We are EU AI Act compliant.",
          "This makes you compliant.", "We guarantee compliance.",
          "You receive a compliance certificate.", "This agent is certified by us.",
          "Your agent is audit-ready."]
HONEST = "It is not a compliance certificate. No agent is regulator-approved by us.\n"


def control():
    """One planted sentence per pattern, so a pattern that stops working is noticed."""
    with tempfile.TemporaryDirectory() as d:
        for i, text in enumerate(PLANTS):
            open(os.path.join(d, "planted%d.md" % i), "w").write(text + "\n")
        open(os.path.join(d, "honest.md"), "w").write(HONEST)
        files = {f for f, _, _ in scan(d)}
    missed = [p for i, p in enumerate(PLANTS) if "planted%d.md" % i not in files]
    ok = not missed and "honest.md" not in files
    print("  %s each pattern finds its planted overclaim, and an honest denial is left alone%s"
          % ("PASS" if ok else "FAIL", "" if not missed else " (missed: %s)" % missed))
    return ok


def real_documents():
    hits = scan(ROOT)
    for f, n, w in hits:
        print("  FAIL %s:%d says %r" % (f, n, w))
    print("  %s no public document claims compliance, certification or regulator approval (%d found)"
          % ("PASS" if not hits else "FAIL", len(hits)))
    return not hits


def main():
    print("claims lint")
    ok = control() and real_documents()
    print("\n%s" % ("ALL GREEN" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
