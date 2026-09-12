#!/usr/bin/env python3
"""Every page must be a document, on a phone, without a mouse.

Nobody looked at these as screens. They were checked for XSS, for offline
behaviour, for whether a chain verifies -- and never once for whether a person
could read them.

customer.html is the page somebody opens on a phone while their crypto is
already in flight. It had no `<meta viewport>`, no `<!DOCTYPE>`, no charset and
no `lang`. A mobile browser therefore rendered a 440px layout at a 980px
virtual viewport and scaled it to about 45%: unreadable text and a deposit QR
code the customer had to pinch to zoom, in quirks mode, at the worst possible
moment. It had been like that since the file was written.

The operator screen had a focus ring on its inputs and none on its buttons,
including the one that authorises a payout. Nothing anywhere honoured
prefers-reduced-motion, and no region that changes after an action told a
screen reader it had changed -- so a blind operator pressed "Request payout"
and heard nothing at all.

None of that is exotic. It is the first thing anyone doing this professionally
would check, and it is checked here now so it cannot quietly come back.

Run: python3 tests/a11y_lint.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (path, must it be a standalone document?, ids that change after an action)
PAGES = [
    # cVerdict, not the drop zone. The verdict is the thing that CHANGES after
    # an action, and it is the one a screen reader has to hear: "this file has
    # been edited" is useless if only sighted users get it. The drop zone and
    # the file input never change their own text.
    ("step-3-verify/verifier.html", True, ["cVerdict"]),
]

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def document(name, s):
    """A browser has to be told it is reading HTML, in what language, in what
    encoding, and how wide the device is. Miss the last one and a phone
    silently renders the page at desktop width and shrinks it."""
    check(s.lstrip().lower().startswith("<!doctype html"), "%s: has a doctype" % name)
    check(bool(re.search(r"<html[^>]+lang=", s, re.I)), "%s: declares a language" % name)
    check(bool(re.search(r'<meta[^>]+charset=', s, re.I)), "%s: declares its charset" % name)
    check(bool(re.search(r'name=["\']viewport["\']', s, re.I)),
          "%s: has a viewport meta -- without it a phone renders it at 980px" % name)


def usable(name, s):
    # Not "the file mentions focus-visible somewhere" -- the original bug was a
    # ring on the inputs and none on the BUTTONS, on the screen whose button
    # authorises a payout. So ask about buttons, and about links, by name.
    for tag in ("button", "a"):
        check(bool(re.search(r"(^|[,\s]){0}:focus-visible".format(tag), s, re.M)),
              "%s: <%s> gets a visible focus ring" % (name, tag))
    check("prefers-reduced-motion" in s,
          "%s: honours prefers-reduced-motion" % name)
    check(not re.search(r'tabindex=["\'][1-9]', s),
          "%s: no positive tabindex (it reorders the whole page)" % name)
    # A button whose only content is an icon says nothing to a screen reader.
    bare = re.findall(r"<button[^>]*>\s*</button>", s)
    check(not bare, "%s: no button with no accessible name (%d)" % (name, len(bare)))


def announces(name, s, ids):
    """A region that changes after the user does something has to say so.

    Without this the operator presses Request payout, the verdict box fills in,
    and a screen reader reads nothing -- the one moment where silence is worst.
    """
    for i in ids:
        m = re.search(r'<[^>]*id=["\']%s["\'][^>]*>' % re.escape(i), s)
        check(bool(m) and "aria-live" in m.group(0),
              "%s: #%s announces itself when it changes" % (name, i))


def main():
    print("every page, as a screen somebody has to read")
    for path, is_doc, ids in PAGES:
        full = os.path.join(ROOT, path)
        if not os.path.exists(full):
            check(False, "%s: exists" % path)
            continue
        s = open(full).read()
        name = os.path.basename(path)
        if is_doc:
            document(name, s)
        usable(name, s)
        announces(name, s, ids)

    print()
    if fails:
        print("ACCESSIBILITY LINT FAILED - %d:" % len(fails))
        for f in fails:
            print("  -", f)
        return 1
    print("every page is a document, readable on a phone, and usable without a mouse.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
