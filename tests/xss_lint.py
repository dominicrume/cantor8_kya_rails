#!/usr/bin/env python3
"""No unescaped interpolation into innerHTML, anywhere.

The verifier is handed receipt files by strangers -- that is its whole job --
and the operator page will be fed by a webhook. A field carrying markup is not
a hypothetical for either of them.

Run: python3 tests/xss_lint.py
"""
import os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PAGES = ["step-5-operator/operator.html", "step-5-operator/customer.html",
         "step-5-operator/bot.html", "step-3-verify/verifier.html"]
# Functions that escape, or that cannot carry markup.
# fmt() escapes first and then renders only *bold*, _italic_ and `code` from
# the already-escaped text, so it is safe by construction.
SAFE = ("esc", "fmt", "Number", "String", "money", "JSON", "encodeURIComponent")

bad = []
for rel in PAGES:
    src = open(os.path.join(ROOT, rel)).read()
    for i, line in enumerate(src.splitlines(), 1):
        if "innerHTML" not in line:
            continue
        # Only what is actually assigned INTO innerHTML. A className on the
        # same line is not a DOM injection, and a lint that says it is gets
        # worked around rather than obeyed.
        rhs = line[line.index("innerHTML"):]
        # Two ways to build a string, and this used to see only one. A template
        # literal -- `<span>${f}</span>` -- was completely invisible, so a live
        # unescaped injection on the operator page passed the lint. The `+`
        # form of the identical injection was caught, which is worse than being
        # uniformly blind: it looked like the rule was enforced.
        found = [(m.group(1), "+") for m in
                 re.finditer(r"\+\s*([A-Za-z_][\w.\[\]]*)", rhs)]
        found += [(m.group(1), "${}") for m in
                  re.finditer(r"\$\{\s*([A-Za-z_][\w.\[\]]*)", rhs)]
        for v, how in found:
            if v.startswith(SAFE):
                continue
            if re.search(r"esc\(\s*" + re.escape(v.split(".")[0]), line):
                continue
            bad.append("%s:%d interpolates %r unescaped (via %s)" % (rel, i, v, how))

print("XSS lint over %d pages" % len(PAGES))
for b in bad:
    print("  FAIL", b)
if bad:
    print("\n%d unescaped interpolation(s). Wrap them in esc()." % len(bad))
    sys.exit(1)
print("  PASS every innerHTML interpolation goes through esc(), by + or by ${}")
