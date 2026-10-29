#!/usr/bin/env python3
"""Who champions a Canton Dev Fund proposal, measured rather than remembered.

WHY THIS EXISTS. On 27 October this repository's owner was told that one
person had championed 15 Dev Fund proposals. On 29 October the same question,
asked a different way, returned 3. Both numbers came from the same API and
neither was written down with its method, so neither could be checked. A
number nobody can re-derive is a rumour, and this file is the answer to that.

Two DIFFERENT things get called "champion" and the confusion between them is
where the 15 and the 3 came from:

  ASSIGNED   The Foundation puts someone on the PR as assignee. This is the
             administrative record and it is what `gh pr list --json
             assignees` returns.
  VOLUNTEERED Someone writes, in a comment, that they will champion it. This
             is how #866 got its champion: Yiannis Varelas (@zeroknowledger)
             wrote "Happy to champion this." on 9 October 2026.

They are not the same set and either one alone is a half-truth.

    python3 tools/champions.py              # both tables
    python3 tools/champions.py --json

Needs `gh` authenticated. The credential never enters this process: gh makes
the call and this file reads only its stdout.
"""
import json
import re
import subprocess  # nosec B404 - fixed argv, no shell
import sys

REPO = "canton-foundation/canton-dev-fund"

# The positive control. Yiannis Varelas wrote "Happy to champion this." on
# proposal #866 on 9 October 2026. If a run of this file does not find HIM, the
# run found nothing because it looked nowhere, and it must say so rather than
# print an empty table. The first version of this file defaulted to reading the
# newest 40 proposals; #866 was 77 back, so it reported "nobody" with a clean
# exit and I believed it for about a minute. A scan that cannot find a case you
# already know about is not a scan.
CONTROL_PR = 866
CONTROL_WHO = "zeroknowledger"

# Said in a comment by someone offering to carry a proposal. Deliberately
# narrow: "championing" and "champion of" match, "this needs a champion" does
# not, because asking for one is the opposite of being one.
VOLUNTEER = re.compile(
    r"\b(happy to champion|i (?:will|can|would) champion|championing this"
    r"|i'?ll champion|will be championing)\b", re.I)


def gh(path, paginate=True):
    """One API call made BY gh, so the credential never enters this process."""
    argv = ["gh", "api", path] + (["--paginate"] if paginate else [])
    try:
        out = subprocess.run(argv, capture_output=True,  # nosec B603 B607
                             text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"_error": str(e)[:90]}
    if out.returncode != 0:
        return {"_error": "gh api exit %d" % out.returncode}
    # --paginate concatenates JSON arrays; stitch them back into one list.
    try:
        return json.loads(out.stdout.replace("][", ","))
    except ValueError as e:
        return {"_error": str(e)[:90]}


def assigned(prs):
    """Who the Foundation put on a proposal, and on which ones."""
    seen = {}
    for pr in prs:
        for who in pr.get("assignees") or []:
            seen.setdefault(who["login"], []).append(pr["number"])
    return seen


def volunteered(prs, limit):
    """Who said in a comment that they would champion one.

    Reads at most `limit` proposals, newest first, because this is one API
    call per proposal and the point is a number you can re-derive in a minute,
    not a complete census you will not wait for.
    """
    seen = {}
    for pr in prs[:limit]:
        body = gh("repos/%s/issues/%d/comments" % (REPO, pr["number"]))
        if isinstance(body, dict):
            continue
        for c in body:
            if VOLUNTEER.search(c.get("body") or ""):
                who = (c.get("user") or {}).get("login", "?")
                seen.setdefault(who, []).append(pr["number"])
    return seen


def table(title, seen, note):
    rows = sorted(seen.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    out = ["%s (%d people)" % (title, len(rows)), "  " + note]
    for who, nums in rows:
        shown = ", ".join("#%d" % n for n in sorted(nums)[:6])
        more = "" if len(nums) <= 6 else ", +%d more" % (len(nums) - 6)
        out.append("  %-26s %2d   %s%s" % (who, len(nums), shown, more))
    if not rows:
        out.append("  nobody")
    return "\n".join(out)


def main(argv):
    limit = 160
    prs = gh("repos/%s/pulls?state=all&per_page=100" % REPO)
    if isinstance(prs, dict):
        sys.exit("could not read %s: %s" % (REPO, prs.get("_error")))
    prs.sort(key=lambda p: -p["number"])
    a, v = assigned(prs), volunteered(prs, limit)
    control_ok = CONTROL_PR in v.get(CONTROL_WHO, [])
    if "--json" in argv:
        print(json.dumps({"repo": REPO, "proposals_read": len(prs),
                          "comments_read_on_newest": min(limit, len(prs)),
                          "assigned": {k: sorted(x) for k, x in a.items()},
                          "volunteered": {k: sorted(x) for k, x in v.items()},
                          "control_passed": control_ok},
                         indent=2, sort_keys=True))
        return 0 if control_ok else 1
    print("%d proposals read from %s\n" % (len(prs), REPO))
    print(table("ASSIGNED by the Foundation", a,
                "the administrative record, across every proposal read"))
    print()
    print(table("VOLUNTEERED in a comment", v,
                "said it themselves, in the newest %d only" % limit))
    print()
    print("The two lists answer different questions. Quote which one you mean.")
    if CONTROL_PR not in v.get(CONTROL_WHO, []):
        print()
        print("FAIL the control: %s is not reported on #%d, and he is there."
              % (CONTROL_WHO, CONTROL_PR))
        print("     So an empty or short list here means the scan looked in")
        print("     the wrong place, not that nobody volunteered.")
        return 1
    print("control: %s found on #%d, so this scan can see a real one."
          % (CONTROL_WHO, CONTROL_PR))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
