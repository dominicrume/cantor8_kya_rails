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
         "step-3-verify/verifier.html"]
SAFE = ("esc", "Number", "String", "money", "JSON", "encodeURIComponent")

bad = []
for rel in PAGES:
    src = open(os.path.join(ROOT, rel)).read()
    for i, line in enumerate(src.splitlines(), 1):
        if "innerHTML" not in line:
            continue
        for m in re.finditer(r"\+\s*([A-Za-z_][\w.\[\]]*)", line):
            v = m.group(1)
            if v.startswith(SAFE):
                continue
            if re.search(r"esc\(\s*" + re.escape(v.split(".")[0]), line):
                continue
            bad.append("%s:%d interpolates %r unescaped" % (rel, i, v))

print("XSS lint over %d pages" % len(PAGES))
for b in bad:
    print("  FAIL", b)
if bad:
    print("\n%d unescaped interpolation(s). Wrap them in esc()." % len(bad))
    sys.exit(1)
print("  PASS every innerHTML interpolation goes through esc()")
