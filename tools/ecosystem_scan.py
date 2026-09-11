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


def fence_files(scope, tok):
    """How many .daml files in `scope` contain a fence, and where.

    Code search matches whole words, so this counts FILES rather than fences --
    it is a triage signal, not a measurement. The measurement needs the
    repository on disk and is what assurance.py does.
    """
    found = {}
    for word in FENCES:
        q = urllib.parse.quote("%s %s extension:daml" % (word, scope))
        d = get("/search/code?q=%s&per_page=100" % q, tok)
        if "_error" in d:
            return None, d["_error"]
        for item in d.get("items", []):
            name = item["repository"]["full_name"]
            found.setdefault(name, set()).add(item["path"])
        time.sleep(3)                       # code search is rate-limited hard
    return {k: len(v) for k, v in found.items()}, None


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
    print("  measurement. Point assurance.py at the top of this list:")
    top = max(rows["with_fences"], key=rows["with_fences"].get)
    print("    python3 tools/assurance.py --src PKG --test PKG --for \"%s\"" % top)


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
        print("No GitHub token. Code search needs one; set GITHUB_TOKEN or run")
        print("`gh auth login`. Repository listing would work without it, but a")
        print("scan that silently skips the fence count is a scan that lies.")
        return 2

    scope = "org:%s" % a.org if a.org else "topic:%s" % a.topic
    repos = repos_of(a.org, tok) if a.org else repos_by_topic(a.topic, tok)
    print("scanning %s -- %d repository/ies" % (scope, len(repos)))

    with_fences, err = fence_files(scope, tok)
    if err:
        print("  the fence search failed: %s" % err)
        return 3

    rows = {"scope": scope, "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "daml_repos": len(repos), "with_fences": with_fences}
    report(rows, scope)
    if a.json:
        with open(a.json, "w") as f:
            json.dump(rows, f, indent=2)
        print()
        print("wrote %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
