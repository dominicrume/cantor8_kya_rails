#!/usr/bin/env python3
"""Measure the Canton Dev Fund voting pipeline from the live repository.

Written 9 November 2026, after 43 days of asking the wrong question about
proposal #860. The question was "who will champion this". The mechanism says
the question is "who opens a vote, and when is it called".

Three facts this tool exists to keep measured rather than remembered:

  1. .github/.gitvote.yml sets automation.enabled: false. A vote is NEVER
     created automatically. Somebody runs the command by hand.
  2. Passing needs 51% of the ALLOWED VOTERS, not 51% of votes cast. With
     five eligible that is three binding "In favor". An absent voter is a no.
  3. The binding-vote timestamps cluster into sittings minutes wide. Votes
     are called in a meeting, not reviewed asynchronously. A vote nobody
     calls before its 21 days expire fails with nobody having voted at all.

Stdlib only, per CLAUDE.md. Reads the public repository through `gh`.
No credential is passed in, so no output here is tainted.

Usage, both runnable exactly as written:

    python3 tools/vote_pipeline.py
    python3 tools/vote_pipeline.py 860
"""

import datetime
import json
import re
import subprocess
import sys
from collections import Counter

REPO = "canton-foundation/canton-dev-fund"
TALLY = re.compile(r"\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|")
BINDING = re.compile(
    r"\|\s*@([A-Za-z0-9_-]+)\s*\|\s*(In favor|Against|Abstain)\s*\|\s*"
    r"([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{1,2}:[0-9]{2}:[0-9]{2})"
)


def gh(*args):
    """Run gh and return stdout, or None when it fails. Never prints stderr."""
    p = subprocess.run(("gh",) + args, capture_output=True, text=True)
    if p.returncode != 0:
        return None
    return p.stdout


def config():
    """The voting rules, read from the repository rather than recalled."""
    out = gh("api", f"repos/{REPO}/contents/.github/.gitvote.yml", "-q", ".content")
    if not out:
        return None
    import base64

    text = base64.b64decode(out).decode("utf-8", "replace")
    got = {}
    for key in ("duration", "pass_threshold", "close_on_passing"):
        m = re.search(rf"^\s*{key}:\s*(\S+)", text, re.M)
        if m:
            got[key] = m.group(1)
    m = re.search(r"automation:\s*\n\s*enabled:\s*(\S+)", text)
    if m:
        got["automation_enabled"] = m.group(1)
    got["allowed_voter_teams"] = re.findall(r"teams:\s*\n\s*-\s*(\S+)", text)
    return got


def proposals(limit=400):
    out = gh("pr", "list", "-R", REPO, "--state", "all", "--limit", str(limit),
             "--json", "number,title,state,labels,createdAt")
    return json.loads(out) if out else []


def vote_of(number):
    """Return (outcome, tally, binding, opener) for one proposal."""
    out = gh("pr", "view", str(number), "-R", REPO, "--json", "comments")
    if not out:
        return None
    comments = json.loads(out).get("comments", [])
    tally = binding = opener = None
    for c in comments:
        if c["author"]["login"] != "git-vote":
            continue
        body = c["body"]
        if "Vote created" in body and opener is None:
            m = re.search(r"@([A-Za-z0-9_-]+)", body)
            opener = m.group(1) if m else None
        m = TALLY.search(body)
        if m:
            tally = tuple(int(x) for x in m.groups())
            found = BINDING.findall(body)
            if found:
                binding = found
    return tally, binding, opener


def control():
    """Positive control: a parser that cannot read a known vote is broken.

    #942 closed on 2026-11-04 with four binding votes in favour and one
    absence. If this does not come back, every number below is unreliable
    and the tool says so instead of printing a plausible wrong answer.
    """
    got = vote_of(942)
    if not got:
        return False, "could not read #942 at all"
    tally, binding, _ = got
    if tally != (4, 0, 0, 1):
        return False, f"#942 tally parsed as {tally}, expected (4, 0, 0, 1)"
    if not binding or len(binding) != 4:
        n = len(binding) if binding else 0
        return False, f"#942 binding votes parsed as {n}, expected 4"
    return True, "#942 reads as 4 in favour, 1 absent, 4 binding rows"


def sittings(stamps, minutes=90):
    """Group binding-vote timestamps into sittings."""
    times = sorted(
        datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S") for s in stamps
    )
    out, cur = [], []
    for t in times:
        if cur and (t - cur[-1]).total_seconds() > minutes * 60:
            out.append(cur)
            cur = []
        cur.append(t)
    if cur:
        out.append(cur)
    return out


def one(number):
    rules = config() or {}
    got = vote_of(number)
    out = gh("pr", "view", str(number), "-R", REPO,
             "--json", "number,title,state,labels,createdAt")
    if out is None or got is None:
        print(f"Could not read #{number}. Is `gh` authenticated for this repo?")
        return 1
    pr = json.loads(out)
    names = [l["name"] for l in pr["labels"]]
    tally, binding, opener = got

    print(f"#{pr['number']}  {pr['title'][:70]}")
    print(f"  opened        {pr['createdAt'][:10]}   state {pr['state']}")
    print(f"  gitvote       {', '.join(n for n in names if n.startswith('gitvote')) or 'NO VOTE HAS EVER BEEN OPENED'}")

    if not any(n.startswith("gitvote") for n in names):
        print()
        print("  No vote exists, so the 21-day clock has never started.")
        print("  automation.enabled is", rules.get("automation_enabled", "?"),
              "- nothing opens a vote on its own.")
        print("  The only thing that starts one is a person running the command.")
        print("  Run this tool with no argument to see who that has always been.")
        return 0

    if tally:
        yes, no, abstain, absent = tally
        eligible = sum(tally)
        need = -(-eligible * int(rules.get("pass_threshold", 51)) // 100)
        print(f"  tally         in favour {yes}, against {no}, abstain {abstain}, did not vote {absent}")
        print(f"  arithmetic    {eligible} eligible, {rules.get('pass_threshold','?')}% threshold, so {need} binding yes needed")
        if binding:
            print("  binding votes")
            for who, how, when in sorted(binding, key=lambda r: r[2]):
                print(f"      {when}  {how:<9} @{who}")
    return 0


def main():
    args = sys.argv[1:]
    if args:
        return one(args[0])

    ok, why = control()
    print("positive control:", "PASS" if ok else "FAIL", "-", why)
    if not ok:
        print("\nRefusing to print numbers from a parser that failed its control.")
        return 1
    print()

    rules = config()
    if rules:
        print("== the rules, read from .github/.gitvote.yml ==")
        print(f"  automation enabled   {rules.get('automation_enabled')}"
              "   (false means every vote is opened by hand)")
        print(f"  duration             {rules.get('duration')}")
        print(f"  pass threshold       {rules.get('pass_threshold')}% of ALLOWED VOTERS, not of votes cast")
        print(f"  allowed voter teams  {', '.join(rules.get('allowed_voter_teams') or ['?'])}")
        print()

    rows = proposals()
    withvote = [p for p in rows
                if any(l["name"].startswith("gitvote") for l in p["labels"])]
    print("== how far proposals get ==")
    print(f"  proposals read        {len(rows)}")
    print(f"  reached any vote      {len(withvote)}  "
          f"({100.0 * len(withvote) / max(len(rows), 1):.1f}%)")

    openers, stamps = Counter(), []
    passed, failed = [], []
    for p in withvote:
        got = vote_of(p["number"])
        if not got:
            continue
        tally, binding, opener = got
        if opener:
            openers[opener] += 1
        if binding:
            stamps += [w for _, _, w in binding]
        names = [l["name"] for l in p["labels"]]
        if "gitvote/passed" in names and tally:
            passed.append((p["number"], tally))
        elif "gitvote/failed" in names and tally:
            failed.append((p["number"], tally))

    print(f"  concluded             {len(passed) + len(failed)}"
          f"  (passed {len(passed)}, failed {len(failed)})")
    print()

    print("== who opens votes ==")
    for who, n in openers.most_common():
        print(f"  {n:>3}  @{who}")
    if len(openers) == 1:
        only = openers.most_common(1)[0][0]
        print(f"  Every vote in this history was opened by @{only}. "
              "That is the gate.")
    print()

    print("== outcomes, as yes votes ==")
    for label, group in (("passed", passed), ("failed", failed)):
        if not group:
            continue
        ys = [t[0] for _, t in group]
        print(f"  {label:<7} n={len(group)}  yes min {min(ys)} max {max(ys)}"
              f" mean {sum(ys) / len(ys):.1f}")
        nobody = [n for n, t in group if t[0] == 0 and t[1] == 0 and t[2] == 0]
        if nobody:
            print(f"      {len(nobody)} of these had NOBODY vote at all: "
                  + ", ".join(f"#{n}" for n in nobody))
    anyno = [n for n, t in passed + failed if t[1] > 0]
    print(f"  votes recording any 'against': {len(anyno)}"
          + (f" ({', '.join('#%s' % n for n in anyno)})" if anyno else ""))
    print()

    print("== when votes are actually cast ==")
    groups = [g for g in sittings(stamps) if len(g) >= 3]
    for g in sorted(groups, key=lambda g: g[0])[-8:]:
        span = (g[-1] - g[0]).total_seconds() / 60.0
        print(f"  {g[0].strftime('%Y-%m-%d %a %H:%M')}  "
              f"{len(g):>2} binding votes over {span:.0f} min")
    days = sorted({g[0].date() for g in groups})
    if len(days) >= 2:
        gaps = [(b - a).days for a, b in zip(days, days[1:])]
        print(f"  sitting days: {', '.join(d.isoformat() for d in days)}")
        print(f"  gaps in days: {gaps}")
        print("  Two or three observed sittings establish a gap, NOT a published")
        print("  schedule. Ask the Foundation for the calendar before relying on it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
