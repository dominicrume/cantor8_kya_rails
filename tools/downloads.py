#!/usr/bin/env python3
"""Measure PyPI downloads, excluding mirrors, instead of remembering them.

WHY THIS EXISTS, with the date and the cost.

STATUS.md carried "84 real downloads a month excluding mirrors" from
2026-10-17 to 2026-11-10. It was never produced by a tool. The only cache in
the repository, docs/evidence/downloads.json, was written 2026-09-24 and its
figures come from pypistats' /recent endpoint, which INCLUDES mirrors, so the
cache could not have been the source of an "excluding mirrors" claim either.

Measured on 2026-11-10 the real figure was 226 in the last 30 days excluding
mirrors. The repository had been understating its own distribution by a factor
of nearly three, in the one file whose job is to be true.

That is the usual rule running backwards. "A number nobody has plotted is a
rumour" is normally a warning against flattering yourself. It cuts both ways:
an unplotted number is simply unknown, and unknown numbers drift in whichever
direction nobody is watching.

    python3 tools/downloads.py                 measure and print
    python3 tools/downloads.py --write         also update docs/evidence/downloads.json

Mirrors are excluded everywhere. A mirror download is a CDN warming its cache,
not a person installing the package, and the two differ by about 3x here.

Python standard library only. No credential is sent, so nothing it prints is
tainted.
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "docs", "evidence", "downloads.json")
API = "https://pypistats.org/api/packages/%s/overall?mirrors=false"

# The Canton package. ai-code-quality-auditor is a SEPARATE PROJECT (CLAUDE.md)
# and is deliberately not summed with this one anywhere.
PACKAGE = "knowyouragenticai-receipts"


def fetch(pkg, mirrors=False):
    url = ("https://pypistats.org/api/packages/%s/overall?mirrors=%s"
           % (pkg, "true" if mirrors else "false"))
    req = urllib.request.Request(url, headers={"User-Agent": "kya-rails-downloads/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:  # nosec B310 - literal https
        return json.load(r)


def window(rows, days):
    """Sum downloads over the last `days` days ending at the newest date present."""
    if not rows:
        return 0, None, None
    dates = sorted(r["date"] for r in rows)
    last = datetime.strptime(dates[-1], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    first = last - timedelta(days=days - 1)
    total = sum(r["downloads"] for r in rows
                if first <= datetime.strptime(r["date"], "%Y-%m-%d").replace(
                    tzinfo=timezone.utc) <= last)
    return total, first.date().isoformat(), last.date().isoformat()


def control():
    """Positive control. Three things must hold or no number is printed.

    1. The endpoint answers for a package that certainly exists and is busy.
    2. Excluding mirrors gives FEWER downloads than including them. If the two
       are equal the mirrors flag is being ignored, which is precisely the bug
       that made the old cache unusable as a source for an "excluding mirrors"
       sentence.
    3. A package that does not exist is reported as missing rather than as
       zero, because a silent zero is indistinguishable from a quiet package.
    """
    try:
        rows = fetch("requests")["data"]
    except Exception as e:                                   # noqa: BLE001
        return False, "could not reach pypistats for the control: %s" % e
    busy, _, _ = window(rows, 30)
    if busy <= 0:
        return False, "the control package reported %d downloads in 30 days" % busy

    with_m, _, _ = window(fetch("requests", mirrors=True)["data"], 30)
    if not with_m > busy:
        return False, ("mirrors=false returned %d and mirrors=true returned %d; "
                       "the flag is being ignored" % (busy, with_m))

    try:
        fetch("kya-rails-no-such-package-exists-here")
        return False, "a package that does not exist answered successfully"
    except urllib.error.HTTPError:
        pass
    except Exception as e:                                   # noqa: BLE001
        return False, "the missing-package probe failed in the wrong way: %s" % e

    return True, ("requests reads %d in 30d without mirrors and %d with, and a "
                  "missing package 404s" % (busy, with_m))


def main():
    ok, why = control()
    print("positive control: %s - %s" % ("PASS" if ok else "FAIL", why))
    if not ok:
        print()
        print("No figure is printed. A download count that cannot be")
        print("controlled is a rumour, and STATUS.md already carried one")
        print("for twenty-four days.")
        return 1

    rows = fetch(PACKAGE)["data"]
    m30, f30, l30 = window(rows, 30)
    m7, _, _ = window(rows, 7)
    allt = sum(r["downloads"] for r in rows)
    with_m = sum(r["downloads"] for r in fetch(PACKAGE, mirrors=True)["data"])

    print()
    print("  package          %s" % PACKAGE)
    print("  data runs        %s to %s" % (
        sorted(r["date"] for r in rows)[0], l30))
    print("  last 30 days     %d   (%s to %s, mirrors excluded)" % (m30, f30, l30))
    print("  last 7 days      %d" % m7)
    print("  all time         %d   (%d including mirrors)" % (allt, with_m))
    print()
    print("  check it yourself:")
    print("    curl -s \"https://pypistats.org/api/packages/%s/overall?mirrors=false\""
          % PACKAGE)

    if "--write" in sys.argv:
        out = {
            "package": PACKAGE,
            "measured": datetime.now(timezone.utc).date().isoformat(),
            "mirrors_excluded": True,
            "window_30d": {"downloads": m30, "from": f30, "to": l30},
            "window_7d": m7,
            "all_time": allt,
            "all_time_including_mirrors": with_m,
            "source": API % PACKAGE,
            "note": ("Mirrors excluded. The previous cache used pypistats /recent, "
                     "which includes mirrors, and was cited for an excluding-mirrors "
                     "claim. See tools/downloads.py."),
        }
        with open(CACHE, "w") as f:
            json.dump(out, f, indent=2)
            f.write("\n")
        print()
        print("  wrote %s" % os.path.relpath(CACHE, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
