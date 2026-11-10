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
# This tool's whole job is to run gh, so the import is the point.
import subprocess  # nosec B404
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
    # Why B603 is suppressed on the call below: literal argv, shell=False,
    # and every element is a string
    # this file wrote: "api", a path built from the REPO constant, and integers
    # formatted into it. No user input reaches it. No credential is passed IN,
    # so nothing it returns is tainted, and stderr is discarded rather than
    # printed because a failing authenticated call echoes its own request.
    p = subprocess.run(("gh",) + args,  # nosec B603
                       capture_output=True, text=True)
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


def _event(when, body):
    """One git-vote comment to (date, kind, tally), or None if it is neither."""
    if "Vote created" in body:
        return (when, "created", None)
    if "Vote closed" not in body:
        return None
    m = TALLY.search(body)
    kind = "failed" if "did not pass" in body else "passed"
    return (when, kind, tuple(int(x) for x in m.groups()) if m else None)


def vote_events(number):
    """Every vote EVENT on one proposal, not just the current label.

    Written 10 November 2026, after this tool said "failed 3" while the
    repository held seven failed votes. The labels gitvote/passed and
    gitvote/failed describe the CURRENT state of a proposal. When a vote
    expires and somebody opens a second one, the label is reset to
    gitvote/open and the failure disappears from any count taken by label.

    #866 is the case that exposed it: a vote opened 16 October, expired
    6 November with nobody having voted, and was re-opened on 9 November.
    By label it is open and has never failed. By history it has failed once.

    Returns a list of (date, kind, tally) oldest first, where kind is
    "created", "failed" or "passed" and tally is (yes, no, abstain, absent)
    or None.
    """
    out = gh("pr", "view", str(number), "-R", REPO, "--json", "comments")
    if not out:
        return []
    bodies = [(c["createdAt"][:10], c["body"])
              for c in json.loads(out).get("comments", [])
              if c["author"]["login"] == "git-vote"]
    return [e for e in (_event(w, b) for w, b in bodies) if e]


def _failure(number):
    """One proposal's last failure, or None. (n, tally, when, re-opened)."""
    ev = vote_events(number)
    fails = [e for e in ev if e[1] == "failed"]
    if not fails:
        return None
    when = fails[-1][0]
    again = [e[0] for e in ev if e[1] == "created" and e[0] >= when]
    return (number, fails[-1][2], when, again[-1] if again else None)


def failures(numbers):
    """Every vote that has failed, by history, with whether it restarted."""
    return [r for r in (_failure(n) for n in numbers) if r]


def _comments(number):
    """(when, author, body) for every comment, oldest first, or None."""
    out = gh("pr", "view", str(number), "-R", REPO, "--json", "comments")
    if not out:
        return None
    return [(c["createdAt"][:16], c["author"]["login"], c["body"])
            for c in json.loads(out).get("comments", [])]


def asks(number, who="dominicrume"):
    """Every ask WE made on a proposal, and whether anybody answered it.

    Written 10 November 2026, after this session told its owner "the question
    has not been asked yet" about #860. It had been asked, on 9 November, and
    it was the right question. The claim was made from memory of the strategy
    rather than from the thread, which is the exact failure the
    no-execution-without-a-measurement rule exists to stop, committed against
    a destination nobody had opened.

    So: before saying anything about what has or has not been asked, run this.

        python3 tools/vote_pipeline.py asks 860
    """
    rows = _comments(number)
    if rows is None:
        print("Could not read #%s." % number)
        return 1
    mine = [r for r in rows if r[1] == who]
    if not mine:
        print("#%s: @%s has never commented. THAT is an unasked question."
              % (number, who))
        return 0
    print("#%s: %d comments, %d of them ours.\n" % (number, len(rows), len(mine)))
    for when, _, body in mine:
        print(_ask_line(when, body, _replies_after(rows, when, who)))
    return 0


def _replies_after(rows, when, who):
    """Comments by anybody else, after ours."""
    return [r for r in rows if r[0] > when and r[1] != who]


def _ask_line(when, body, after):
    """One of our comments, with whether anybody answered it."""
    first = body.strip().splitlines()[0][:72]
    if after:
        tail = "      answered %s by @%s" % (after[0][0], after[0][1])
    else:
        tail = ("      NO REPLY since. Asking again is a nudge unless "
                "something changed.")
    return "  %s  %s\n%s" % (when, first, tail)


def _by_yes(row):
    """Sort failures by how many yes votes they got, fewest first."""
    tally = row[1]
    return tally[0] if tally else 9


def _row(row):
    """One failure as a table line."""
    n, tally, when, again = row
    cells = "  ".join("%3s" % x for x in (tally or ("?", "?", "?", "?")))
    return "  #%-5s %s   %s   %s" % (n, cells, when, again or "no")


def reopened(numbers):
    """Print the failures the labels hide, and whether the clock restarted.

    This is the finding the tool exists for now. A failed vote is not final:
    the same person who opened the first one opens a second, and the label
    makes the first failure invisible.
    """
    rows = failures(numbers)
    if not rows:
        return
    print("== every vote that has FAILED, by history and not by label ==")
    print("  prop   yes  no abs absent   failed on    re-opened")
    for row in sorted(rows, key=_by_yes):
        print(_row(row))
    quiet = [r for r in rows if r[1] and r[1][1] == 0]
    back = [r for r in rows if r[3]]
    print(f"  {len(rows)} votes have failed. {len(quiet)} recorded NO vote "
          "against at all: they failed")
    print("  because the eligible voters did not vote, not because anybody "
          "objected.")
    print(f"  {len(back)} of the {len(rows)} were re-opened afterwards, which "
          "resets the label and")
    print("  removes the failure from any count taken by label, including "
          "this tool's own")
    print("  until 10 November 2026.")
    print()


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


def usage():
    print("usage: vote_pipeline.py [<proposal>] | asks <proposal>")
    return 2


def main():
    args = sys.argv[1:]
    if args and args[0] == "asks":
        return asks(args[1]) if len(args) > 1 else usage()
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

    reopened([p["number"] for p in withvote])

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
