#!/usr/bin/env python3
"""The scan tells the truth about what it found, including when it found none.

`assurance.py` costs a full rebuild and test run per fence -- hours for a large
repository. Deciding where to spend that on a hunch is how a week disappears.
The scan is the triage, so the thing it must never do is be encouraging.

Three claims, and the second is the one that saved a weekend.

**It counts files, and says so.** Code search matches words, not fences. A
repository with 48 matching files does not have 48 fences, and a triage signal
presented as a measurement is a number that will be quoted back wrongly.

**Nothing found is a result, not a failure.** IntellectEU is one of the
eighteen organisations the Dev Fund's champion check accepts. It has twelve
Daml repositories and no `assertMsg` in any of them. The scan has to say that
plainly rather than print an empty table, because "no fences here" is what
stopped a weekend being spent on a target with nothing to measure.

**It never writes a credential into its output.** The whole point of measuring
an ecosystem is that the number can be published. A token travelling inside it
would be a private key in a public file.

No network: the API layer is stubbed, because what is under test is what the
tool concludes, not whether GitHub is up.

Run: python3 tests/ecosystem_scan_smoke.py
"""
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import ecosystem_scan as scan                                   # noqa: E402

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def run_with(repos, code_hits, argv):
    """The tool, with GitHub replaced by fixtures."""
    calls = []

    def fake_get(path, tok, tries=3):
        calls.append(path)
        if "/search/repositories" in path:
            return {"items": repos}
        if "/search/code" in path:
            return {"items": code_hits}
        return {"_error": "unexpected path"}

    real_get, real_token, real_sleep = scan.get, scan.token, __import__("time").sleep
    scan.get = fake_get
    scan.token = lambda: "fake-token-not-real"
    import time as _t
    _t.sleep = lambda *_a: None
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            rc = scan.main(argv)
    finally:
        scan.get, scan.token = real_get, real_token
        _t.sleep = real_sleep
    return rc, buf.getvalue(), calls


REPOS = [{"full_name": "acme/one"}, {"full_name": "acme/two"}]
HITS = [
    {"repository": {"full_name": "acme/one"}, "path": "daml/A.daml"},
    {"repository": {"full_name": "acme/one"}, "path": "daml/B.daml"},
    {"repository": {"full_name": "acme/one"}, "path": "daml/A.daml"},   # same file, both words
    {"repository": {"full_name": "acme/two"}, "path": "daml/C.daml"},
]

print("a file counted twice is still one file")
out_path = os.path.join(tempfile.mkdtemp(), "scan.json")
rc, text, calls = run_with(REPOS, HITS, ["--org", "acme", "--json", out_path])
check(rc == 0, "the scan completes")
data = json.load(open(out_path))
check(data["with_fences"]["acme/one"] == 2,
      "acme/one counted as 2 files, not 3 -- A.daml matched both words")
check(data["with_fences"]["acme/two"] == 1, "acme/two counted as 1")
check(data["daml_repos"] == 2, "the repository count is the repositories")

print()
print("it says FILES, so nobody quotes it as fences")
check("files with fences" in text, "the column is labelled files with fences")
check("FILES, not fences" in text, "  and it says so in words as well")
check("triage rather than" in text, "  and calls itself triage, not measurement")

print()
print("both fence words are searched, not just the first")
code_queries = [c for c in calls if "/search/code" in c]
check(len(code_queries) == len(scan.FENCES),
      "one code search per fence word (%d)" % len(code_queries))
check(any("assertMsg" in c for c in code_queries), "  assertMsg is searched")
check(any("ensure" in c for c in code_queries), "  ensure is searched")
check(all("extension%3Adaml" in c or "extension:daml" in c for c in code_queries),
      "  and both are limited to .daml files")

print()
print("finding nothing is a result, said plainly")
rc, text, _ = run_with(REPOS, [], ["--org", "empty-org"])
check(rc == 0, "an empty result is still a successful scan")
check("Nothing here to measure" in text,
      "it says there is nothing to measure rather than printing an empty table")
check("itself a finding" in text, "  and names that as a finding")
check("files with fences   repository" not in text,
      "  and does not print a table header with no rows under it")

print()
print("no token ever reaches the file it writes")
body = open(out_path).read().lower()
for secret in ("fake-token-not-real", "authorization", "bearer", "ghp_", "gh_token"):
    check(secret not in body, "the output carries no %r" % secret)
check(set(json.load(open(out_path))) ==
      {"scope", "scanned_at", "daml_repos", "with_fences", "liveness"},
      "the output has exactly the five fields it documents")

print()
print("a frozen repository is not a target, however many fences it has")


def aged(days, outside=0, answered=0, archived=False):
    import datetime
    when = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    return {"last_commit": when, "archived": archived,
            "outside_issues": outside, "answered": answered}


for days, label, want in [(10, "committed last week", "YES"),
                          (200, "quiet for 200 days", "WEAK"),
                          (500, "frozen for 500 days", "NO")]:
    verdict, why = scan.worth_it(aged(days, outside=2, answered=1))
    check(verdict == want, "%s -> %s (%s)" % (label, verdict, why[:38]))

check(scan.worth_it({"archived": True})[0] == "NO", "an archived repo is never a target")
check(scan.worth_it(aged(10, outside=4, answered=0))[0] == "WEAK",
      "active but never answers an outsider -> WEAK, because we would be the outsider")
check(scan.worth_it({"error": "403"})[0] == "?", "an unreadable repo is unknown, not a yes")

# The case that cost three hours: many fences, long dead.
verdict, why = scan.worth_it(aged(520, outside=4, answered=1))
check(verdict == "NO" and "nobody would read" in why,
      "daml-finance's actual shape is refused, and the reason says why")

print()
print("without a token it refuses rather than half-scanning")
real = scan.token
scan.token = lambda: ""
buf = io.StringIO()
try:
    with redirect_stdout(buf):
        rc = scan.main(["--org", "acme"])
finally:
    scan.token = real
check(rc == 2, "exits non-zero with no token")
check("silently skips the fence count is a scan that lies" in buf.getvalue(),
      "  and says why a partial scan would be worse than none")

print()
if fails:
    print("FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("the scan counts files and says so, reports an empty result as a result,")
print("and never writes a credential into a number meant to be published.")
