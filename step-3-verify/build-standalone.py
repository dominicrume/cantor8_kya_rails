#!/usr/bin/env python3
"""Fold receipts.js into verifier.html and emit ONE file.

verifier.html loads receipts.js with a <script src>, which a browser will
refuse to fetch over file:// in some configurations. This build inlines it, so
the result is a single document that opens by double-click, on any machine,
with no server, no install and no network. That is the file you hand a judge.

    python3 step-3-verify/build-standalone.py
    open step-3-verify/kya-rails-standalone.html
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
html = open(os.path.join(HERE, "verifier.html")).read()
receipts = open(os.path.join(HERE, "receipts.js")).read()

out = html.replace('<script src="receipts.js"></script>',
                   "<script>\n" + receipts + "\n</script>")
if out == html:
    raise SystemExit("could not find the receipts.js script tag in verifier.html")

path = os.path.join(HERE, "kya-rails-standalone.html")
open(path, "w").write(out)
print("wrote %s (%s bytes, no external files)" % (path, format(len(out), ",")))
