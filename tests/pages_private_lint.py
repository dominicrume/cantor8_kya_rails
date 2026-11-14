#!/usr/bin/env python3
"""The private working files stay out of the repository, and out of the site.

    python3 tests/pages_private_lint.py

WHY. On 14 November 2026 a review found unsent drafts, a CV, an application, a
third party's private message and a room briefing returning HTTP 200 on
dominicrume.github.io, because docs/ had no Jekyll config and Pages serves
every file under docs/ by default. docs/_config.yml now excludes them. This
fails if that list loses an entry, or if anything in the repository points at
a Pages URL under an excluded path (a link that the exclusion would break).

SINCE 14 NOVEMBER 2026 the private files are not in the repository at all:
they live in a folder outside it (KYA_PRIVATE, default ~/kya-private), and
were removed from git history. This fails if any of them reappears under its
old path. docs/_config.yml still excludes the paths, as a second lock.

WHAT IT DOES NOT SHOW. That Pages honours the file. Only a request to the live
site can show that, and the push that ships the file is what makes it true.
Excluding a file from Pages does not make it private: the repository is public.

Stdlib only, per THE-RULES.md.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUST_EXCLUDE = ["drafts", "outreach", "room-briefing-18-oct.html",
                "opportunities.md", "conversations.md",
                "teaching-the-three-answers.md", "dev-fund-reality.md",
                "moving-to-a-vorem-org.md"]
# Paths that must not exist in the repository at all. posted.log is the one
# thing allowed to stay under docs/drafts: it is the honesty record three
# tools read, and holds only dates, draft names and what was verified.
MUST_NOT_EXIST = ["DO-THIS.md", "docs/outreach", "docs/room-briefing-18-oct.html",
                  "docs/opportunities.md", "docs/conversations.md",
                  "docs/teaching-the-three-answers.md",
                  "docs/dev-fund-reality.md", "docs/moving-to-a-vorem-org.md"]
ALLOWED_IN_DRAFTS = {"posted.log"}
PAGES_URL = re.compile(r"github\.io/cantor8_kya_rails/([A-Za-z0-9_./-]*)")
fails = []


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


def exclude_entries(path):
    """The `- name` lines under `exclude:` in a Jekyll config file."""
    lines = open(path, encoding="utf-8").read().split("\n")
    start = [i for i, line in enumerate(lines) if line.startswith("exclude:")]
    out = []
    for line in lines[start[0] + 1:] if start else []:
        if line.strip() and not line.startswith(" "):
            break
        if line.strip().startswith("- "):
            out.append(line.strip()[2:].strip())
    return out


def excluded():
    """The names excluded by docs/_config.yml, or None if it is missing."""
    path = os.path.join(ROOT, "docs", "_config.yml")
    return exclude_entries(path) if os.path.exists(path) else None


SKIP_DIRS = {".git", "node_modules", ".daml", "log", "__pycache__"}


def repo_files():
    """Every file in the repository, relative to the root. A filesystem walk,
    not `git ls-files`: a copy without .git (the dashboard runs in one) must
    give the same answer, and an untracked draft is just as publishable."""
    out = []
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        out += [os.path.relpath(os.path.join(folder, f), ROOT) for f in files]
    return out


def links_into(names):
    """(file, url path) for every Pages URL under an excluded name."""
    hits = []
    for rel in repo_files():
        if not rel.endswith((".md", ".py", ".html", ".txt", ".json", ".log")):
            continue
        try:
            text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue
        for m in PAGES_URL.finditer(text):
            top = m.group(1).split("/")[0]
            if top in names:
                hits.append((rel, m.group(1)))
    return hits


def main():
    print("the public site does not serve the private working files")
    names = excluded()
    check(names is not None, "docs/_config.yml exists")
    names = names or []
    for want in MUST_EXCLUDE:
        check(want in names, "docs/_config.yml excludes %s" % want)
    for gone in MUST_NOT_EXIST:
        check(not os.path.exists(os.path.join(ROOT, gone)),
              "%s is not in the repository" % gone)
    drafts = os.path.join(ROOT, "docs", "drafts")
    left = sorted(set(os.listdir(drafts)) - ALLOWED_IN_DRAFTS) \
        if os.path.isdir(drafts) else []
    check(not left, "docs/drafts holds only posted.log %s" % (left[:3] or ""))
    bad = links_into(names)
    check(not bad, "no repository file links to an excluded Pages path %s"
          % (bad[:2] or ""))
    print("")
    if fails:
        print("FAILED: %d" % len(fails))
        return 1
    print("the private files are out of the repository, still excluded from the")
    print("site as a second lock, and nothing links to one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
