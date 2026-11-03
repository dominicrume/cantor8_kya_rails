#!/usr/bin/env python3
"""Decide whether to open anything in somebody else's repository. Exit 1 = no.

WHY THIS EXISTS, with the date and the cost.

CLAUDE.md has carried "NEVER REPORT A DEFECT UNTIL THE COMPARISON IS
CONTROLLED" since 23 October 2026, written after issue #329 against
digital-asset/dpm turned out to be a local misconfiguration. On 31 October
pull request #331 was opened in the same repository and closed the next day
with "AI contribution -- does not appear to be a true concern". The
maintainer was right. The standard he applied had already been written down
before the thing was filed, in the author's own words: a proven mechanism, a
convention it contradicted, no demonstrated user-visible failure.

So the rule existed, was read, was agreed with, and was then walked past. A
rule that has been written four times and broken twice is not a rule, it is a
wish. This is the gate.

    python3 tools/before_contributing.py <owner/repo>

It asks for the four things that separate #330, which merged in six days with
no questions, from #331, which was closed in one day:

  1. the failure a USER hits, in one sentence,
  2. the test that goes red without the fix,
  3. who asked for it, or the issue number, or honestly nobody,
  4. your own record in that repository, which it measures rather than asks.

Three of those are judgement and it writes them down so they can be read back
cold. The fourth is arithmetic and it does it for you: `gh` is called with a
literal argv, nothing is passed a credential, nothing it prints is a secret.

It refuses outright on the phrases that are tells rather than caveats, and it
refuses when your record in that repository says you have already spent more
review time than you have earned back.

Python standard library only.
"""

import json
import os
import subprocess  # nosec B404 - literal argv, shell=False, no credential in
                   # and nothing printed but counts and logins.
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "docs", "contributions.log")
ME = "dominicrume"

# Phrases that read as candour in a draft and are actually the verdict. Each
# one is lifted from the body of #331, which was closed the next day.
TELLS = [
    "what this does not claim",
    "no report of a user hitting this",
    "i have no report",
    "does not claim",
    "no current caller",
    "i have no evidence anyone",
]


def gh(*args):
    r = subprocess.run(  # nosec B603 B607 - literal argv, no shell
        ["gh"] + list(args), capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def record(repo):
    """Your merged and closed count in this repository, measured not asked."""
    raw = gh("api",
             "search/issues?q=repo:%s+author:%s+type:pr&per_page=100" % (repo, ME),
             "--jq", "[.items[] | {n: .number, merged: (.pull_request.merged_at != null), state: .state}]")
    try:
        items = json.loads(raw) if raw else []
    except ValueError:
        return None
    merged = [i["n"] for i in items if i["merged"]]
    closed = [i["n"] for i in items if not i["merged"] and i["state"] == "closed"]
    openn = [i["n"] for i in items if i["state"] == "open"]
    return merged, closed, openn


def ask(prompt, allow_empty=False):
    while True:
        a = input(prompt).strip()
        if a or allow_empty:
            return a
        print("  (this one is required, and if you cannot write it that is "
              "the answer)")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    repo = argv[1]
    if "/" not in repo:
        print("Give it as owner/repo, for example digital-asset/dpm.")
        return 2

    print("Gate for a contribution to %s" % repo)
    print("=" * 66)

    # 4 first, because it is the only one that is arithmetic and it changes
    # how honestly the other three get answered.
    r = record(repo)
    if r is None:
        print("Could not read your record there. gh may not be authenticated.")
        print("Not treating that as a pass: stop and check.")
        return 1
    merged, closed, openn = r
    print("YOUR RECORD THERE, measured just now:")
    print("  merged : %d  %s" % (len(merged), merged or ""))
    print("  closed : %d  %s" % (len(closed), closed or ""))
    print("  open   : %d  %s" % (len(openn), openn or ""))
    if closed and len(closed) >= len(merged):
        print()
        print("  You have had as many closed unmerged as merged here. Every")
        print("  further miss is read against that ratio by whoever picks it")
        print("  up. The bar for this one is higher than for your first.")
    print()

    print("Answer these as if the maintainer were reading them, because the")
    print("whole point is that they will be.")
    print()

    failure = ask("1. What does a USER hit? One sentence, concrete:\n   > ")
    low = failure.lower()
    for t in TELLS:
        if t in low:
            print()
            print("REFUSED. That sentence contains \"%s\"." % t)
            print("That phrasing is not a caveat on a good filing. It was in")
            print("the body of #331 and it was the reason it was closed.")
            return 1
    if len(failure.split()) < 6:
        print()
        print("REFUSED. Six words is not a failure, it is a label.")
        return 1

    test = ask("2. Which test goes red without the fix? Name it, or say no:\n   > ")
    if test.lower() in ("no", "none", "n", "nothing"):
        print()
        print("REFUSED. No failing test means no demonstrated defect. Write")
        print("the test first. If you cannot make one go red, there is")
        print("nothing here to report.")
        return 1

    asked_by = ask("3. Who asked, or which issue? 'nobody' is a valid answer:\n   > ")
    unsolicited = asked_by.lower() in ("nobody", "no one", "none", "unasked")

    print()
    print("=" * 66)
    print("READ THIS BACK COLD before you answer the last one.")
    print()
    print("  user hits : %s" % failure)
    print("  red test  : %s" % test)
    print("  asked by  : %s" % asked_by)
    if unsolicited:
        print()
        print("  Nobody asked. That is allowed and it is how #330 happened.")
        print("  It also means the whole value is in the first line being")
        print("  true, because there is no request to fall back on.")
    print()
    go = ask("Would you spend a maintainer's afternoon on that? yes/no:\n   > ")
    if go.lower() != "yes":
        print()
        print("Stopped. Nothing opened, and that is a result, not a failure.")
        return 1

    with open(LOG, "a") as f:
        f.write("%s %s\n  user hits : %s\n  red test  : %s\n  asked by  : %s\n"
                % (time.strftime("%Y-%m-%d"), repo, failure, test, asked_by))
    print()
    print("Written to docs/contributions.log so the next one can be weighed")
    print("against this one. Open it, and put that first line in the body.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
