#!/usr/bin/env python3
"""Turn a mutation run into a record the client can check without trusting you.

An audit firm hands over a PDF. A PDF is a claim: it says what was checked and
you believe it because of who signed it. If a finding is later softened, or one
quietly removed before the report goes to a regulator, nothing about the
document reveals that.

This produces the same thing the rest of this repository produces for payments:
a hash-chained record where every entry names what was checked, what was found,
and the rule that decided it -- and where removing one breaks every seal after
it. The client drops the file on the public verifier page and confirms nobody
edited the findings, including the auditor.

    python3 tools/assurance.py --src PKG --test PKG --for "Their Name"
    python3 tools/assurance.py --src PKG --test PKG --out findings.json

The entries a mutation run produces are exactly the shape a receipt wants: an
attempt, an outcome, and the rule that produced it. `amount` carries the line
number, `payee` the file, `ledger` the toolchain that answered. Reusing the
format rather than inventing a second one is the whole point -- the verifier
page, the three independent implementations and the conformance vectors all
work on this file already, and none of them had to be told about audits.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "step-2-agent"))
sys.path.insert(0, HERE)

from kya_chain import Chain                                    # noqa: E402
import daml_mutate                                             # noqa: E402


def toolchain(src=None):
    """What answered. A finding is only as good as the thing that produced it,
    so the version goes inside the seal rather than beside it.

    Asked about the SUBJECT's directory, because the subject decides which
    assistant builds it. This used to ask from this repository's root, which
    answered "daml 3.4.x" for a package that was built with dpm 3.5.8, so a
    sealed record named a toolchain that had not run.
    """
    where = src or ROOT
    tool, _why = daml_mutate.toolchain_for(where)
    ok, out = daml_mutate.daml(["version"], where)
    for line in out.splitlines():
        if tool == "dpm" and line.strip().startswith("*"):
            return "dpm " + line.strip().lstrip("* ").split()[0]
        if any(w in line for w in ("package SDK version", "project SDK version",
                                   "default SDK version")):
            return "daml " + line.strip().split()[0]
    return "%s (version not reported)" % tool


def subject_commit(path):
    """The commit the subject was at, so the finding stays checkable.

    Added after a re-run on 2026-10-09 found that "52 of 69 on 7 September"
    had quietly stopped being verifiable. Two of the three subject
    repositories had not moved since March, so those numbers reproduced
    exactly. The third had been restructured on 30 September and the package
    the finding named, access-control-v1, no longer existed. There was no way
    to tell from the sealed record which commit had been measured, because
    the record carried a date and a toolchain version and not a commit.

    A date pins the finding to a moment. A commit pins it to the code. Only
    the second survives the subject shipping.
    """
    import subprocess  # nosec B404 - fixed argv, no shell
    try:
        p = subprocess.run(  # nosec B603 B607 - literal argv
            ["git", "-C", path, "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=20)
        sha = p.stdout.strip()
        return sha if p.returncode == 0 and sha else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def stamp_one(chain, row, subject, tools):
    """One fence, one receipt. COVERED and UNCOVERED are both recorded: a report
    that lists only problems is a report nobody can tell apart from a short
    one."""
    state, where, detail = row
    outcome = {"ok": "COVERED", "UNCOVERED": "UNCOVERED",
               "BROKE": "NOT TESTABLE", "STALE": "NOT CHECKED"}.get(state, state)
    path, _, rest = where.partition(":")
    line, _, text = rest.partition("  ")
    return chain.stamp(
        what=text.strip()[:120] or "fence",
        amount=line.strip(),                  # the line number, as a string
        payee=path.strip(),                   # the file it lives in
        rule=detail[:160],
        outcome=outcome,
        approved_by="mutation testing: the condition was made vacuous and the "
                    "suite re-run",
        ledger=tools,
        currency="N/A",
        instrument=subject,
    )


def ascii_only(text):
    """The record format refuses non-ASCII (SPEC section 5). A line of someone
    else's source can hold any character, so make it safe rather than crash."""
    return text.encode("ascii", "replace").decode("ascii")


def stamp_unseen(chain, src, under, subject, tools):
    """One NOT SEEN receipt per check-like line the tool does not test, with the
    reason. A record that listed only what was tested would read as complete."""
    unseen = daml_mutate.unseen_all(src, under)
    for path, line, why, text in unseen:
        chain.stamp(
            what=ascii_only(text.strip())[:120] or "check-like line",
            amount=str(line),
            payee=ascii_only(os.path.relpath(path, src)),
            rule=ascii_only(why)[:160],
            outcome="NOT SEEN",
            approved_by="discovery: a check-like line this tool does not test",
            ledger=tools, currency="N/A", instrument=subject)
    return len(unseen)


def stamp_scope(chain, n_fences, n_unseen, n_defs, subject, tools):
    """The closing receipt: what this record covers and what it does not.
    `helper_defs` counts lines of check helpers' own definitions, which are
    never mutated; leaving that number out would make the totals look like
    they accounted for every check word in the source when they did not."""
    named = ",".join(sorted(daml_mutate.SETTINGS["known"])) or "none"
    chain.stamp(
        what="scope of this record", amount=str(n_fences), payee="all",
        rule=("recognised=%d;not_seen=%d;helper_defs=%d;constructs=all;"
              "discovery=daml_fences" % (n_fences, n_unseen, n_defs))[:160],
        outcome="SCOPE",
        approved_by=ascii_only("named check helpers: " + named)[:120],
        ledger=tools, currency="N/A", instrument=subject)


def summary(rows):
    counts = {}
    for state, _w, _d in rows:
        counts[state] = counts.get(state, 0) + 1
    return counts


def run(src, test, subject, out_path, under=None):
    found = daml_mutate.fences(src, under)
    if not found:
        print("No fences in %s. Nothing to assure." % src)
        return 1

    # Pin the subject to a commit, inside the seal, not beside it. See
    # subject_commit() for why this was not here originally and what it cost.
    sha = subject_commit(src)
    if sha:
        subject = "%s @ %s" % (subject, sha)
    else:
        subject = "%s @ commit unknown" % subject
        print("  WARNING: %s is not a git checkout, so this finding cannot be\n"
              "  pinned to a commit and will not stay checkable once the\n"
              "  subject ships." % src)

    print("assuring %s" % subject)
    compiled, base, _out = daml_mutate.build_and_test(src, test)
    if not compiled or not base:
        print("  the project does not build and test cleanly before any mutation.")
        return 2
    print("  %d fence(s), %d passing script(s). This takes a while.\n"
          % (len(found), len(base)))

    rows = daml_mutate.run_all(found, src, test, base)
    tools = toolchain(src)

    chain = Chain()
    for row in rows:
        stamp_one(chain, row, subject, tools)
    if daml_mutate.SETTINGS["constructs"] == "all":
        n_unseen = stamp_unseen(chain, src, under, subject, tools)
        n_defs = len(daml_mutate.helper_defs_all(src, under))
        stamp_scope(chain, len(rows), n_unseen, n_defs, subject, tools)

    ok, bad = chain.verify()
    if not ok:
        print("\nthe record does not verify at entry %s. Refusing to write it." % bad)
        return 3

    with open(out_path, "w") as f:
        json.dump(chain.receipts, f, indent=2)
    report(rows, chain, out_path, subject, len(base))
    return 0


def report(rows, chain, out_path, subject, scripts):
    counts = summary(rows)
    print()
    print("%s -- %d fence(s) against %d passing script(s)" % (subject, len(rows), scripts))
    for state, label in (("ok", "covered by a named test"),
                         ("UNCOVERED", "NO test notices their removal"),
                         ("BROKE", "not testable"),
                         ("STALE", "not checked")):
        if counts.get(state):
            print("  %-3d %s" % (counts[state], label))
    print()
    print("wrote %s -- %d sealed entries, head %s"
          % (out_path, len(chain.receipts), chain.receipts[-1]["seal"][:16] + "..."))
    print()
    print("Hand that file to whoever commissioned this. They can check it on")
    print("https://dominicrume.github.io/cantor8_kya_rails/ with nothing installed.")
    print("If a finding is removed or softened afterwards, every seal after it")
    print("stops matching -- including by the person who wrote the report.")


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", required=True, help="the Daml package holding the contracts")
    ap.add_argument("--test", required=True, help="the package holding the test scripts")
    ap.add_argument("--for", dest="subject", help="who or what this is about")
    ap.add_argument("--out", default="findings.json", help="where to write the record")
    daml_mutate.add_options(ap)
    ap.add_argument("--under", help="mutate only files under this path inside --src; "
                                    "the project still builds from --src. A library whose "
                                    "tests live in the same tree needs this, or the run "
                                    "mutates the tests it is measuring.")
    a = ap.parse_args(argv)
    daml_mutate.configure(a)
    subject = a.subject or os.path.basename(os.path.abspath(a.src))
    return run(a.src, a.test, subject, a.out, a.under)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
