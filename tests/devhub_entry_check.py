#!/usr/bin/env python3
"""Check the dev-hub listing against the Foundation's own rules before the PR.

The Canton Developer Hub catalogue is a JSON file in a public repo, and its
Contributing.md lists exactly what gets a PR closed without merge:

    - Missing or null daml_sdk_version when the tool clearly uses the Daml SDK
    - type set to "official" for tools not maintained by Digital Asset or
      Canton Foundation
    - Broken or non-https links
    - Invalid JSON
    - Descriptions that are purely marketing copy with no technical substance
    - Tools that are not functional or publicly accessible
    - Duplicate entries for tools already listed

Every one of those is checkable from here, so none of them should be found by
a reviewer. The SDK version is the one that will rot: the Foundation says
"you are responsible for keeping your listing" and a tool more than one major
version behind may be removed. This reads the real number out of daml.yaml
rather than trusting what the entry claims.

    python3 tests/devhub_entry_check.py

Needs network for the link check. That is the point of it.
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRY = os.path.join(ROOT, "docs", "dev-hub-entry.json")
DAML_YAML = os.path.join(ROOT, "step-1-mandate", "daml.yaml")
CATALOGUE = ("https://raw.githubusercontent.com/canton-network-devs/"
             "Canton-Developer-Hub/main/Github%20Page/tools.json")

# From the live catalogue. Kept here so the check still runs offline for
# everything except the link probe.
CATEGORIES = {"Smart Contract Dev", "SDKs", "APIs", "AI Tools", "Data & Indexing",
              "Getting Started", "Local Dev", "Wallet Integration", "Identity"}

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def _via_curl(url):
    """Some sandboxes let curl out but not urllib. Same question, other door."""
    try:
        out = subprocess.run(
            ["curl", "-sL", "--max-time", "25", "-w", "\n%{http_code}", url],
            capture_output=True, timeout=40)
    except (OSError, subprocess.SubprocessError) as e:
        return "unreachable:" + type(e).__name__, b""
    body, _, code = out.stdout.rpartition(b"\n")
    return (int(code) if code.strip().isdigit() else "no status"), body


def fetch(url):
    """(status, body). A status that is not an int means the check could not
    be made -- which is reported as a failure, not quietly as a pass. A link
    nobody could reach is exactly the thing this file exists to catch."""
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""                  # a real answer, just not a 200
    except (urllib.error.URLError, OSError):
        return _via_curl(url)               # no network from here; try the shell


def declared_sdk():
    for line in open(DAML_YAML):
        if line.startswith("sdk-version:"):
            return line.split(":", 1)[1].strip()
    return None


def shape(entry):
    check(entry.get("type") in ("official", "partner"),
          'type is exactly "official" or "partner" (got %r)' % entry.get("type"))
    check(entry.get("type") != "official",
          'type is not "official" -- that is for Digital Asset and the Foundation only')
    check(entry.get("category") in CATEGORIES,
          "category is one the catalogue uses (got %r)" % entry.get("category"))
    check(isinstance(entry.get("dev_fund"), bool),
          "dev_fund is a real boolean, not a string")
    check(bool(entry.get("maintained_by")), "maintained_by names who keeps this current")
    check(bool(entry.get("last_updated")), "last_updated is set")


def description(entry):
    desc = entry.get("desc", "")
    sentences = [s for s in desc.replace("\n", " ").split(". ") if s.strip()]
    check(1 <= len(sentences) <= 2,
          "desc is one to two sentences (got %d)" % len(sentences))
    # "Descriptions that are purely marketing copy with no technical substance"
    # get rejected. Naming the mechanism is what makes it not that.
    substance = ("Daml", "assertMsg", "hash", "chain", "ledger", "choice body",
                 "on-ledger", "SDK", "API", "MCP")
    check(any(w in desc for w in substance),
          "desc names a mechanism, not just a benefit")
    puff = ("revolutionary", "seamless", "cutting-edge", "world-class", "best-in-class",
            "game-changing", "unlock", "empower", "leverage", "next-generation")
    found = [w for w in puff if w in desc.lower()]
    check(not found, "desc has no marketing words (%s)" % (found or "none"))


def sdk(entry):
    real, claimed = declared_sdk(), entry.get("daml_sdk_version")
    check(claimed not in (None, "null", ""),
          "daml_sdk_version is set -- null is an automatic rejection")
    check(claimed == real,
          "daml_sdk_version matches step-1-mandate/daml.yaml (entry %r, repo %r)"
          % (claimed, real))


def links(entry):
    ls = entry.get("links") or []
    check(bool(ls), "there is at least one link")
    for l in ls:
        url = l.get("url", "")
        check(url.startswith("https://"), "%s is https" % l.get("label"))
        code, _ = fetch(url)
        check(code == 200, "%s is live (%s -> %s)" % (l.get("label"), url[:54], code))


def matches_the_listing(entry):
    """Once we are listed, the question inverts.

    This asked "are we absent?", which is the right question exactly once --
    before submitting, so a duplicate is not opened. PR #156 was merged on
    2026-09-08, and from that moment the check was asserting something we had
    just made false, and would have stayed red forever while telling us
    nothing.

    What matters now is drift: the live catalogue is the copy a developer
    reads, and ours is the copy we edit. A description improved here and never
    carried over is a listing that misdescribes the project, and nothing else
    in this repository would notice."""
    code, body = fetch(CATALOGUE)
    if code != 200:
        check(False, "could read the live catalogue (%s)" % code)
        return
    tools = json.loads(body)
    tools = tools if isinstance(tools, list) else tools.get("tools", [])
    mine = [t for t in tools
            if t.get("name", "").strip().lower() == entry["name"].strip().lower()]
    check(len(mine) == 1,
          "listed exactly once (%d entries in the live catalogue)" % len(tools))
    check(entry.get("category") in {t.get("category") for t in tools},
          "category still exists in the live catalogue")
    if len(mine) == 1:
        same_as_live(entry, mine[0])


def same_as_live(entry, live):
    """Field by field, ours against theirs."""
    for field in ("name", "maker", "type", "category", "desc"):
        check(live.get(field) == entry.get(field),
              "live `%s` is what we declare here" % field)
    labelled = lambda t: [(l.get("label"), l.get("url")) for l in t.get("links") or []]
    check(labelled(entry) == labelled(live),
          "all %d links match the live listing, in order" % len(labelled(entry)))


def main():
    print("the dev-hub listing, against the Foundation's own reject list")
    try:
        entry = json.load(open(ENTRY))
    except ValueError as e:
        print("  FAIL the entry is not valid JSON: %s" % e)
        return 1
    check(True, "the entry is valid JSON")
    shape(entry)
    description(entry)
    sdk(entry)
    links(entry)
    matches_the_listing(entry)

    print()
    if fails:
        print("NOT READY TO SUBMIT - %d:" % len(fails))
        for f in fails:
            print("  -", f)
        return 1
    print("this entry passes every rule the Foundation publishes, and the live")
    print("listing still says what we say here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
