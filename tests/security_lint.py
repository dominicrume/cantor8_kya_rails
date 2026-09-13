#!/usr/bin/env python3
"""Bandit, with production code held to zero.

This is the metric the auditor reports, run directly so the number can be
broken down instead of quoted. The rule is asymmetric on purpose:

  production code   -> zero findings, no exceptions
  test harnesses    -> subprocess and urlopen are what a harness IS, and
                       flagging them measures how thoroughly a codebase is
                       tested, then reports it as a security score

Every allowance below names the rule and why. An allowance without a reason
is how a security check becomes decoration.

Run: python3 tests/security_lint.py
"""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Rules a test harness necessarily trips, allowed ONLY inside tests/.
TEST_ALLOWED = {
    "B101": "assert IS the test",
    "B404": "importing subprocess is how a harness starts the thing under test",
    "B603": "subprocess with list args and no shell; the argv is ours",
    "B607": "partial path for `daml`, which lives wherever the SDK installed it",
    "B310": "urlopen against our own local test server, guarded by _http()",
}


def is_test(rel):
    name = rel.rsplit("/", 1)[-1]
    return (name.startswith("test_") or name.endswith("_test.py")
            or name == "conftest.py" or "/tests/" in "/" + rel or rel.startswith("tests/"))


def classify(results):
    """Split CWE-tagged findings into production and allowed-in-tests."""
    prod, allowed = [], []
    for i in results:
        if not (i.get("issue_cwe") or {}).get("id"):
            continue
        rel = os.path.relpath(i["filename"], ROOT)
        entry = "%s:%s %s %s" % (rel, i["line_number"], i["test_id"],
                                 i["issue_text"][:58])
        (allowed if is_test(rel) and i["test_id"] in TEST_ALLOWED
         else prod).append(entry)
    return prod, allowed


def main():
    proc = subprocess.run(["bandit", "-r", ROOT, "-f", "json", "-q"],
                          capture_output=True, text=True, check=False)
    if not proc.stdout.strip():
        print("bandit produced no output"); return 1
    results = json.loads(proc.stdout).get("results", [])

    prod, allowed = classify(results)

    print("bandit: %d counted findings" % (len(prod) + len(allowed)))
    print("  %d in test harnesses (allowed, each rule justified in this file)"
          % len(allowed))
    print("  %d in production code" % len(prod))
    if prod:
        print()
        for e in prod:
            print("  FAIL", e)
        print("\nProduction code must be clean. Fix it, or if it is genuinely")
        print("safe, add a `# nosec <RULE> - <reason>` on the line saying why.")
        print()
        print("Separate several rules with a SPACE, not a comma. bandit 1.9.4")
        print("parses `# nosec B603,B607` as B607 only and silently leaves B603")
        print("reported -- a suppression that half-works, which is worse than")
        print("one that does not work at all.")
        return 1
    print("\n  PASS production code is clean")
    return leaky_commands()


LEAKY = [("git credential-", "prints the stored password for a host"),
         ("gh auth token", "prints the GitHub token"),
         ("cat ~/.netrc", "prints stored logins"),
         ("echo $C8_CLIENT_SECRET", "prints the DevNet secret")]

# A line that NAMES one of these in order to forbid it is the point of the
# rule, not a breach of it. The marker often sits on another line because prose
# wraps, so a window is searched rather than the line alone: the first version
# looked at one line and flagged CLAUDE.md and THE-RULES.md for containing the
# rule they state.
ALLOWED_NEARBY = ("never run", "forbid", "prints the", "do not run", "leaky")


def leaks_in(path):
    """Every line of one file that runs a credential-printing command."""
    try:
        lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
    except OSError:
        return []
    out = []
    for i, line in enumerate(lines):
        window = " ".join(lines[max(0, i - 5):i + 6]).lower()
        if any(a in window for a in ALLOWED_NEARBY):
            continue
        for cmd, why in LEAKY:
            if cmd in line:
                out.append("%s:%d: %s (%s)"
                           % (os.path.relpath(path, ROOT), i + 1, cmd, why))
    return out


def scan_finds_a_planted_one():
    """The positive control.

    An empty rule list finds nothing in a clean repository and looks exactly
    like a working scan. The mutation harness proved that, reporting BLIND when
    LEAKY was emptied, so the scan has to demonstrate it can say yes.
    """
    d = tempfile.mkdtemp()
    probe = os.path.join(d, "planted.sh")
    with open(probe, "w") as f:
        f.write("#!/bin/sh\ngh auth token > /tmp/x\n")
    found = bool(leaks_in(probe))
    os.remove(probe)
    os.rmdir(d)
    return found


def scannable():
    """Every file worth reading, except this one, which lists them by design."""
    here = os.path.abspath(__file__)
    for base, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs
                   if d not in (".git", ".daml", "__pycache__", "node_modules")]
        for name in names:
            if not name.endswith((".py", ".sh", ".md", ".yml", ".yaml")):
                continue
            path = os.path.join(base, name)
            if os.path.abspath(path) != here:
                yield path


def leaky_commands():
    """Commands whose OUTPUT is a credential.

    Everything above this reads FILES, which is why none of it could have
    caught what happened on 2026-09-13: an assistant debugging a failed push
    ran a credential helper and a live GitHub OAuth token went into the
    transcript. Nothing was written to disk, so nothing scanned it.

    A rule that lives only in prose is a rule that gets broken by whoever has
    not read the prose recently, which on this project is regularly an AI.
    """
    hits = []
    for path in scannable():
        hits += leaks_in(path)

    print()
    print("and nothing here runs a command that prints a credential")
    if not scan_finds_a_planted_one():
        print("  FAIL the scan cannot find a planted one, so 'clean' means nothing")
        return 1
    if hits:
        print("  FAIL")
        for h in sorted(set(hits))[:6]:
            print("    - " + h)
        return 1
    print("  PASS no command in this repository emits a secret to stdout")
    return 0


if __name__ == "__main__":
    sys.exit(main())
