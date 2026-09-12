#!/usr/bin/env python3
"""Text nobody can read is not a style choice.

verifier.html -- the page this whole project points strangers at -- shipped with
`body { background:#0e1512; color:#1c1c1c }`. Near-black text on a near-black
ground. **1.09 to 1**, where the WCAG AA minimum for body text is 4.5. It had to
be select-all-highlighted before it could be read, and that is how it was found:
somebody opened it and could not see the words.

The cause is worth naming because it will happen again. The palette had one ink,
`--ink: #1c1c1c`, and it was correct -- for the light cards. The chat bubbles and
the statement panel set light backgrounds and inherited it, and they read fine at
12:1. Everything sitting directly on the DARK page inherited the same ink and
disappeared. One token doing two jobs on two different grounds.

So this checks two things:

  1. every rule that sets BOTH a background and a colour clears 4.5:1
  2. a rule that sets a background very different from the body's, and does NOT
     set its own colour, is flagged -- because it is inheriting an ink chosen
     for a different ground, which is exactly the bug above

Run: python3 tests/contrast_lint.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = ["step-3-verify/verifier.html", "docs/index.html"]

AA_BODY = 4.5

# Rules that set a background but carry no text, so no ink applies to them.
# Each needs a reason, the same way the complexity ceiling does.
NO_TEXT = {
    ".dot": "a coloured status dot, no text inside",
    ".dot.on": "the same dot, lit",
    ".bar2 i": "a progress bar segment",
    ".bar span": "a progress bar segment",
    ".bar .used": "a progress bar segment",
    ".bar .win": "a progress bar segment",
    ".phone": "the black bezel around the demo screen",
    ".avatar": "sets its own colour anyway",
    ".legend i": "a colour swatch in a legend",
    ".qr": "a white box holding a QR image; line-height:0, no text",
}

# WCAG 2.1 SC 1.4.3 exempts "inactive user interface components" by name. A
# disabled control is meant to read as unavailable, and forcing it to 4.5:1
# would make it look enabled. Listed rather than silently skipped.
DISABLED = re.compile(r":disabled|\.dot\b(?!\.on)|\bdisabled\b")

fails = []


def check(ok, what):
    if not ok:
        fails.append(what)
        print("  FAIL " + what)
    return ok


def lum(hexcol):
    h = hexcol.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) not in (6, 8):
        return None
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4
    return .2126 * f(r) + .7152 * f(g) + .0722 * f(b)


def ratio(a, b):
    la, lb = lum(a), lum(b)
    if la is None or lb is None:
        return None
    hi, lo = max(la, lb), min(la, lb)
    return (hi + .05) / (lo + .05)


def tokens(css):
    """--name: #hex, resolved one level deep, which is all these pages use."""
    out = dict(re.findall(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})", css))
    return out


def colour(value, toks):
    value = value.strip().split()[0].rstrip(";")
    m = re.match(r"var\(--([\w-]+)\)", value)
    if m:
        return toks.get(m.group(1))
    return value if value.startswith("#") else None


def rules(css):
    for m in re.finditer(r"([^{}@]+)\{([^}]*)\}", css):
        sel = " ".join(m.group(1).split())
        if not sel or sel.startswith(("/*", "@")):
            continue
        yield sel, m.group(2)


def body_of(css, toks):
    """(background, ink) for the page itself. Both must be explicit: a body with
    no background borrows whatever ground it happens to land on."""
    for sel, decl in rules(css):
        if sel != "body":
            continue
        bg = re.search(r"background(?:-color)?\s*:\s*([^;}]+)", decl)
        fg = re.search(r"(?:^|[;{\s])color\s*:\s*([^;}]+)", decl)
        return (colour(bg.group(1), toks) if bg else None,
                colour(fg.group(1), toks) if fg else None)
    return None, None


def declared_pair(decl, toks):
    """(background, colour) as this rule states them. None where absent or not
    a measurable colour -- a gradient or a keyword is neither."""
    bg = re.search(r"background(?:-color)?\s*:\s*([^;}]+)", decl)
    fg = re.search(r"(?:^|[;{\s])color\s*:\s*([^;}]+)", decl)
    return (colour(bg.group(1), toks) if bg else None,
            colour(fg.group(1), toks) if fg else None)


def borrowed_ink(name, sel, b, body_bg, body_ink):
    """A rule with a ground of its own and no ink of its own inherits an ink
    chosen for a different ground. That is the bug this file exists for."""
    if sel in NO_TEXT or body_bg is None:
        return
    lb, lp = lum(b), lum(body_bg)
    if lb is None or lp is None or abs(lb - lp) <= .35:
        return
    check(False, "%s: %s sets a %s background but no colour, so it inherits "
                 "the ink meant for the page (%s)"
          % (name, sel[:30], "light" if lb > lp else "dark", body_ink))


def one_rule(name, sel, decl, toks, body_bg, body_ink):
    b, f = declared_pair(decl, toks)
    if b is None:
        return
    if f is None:
        borrowed_ink(name, sel, b, body_bg, body_ink)
        return
    r = ratio(f, b)
    if r is not None and not DISABLED.search(sel):
        check(r >= AA_BODY, "%s: %s -> %s on %s is %.2f:1"
              % (name, sel[:30], f, b, r))


def page(path):
    s = open(os.path.join(ROOT, path)).read()
    if "<style>" not in s:
        return
    css = s[s.index("<style>"):s.rindex("</style>")]
    toks = tokens(css)
    name = os.path.basename(path)

    body_bg, body_ink = body_of(css, toks)
    check(body_bg is not None, "%s: body sets an explicit background" % name)
    check(body_ink is not None, "%s: body sets an explicit text colour" % name)
    if body_bg and body_ink:
        r = ratio(body_ink, body_bg)
        check(r is not None and r >= AA_BODY,
              "%s: body text %s on %s is %.2f:1, below the %.1f:1 minimum"
              % (name, body_ink, body_bg, r or 0, AA_BODY))

    for sel, decl in rules(css):
        one_rule(name, sel, decl, toks, body_bg, body_ink)


def main():
    print("contrast, on every page a person actually opens")
    for p in PAGES:
        if os.path.exists(os.path.join(ROOT, p)):
            page(p)
    print()
    if fails:
        print("CONTRAST LINT FAILED - %d:" % len(fails))
        for f in fails:
            print("  -", f)
        return 1
    print("every measurable text/background pair clears %.1f:1, and no container" % AA_BODY)
    print("borrows an ink meant for a different ground.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
