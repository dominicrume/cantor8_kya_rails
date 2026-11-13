#!/usr/bin/env python3
"""What is finished here and cannot be read by anybody else.

    python3 tools/unpublished.py

WHY THIS EXISTS. On 13 November 2026 this repository built an adversarial
harness that nobody in the Canton ecosystem had, proved it against a real
ledger with a control that caught three separate errors, wrote it up, and left
it on one laptop while its author discussed where to post it. At the same
moment, three corrections to false public claims sat in the same unpushed
commit, so github.com was still telling readers that a chain was "anchored on
Canton" when no anchor has ever existed, and that a threat was "defended" on
the strength of a template that had only ever passed `daml test`.

It was the second instance that day of the same shape. The first was a
credential: for 74 days STATUS.md recorded a missing DevNet secret as the
reason the project's central claim was unproven, when the SDK already
installed here shipped a real Canton that needed nobody's permission.

The engineering was never the bottleneck. THE LAST STEP IS THE ONE THAT KEEPS
NOT HAPPENING, and a rule written down is a wish. So this measures the gap
rather than reminding anyone about it.

THREE QUESTIONS, in the order they bite:

  1. Is anything committed and not pushed? Work nobody can fetch is work
     nobody has.
  2. Does every file this repository tells a stranger to run actually answer
     on the public URL? A README that names a command returning 404 is worse
     than silence, because somebody tried.
  3. Is any draft written and unsent? docs/drafts/posted.log is the record,
     and its own first line admits it only begins on 4 November.

It reports and does not scold. Several answers are legitimately "not yet",
and the point is that the number is visible rather than that it is zero.

Stdlib only, per THE-RULES.md. The network reads are plain unauthenticated
GETs of public raw URLs, so no credential goes in and nothing comes back that
needs filtering.
"""
import json
import os
import re
import subprocess  # nosec B404
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = "https://raw.githubusercontent.com/dominicrume/cantor8_kya_rails/main/"

# Files a reader is told to run or read. Checked against the public URL,
# because "it works here" is the whole failure this tool exists for.
PROMISED = [
    "tools/can_the_auditor_tell.py",
    "tools/prove_refusal_on_sandbox.py",
    "tools/vote_pipeline.py",
    "tools/downloads.py",
    "tests/daml_tests.py",
    "tests/mutation_suite.py",
    "docs/the-system-measured.md",
    "docs/dev-fund-vote-mechanism.md",
    "docs/evidence/external-quotes.md",
    "SPEC.md",
    "STATUS.md",
]


def git(*args):
    # B603 and B607: literal argv, shell=False, every element a string.
    r = subprocess.run(["git"] + list(args), cwd=ROOT,  # nosec B603 B607
                       capture_output=True, text=True)
    return r.stdout.strip()


def unpushed():
    """Commits here that the remote does not have."""
    out = git("log", "origin/main..HEAD", "--oneline")
    return [l for l in out.splitlines() if l.strip()]


def reachable(path):
    """Does the public raw URL answer? Returns the status code or None."""
    try:
        req = urllib.request.Request(RAW + path, method="HEAD")
        with urllib.request.urlopen(req, timeout=20) as r:  # nosec B310
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def unsent_drafts():
    """Drafts with no line in posted.log, and not marked RETIRED or BLOCKED."""
    d = os.path.join(ROOT, "docs", "drafts")
    log_path = os.path.join(d, "posted.log")
    log = open(log_path).read() if os.path.exists(log_path) else ""
    out = []
    for name in sorted(os.listdir(d)):
        if not name.endswith(".md") or name in ("README.md", "posted.log"):
            continue
        head = open(os.path.join(d, name)).read(400)
        if re.search(r"^\s*(RETIRED|BLOCKED)", head, re.M):
            continue
        if name not in log:
            out.append(name)
    return out


def check_unpushed(say):
    """Commits nobody else can fetch. 1 if any, 0 if none."""
    say("1. COMMITTED HERE, NOT PUSHED")
    ahead = unpushed()
    if not ahead:
        say("   none. everything committed is fetchable.")
        return 0
    say("   %d commit(s) nobody else can fetch:" % len(ahead))
    for l in ahead:
        say("     " + l)
    say("   git push origin main")
    return 1


def check_reachable(say):
    """Promised files that do not answer 200 publicly. 1 if any."""
    say("2. PROMISED TO A READER, CHECKED ON THE PUBLIC URL")
    missing = [(p, reachable(p)) for p in PROMISED]
    missing = [(p, c) for p, c in missing if c != 200]
    if not missing:
        say("   all %d answer 200." % len(PROMISED))
        return 0
    for path, code in missing:
        say("   %-46s %s" % (path, code if code else "unreachable"))
    say("   A command in a README that 404s is worse than no command.")
    return 1


def report_drafts(say):
    """Reported, never failed: a draft may legitimately be waiting."""
    say("3. WRITTEN AND NOT SENT")
    drafts = unsent_drafts()
    if not drafts:
        say("   none.")
        return
    say("   %d draft(s) with no line in posted.log:" % len(drafts))
    for name in drafts:
        say("     " + name)
    say("   Not a failure on its own. A draft can wait. A forgotten one")
    say("   cannot be told apart from a waiting one without this list.")


def main():
    say = print
    fails = 0

    fails += check_unpushed(say)
    say("")
    fails += check_reachable(say)
    say("")
    report_drafts(say)

    say("")
    if fails:
        say("%d of the first two checks is work that exists and cannot be"
            " reached." % fails)
        return 1
    say("Nothing finished here is unreachable by somebody else.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
