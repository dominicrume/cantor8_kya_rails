#!/usr/bin/env python3
"""Is there pull? Measured from public data, with the thresholds written down first.

    python3 tools/pmf_check.py

Product-market fit is not a name and not a formula. It is people who would be very
disappointed if the thing went away. Public counts cannot show that, so this never says
it has been achieved. What it can do is say, from data a stranger can re-read in one
command, whether there is ANY outside pull: downloads, stars, forks, outsiders who opened
an issue or a pull request, an entry on the MCP registry.

Two rules keep it honest:

  * The thresholds below were written before the numbers were read. Moving them afterwards
    is how a rumour gets into a document.
  * A source that could not be reached is NOT CHECKED. It is never read as zero, because
    "I could not look" and "there is nothing" are different sentences.

What it cannot see is kept in docs/pmf-ledger.md by hand: named people, what they did, and
whether they would be very disappointed. Revenue is not public data.

Stdlib only, per THE-RULES.md. It calls curl for the requests, the way tools/authed.py does.
"""
import datetime
import json
import subprocess  # nosec B404 - curl with a literal argv, no shell
import sys

OWNER = "dominicrume"
PACKAGE = "knowyouragenticai-receipts"
REPOS = ("dominicrume/cantor8_kya_rails", "dominicrume/kya-agent-check")
NAME_PARTS = ("knowyouragenticai", "kya-agent-check", "cantor8_kya", OWNER)

# Declared before measuring. Any one of these met is "some outside pull", not fit.
THRESHOLDS = {"outside_contributors": 1, "stars_total": 10, "downloads_30d": 1000}

LIMIT = ("Public counts cannot show product-market fit. Only people who would be very "
         "disappointed without it can, and they are kept by hand in docs/pmf-ledger.md.")


def curl(url):
    """Parsed JSON, or None when the source could not be read."""
    try:
        r = subprocess.run(["curl", "-s", "-m", "25", "-H", "Accept: application/json", url],  # nosec B603 B607
                           capture_output=True, text=True, timeout=40)
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def downloads_30d(fetch):
    data = fetch("https://pypistats.org/api/packages/%s/overall?mirrors=false" % PACKAGE)
    rows = (data or {}).get("data")
    if not isinstance(rows, list):
        return None
    cutoff = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    return sum(r.get("downloads", 0) for r in rows if str(r.get("date", "")) >= cutoff)


def repo_facts(fetch, repo):
    info = fetch("https://api.github.com/repos/" + repo)
    if not isinstance(info, dict) or "stargazers_count" not in info:
        return None
    items = fetch("https://api.github.com/repos/%s/issues?state=all&per_page=100" % repo)
    outsiders = None
    if isinstance(items, list):
        outsiders = {i.get("user", {}).get("login") for i in items} - {OWNER, None}
    return {"stars": info["stargazers_count"], "forks": info.get("forks_count", 0),
            "watchers": info.get("subscribers_count", 0), "outside_people": outsiders}


def registry_entries(fetch):
    found = fetch("https://registry.modelcontextprotocol.io/v0/servers?search=knowyouragenticai&limit=20")
    servers = (found or {}).get("servers")
    if not isinstance(servers, list):
        return None
    names = [(s.get("server", s) or {}).get("name", "") for s in servers]
    return [n for n in names if any(p in n.lower() for p in NAME_PARTS)]


def gather(fetch):
    repos = {r: repo_facts(fetch, r) for r in REPOS}
    return {"downloads_30d": downloads_30d(fetch), "repos": repos, "registry": registry_entries(fetch)}


def outside_people(repos):
    people = set()
    for r in repos:
        people |= (r or {}).get("outside_people") or set()
    return people


def unreachable(facts):
    """True if any source could not be read, so the result is not a finding."""
    repos = facts["repos"].values()
    return (facts["downloads_30d"] is None or facts["registry"] is None
            or any(r is None or r["outside_people"] is None for r in repos))


def tally(facts):
    """(stars across the repositories, outside contributors, any source unreachable)."""
    repos = facts["repos"].values()
    return sum(r["stars"] for r in repos if r), len(outside_people(repos)), unreachable(facts)


def verdict(facts):
    stars, people, blind = tally(facts)
    met = []
    if people >= THRESHOLDS["outside_contributors"]:
        met.append("an outsider has opened an issue or a pull request")
    if stars >= THRESHOLDS["stars_total"]:
        met.append("%d stars across the repositories" % stars)
    if (facts["downloads_30d"] or 0) >= THRESHOLDS["downloads_30d"]:
        met.append("%d downloads in 30 days, mirrors excluded" % facts["downloads_30d"])
    if met:
        return "SOME OUTSIDE PULL: " + "; ".join(met) + ". Read the ledger before believing it."
    if blind:
        return "INCOMPLETE: a source could not be read, so this is not a finding."
    return "NO EVIDENCE OF OUTSIDE PULL in public data. That is not the same as proof of none."


def render(facts):
    def show(v):
        return "NOT CHECKED" if v is None else str(v)
    print("pull check, %s (public data, read now)" % datetime.date.today().isoformat())
    print("thresholds declared first: %s" % json.dumps(THRESHOLDS))
    print("  PyPI downloads, last 30 days, mirrors excluded: %s" % show(facts["downloads_30d"]))
    for repo, r in facts["repos"].items():
        if r is None:
            print("  %s: NOT CHECKED" % repo)
            continue
        print("  %s: stars %d, forks %d, watchers %d, outsiders on issues or pull requests: %s"
              % (repo, r["stars"], r["forks"], r["watchers"], show(None if r["outside_people"] is None else len(r["outside_people"]))))
    reg = facts["registry"]
    print("  MCP Registry entries that are ours: %s" % show(None if reg is None else len(reg)))
    print("  outside repositories that import the package: NOT CHECKED (needs an authenticated code search)")
    print("  revenue and named users: NOT MEASURABLE from public data (docs/pmf-ledger.md)")
    print("\n" + verdict(facts))
    print(LIMIT)


def main(fetch=curl):
    render(gather(fetch))
    return 0


if __name__ == "__main__":
    sys.exit(main())
