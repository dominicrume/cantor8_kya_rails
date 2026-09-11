#!/usr/bin/env python3
"""Find the Daml authorisation fences in public code, without cloning anything.

`assurance.py` answers "would anything notice if this rule were removed?" for
one package. It costs a full rebuild and test run per fence, so pointing it at
a repository is a decision worth making on evidence.

This is the evidence. It asks GitHub which repositories contain `assertMsg` or
`ensure` at all, and how many files, so a day of machine time goes somewhere it
will produce a finding rather than a shrug.

    python3 tools/ecosystem_scan.py --org digital-asset
    python3 tools/ecosystem_scan.py --topic canton-network --json out.json

The first scan it ever ran settled a question in two minutes that would have
taken a weekend to answer by hand: IntellectEU, one of the eighteen
organisations the Dev Fund's champion check accepts, has twelve Daml
repositories and **not one `assertMsg` between them**. Nothing to measure. Two
API calls, one target eliminated.

Authentication: the GitHub API allows sixty calls an hour anonymously and code
search needs a token. It reads `GITHUB_TOKEN`, or asks the `gh` CLI at run
time. Nothing is stored, and no token is ever written to a file this tool
produces -- the whole point of publishing a number is that the number can
travel, and a credential must not travel with it.
"""
import argparse
import json
import os
import subprocess  # nosec B404 - asks the gh CLI for a token, nothing else
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
FENCES = ("assertMsg", "ensure")


def token():
    """From the environment, or from `gh`, or not at all."""
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(name):
            return os.environ[name]
    try:
        out = subprocess.run(["gh", "auth", "token"],  # nosec B603 B607 - literal argv
                             capture_output=True, text=True, timeout=20)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return ""


def get(path, tok, tries=3):
    """One API call. Rate limits are answered by waiting, not by failing --
    a scan that dies halfway leaves a half-truth, which is worse than a slow
    scan."""
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "kya-rails-ecosystem-scan",
        **({"Authorization": "Bearer " + tok} if tok else {})})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:  # nosec B310 - https, fixed host
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and attempt < tries - 1:
                time.sleep(20 * (attempt + 1))     # secondary rate limit
                continue
            return {"_error": "%s %s" % (e.code, e.reason)}
        except (urllib.error.URLError, OSError, ValueError) as e:
            if attempt < tries - 1:
                time.sleep(5)
                continue
            return {"_error": str(e)[:90]}
    return {"_error": "gave up"}


def repos_of(org, tok):
    q = urllib.parse.quote("org:%s language:Daml" % org)
    d = get("/search/repositories?q=%s&per_page=100" % q, tok)
    return [] if "_error" in d else d.get("items", [])


def repos_by_topic(topic, tok):
    q = urllib.parse.quote("topic:%s" % topic)
    d = get("/search/repositories?q=%s&per_page=100" % q, tok)
    return [] if "_error" in d else d.get("items", [])


def fence_files(scopes, tok):
    """How many .daml files in each scope contain a fence, and where.

    Code search matches whole words, so this counts FILES rather than fences --
    it is a triage signal, not a measurement. The measurement needs the
    repository on disk and is what assurance.py does.

    `scopes` is a list of qualifiers code search actually understands. That
    word ACTUALLY matters: this took a single `topic:canton-network` scope at
    first, and code search does not support `topic:`. It does not error on one
    either -- it returns total_count 0. So the tool answered "no fences in 46
    repositories, nothing here to measure", confidently, about a question the
    API had never been asked. An unanswerable question reported as an empty
    answer is the precise failure this file's own docstring promises not to
    commit, and it committed it within an hour of being written.
    """
    found = {}
    for scope in scopes:
        for word in FENCES:
            q = urllib.parse.quote("%s %s extension:daml" % (word, scope))
            d = get("/search/code?q=%s&per_page=100" % q, tok)
            if "_error" in d:
                return None, d["_error"]
            for item in d.get("items", []):
                name = item["repository"]["full_name"]
                found.setdefault(name, set()).add(item["path"])
            time.sleep(3)                   # code search is rate-limited hard
    return {k: len(v) for k, v in found.items()}, None


def searchable_scopes(org, repos):
    """Qualifiers code search understands, for the thing the user asked about.

    `org:` it understands. `topic:` it does not, and says so by returning
    nothing rather than by failing -- so a topic scan has to be expanded into
    one `repo:` per repository before it is asked.
    """
    if org:
        return ["org:%s" % org]
    return ["repo:%s" % r["full_name"] for r in repos]


def liveness(full_name, tok):
    """Is anyone home?

    The first target this tool picked had 71 fences, an Apache licence and an
    owner on the Dev Fund's champion list. It was also frozen: last commit to
    main seventeen months earlier, four issues ever opened from outside, one
    ever answered. Three hours of mutation testing were spent before anyone
    asked whether a finding delivered there would be read by a human.

    Fences say there is something to measure. These say whether measuring it
    will reach anybody, which is the constraint that actually binds.
    """
    repo = get("/repos/%s" % full_name, tok)
    if "_error" in repo:
        return {"error": repo["_error"]}
    commits = get("/repos/%s/commits?sha=%s&per_page=1"
                  % (full_name, repo.get("default_branch", "main")), tok)
    last = (commits[0]["commit"]["author"]["date"][:10]
            if isinstance(commits, list) and commits else "")
    outside, answered = outsider_issues(full_name, tok)
    return {"last_commit": last, "archived": repo.get("archived"),
            "outside_issues": outside, "answered": answered,
            "stars": repo.get("stargazers_count", 0)}


def outsider_issues(full_name, tok):
    """(raised by outsiders, of those answered).

    Issues from the owning organisation say nothing about whether a stranger
    gets heard, and a stranger is what we would be.
    """
    issues = get("/repos/%s/issues?state=all&per_page=30" % full_name, tok)
    if not isinstance(issues, list):
        return 0, 0
    org = full_name.split("/")[0].lower().split("-")[0]
    outside = [i for i in issues
               if not i.get("pull_request")
               and not _insider((i.get("user") or {}).get("login", ""), org)]
    return len(outside), len([i for i in outside if i.get("comments", 0)])


def _insider(login, org):
    login = login.lower()
    return login.endswith("-da") or (org and org in login)


def days_since(date_str):
    if not date_str:
        return 9999
    import datetime
    try:
        d = datetime.date(*[int(x) for x in date_str.split("-")])
        return (datetime.date.today() - d).days
    except ValueError:
        return 9999


def worth_it(live):
    """One line a person can act on, and the reason."""
    if live.get("error"):
        return "?", live["error"]
    if live.get("archived"):
        return "NO", "archived"
    age = days_since(live.get("last_commit"))
    if age > 365:
        return "NO", "last commit %d days ago -- nobody would read a finding" % age
    if age > 180:
        return "WEAK", "last commit %d days ago" % age
    if live.get("outside_issues") and not live.get("answered"):
        return "WEAK", "%d outside issues, none answered" % live["outside_issues"]
    return "YES", "active (%d days), %d/%d outside issues answered" % (
        age, live.get("answered", 0), live.get("outside_issues", 0))


def score_all(with_fences, tok, limit=12):
    """The busiest repositories first -- liveness costs three API calls each."""
    live = {}
    for name in sorted(with_fences, key=lambda n: -with_fences[n])[:limit]:
        info = liveness(name, tok)
        info["verdict"], info["why"] = worth_it(info)
        live[name] = info
        time.sleep(1)
    return live


def scan_scope(org, topic, tok):
    """Everything the scan knows about one org or topic, or why it does not."""
    scope = "org:%s" % org if org else "topic:%s" % topic
    repos = repos_of(org, tok) if org else repos_by_topic(topic, tok)
    print("scanning %s -- %d repository/ies" % (scope, len(repos)))
    with_fences, err = search_fences(org, repos, tok)
    if err:
        return None, err
    return {"scope": scope,
            "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "daml_repos": len(repos), "with_fences": with_fences,
            "liveness": score_all(with_fences, tok)}, None


def refuse_without_token():
    print("No GitHub token. Code search needs one; set GITHUB_TOKEN or run")
    print("`gh auth login`. Repository listing would work without it, but a")
    print("scan that silently skips the fence count is a scan that lies.")


def search_fences(org, repos, tok):
    """Ask the question in a form the API can answer, or say we could not."""
    scopes = searchable_scopes(org, repos)
    if not scopes:
        return None, "no repositories matched, so there was nothing to search"
    if not org:
        print("  expanding to %d repo: queries -- code search does not "
              "understand topic:" % len(scopes))
    return fence_files(scopes, tok)


def report(rows, scope):
    print()
    print("%s: %d repository/ies with Daml, %d with fences"
          % (scope, rows["daml_repos"], len(rows["with_fences"])))
    if not rows["with_fences"]:
        print("  No assertMsg or ensure anywhere. Nothing here to measure --")
        print("  which is itself a finding, and it cost two API calls.")
        return
    print()
    print("  files with fences   repository")
    for name, n in sorted(rows["with_fences"].items(), key=lambda kv: -kv[1]):
        print("  %5d               %s" % (n, name))
    print()
    print("  The count is FILES, not fences, and it is triage rather than")
    print("  measurement.")
    if rows.get("liveness"):
        print()
        print("  Is anyone home? A finding in a frozen repository reaches nobody.")
        print()
        print("  worth it  repository                                  why")
        order = {"YES": 0, "WEAK": 1, "NO": 2, "?": 3}
        for name in sorted(rows["liveness"], key=lambda n: (
                order.get(rows["liveness"][n]["verdict"], 9),
                -rows["with_fences"].get(n, 0))):
            v = rows["liveness"][name]
            print("  %-9s %-42s %s" % (v["verdict"], name[:42], v["why"][:44]))
        live = [n for n, v in rows["liveness"].items() if v["verdict"] == "YES"]
        if live:
            print()
            print("  Start here: %s" % live[0])
        else:
            print()
            print("  None of these are worth a mutation run today. That is a")
            print("  result: it costs two minutes and saves a weekend.")


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--org", help="a GitHub organisation to scan")
    ap.add_argument("--topic", help="a GitHub topic to scan instead")
    ap.add_argument("--json", help="also write the result here")
    a = ap.parse_args(argv)
    if not (a.org or a.topic):
        ap.error("give --org or --topic")

    tok = token()
    if not tok:
        refuse_without_token()
        return 2

    rows, err = scan_scope(a.org, a.topic, tok)
    if err:
        print("  the fence search failed: %s" % err)
        return 3

    report(rows, rows["scope"])
    if a.json:
        with open(a.json, "w") as f:
            json.dump(rows, f, indent=2)
        print()
        print("wrote %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
