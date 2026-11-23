#!/usr/bin/env python3
"""The pull check must never turn "I could not look" into "there is nothing".

    python3 tests/pmf_check_smoke.py

tools/pmf_check.py reads public data and says whether there is any outside pull. This
drives it with a fake data source, so no network is needed, and holds it to its rules:
the thresholds are declared up front, the owner's own activity is not outside pull, an
unreachable source is NOT CHECKED and never zero, and the tool never claims fit.

Stdlib only, per THE-RULES.md.
"""
import contextlib
import datetime
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pmf_check as P  # noqa: E402

fails = []


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


def feed(downloads=0, stars=0, outsiders=(), registry=(), down=(), old=0):
    """A fake fetch. `down` lists URL fragments that are unreachable (None)."""
    today = datetime.date.today().isoformat()
    long_ago = (datetime.date.today() - datetime.timedelta(days=90)).isoformat()
    people = [{"user": {"login": P.OWNER}}] + [{"user": {"login": o}} for o in outsiders]
    # Order matters: the issues URL also contains the repository URL.
    routes = [
        ("pypistats", {"data": [{"date": today, "downloads": downloads},
                                {"date": long_ago, "downloads": old}]}),
        ("/issues", people),
        ("api.github.com/repos/", {"stargazers_count": stars, "forks_count": 0, "subscribers_count": 0}),
        ("registry", {"servers": [{"server": {"name": n}} for n in registry]}),
    ]

    def fetch(url):
        if any(d in url for d in down):
            return None
        return next((body for fragment, body in routes if fragment in url), None)
    return fetch


def run(**kw):
    facts = P.gather(feed(**kw))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        P.render(facts)
    return P.verdict(facts), out.getvalue()


def the_quiet_case():
    v, out = run()
    check(v.startswith("NO EVIDENCE"), "nothing anywhere reads as no evidence of outside pull")
    check("not the same as proof of none" in v, "and says that is not proof of none")
    check("Public counts cannot show product-market fit" in out, "it always says public counts cannot show fit")
    check("fit has been achieved" not in out and "PMF achieved" not in out, "it never claims product-market fit")
    check('"stars_total": 10' in out and "declared first" in out, "the thresholds are printed, declared first")


def people_and_stars():
    v, _ = run(outsiders=["alice"])
    check(v.startswith("SOME OUTSIDE PULL") and "outsider" in v, "an outsider's issue is outside pull")
    v, _ = run()
    check("outsider" not in v, "the owner's own issues are not outside pull")
    v, _ = run(stars=4)
    check(v.startswith("NO EVIDENCE"), "8 stars across two repositories is under the threshold, so not pull")
    check(P.tally(P.gather(feed(stars=6)))[0] == 12, "stars are summed across both repositories")
    v, _ = run(stars=6)
    check(v.startswith("SOME OUTSIDE PULL") and "12 stars" in v, "12 stars across two repositories meets the threshold")


def downloads():
    v, _ = run(downloads=10, old=50000)
    check(v.startswith("NO EVIDENCE"), "downloads from 90 days ago are not in a 30 day figure")
    v, _ = run(downloads=1200)
    check(v.startswith("SOME OUTSIDE PULL") and "downloads" in v, "downloads over the threshold are reported")


def unreachable_sources():
    v, out = run(down=["pypistats"])
    check(v.startswith("INCOMPLETE") and "NOT CHECKED" in out, "unreachable downloads are NOT CHECKED, never zero")
    v, out = run(down=["/issues"])
    check(v.startswith("INCOMPLETE") and "NOT CHECKED" in out, "unreachable issue lists are NOT CHECKED, never zero")
    v, _ = run(down=["registry"])
    check(v.startswith("INCOMPLETE"), "an unreachable registry is not read as 'not listed'")
    v, _ = run(down=["pypistats"], outsiders=["alice"])
    check(v.startswith("SOME OUTSIDE PULL"), "real pull is still reported when another source is down")


def the_registry():
    names = ["io.github.dominicrume/kya", "com.skyaccess/skyaccess"]
    check(P.registry_entries(feed(registry=names)) == ["io.github.dominicrume/kya"],
          "only registry entries that are ours are counted ('skyaccess' is not)")


def main():
    print("pull check")
    for group in (the_quiet_case, people_and_stars, downloads, unreachable_sources, the_registry):
        group()
    print("\n%s" % ("ALL GREEN" if not fails else "%d FAILED: %s" % (len(fails), fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
