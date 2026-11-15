#!/usr/bin/env python3
"""The README names exactly the constructs the harness recognises.

    python3 tests/daml_constructs_parity_lint.py

tools/daml_fences.py decides which Daml constructs count as checks. The README
tells readers which they are. Three documents once named only `assertMsg` and
`ensure` while the tool's real list was changing, which is how a stranger
comes to trust a count that means something else. This fails if the list in
README.md between the `constructs:begin` and `constructs:end` markers differs
from daml_fences.ALL_KINDS, in either direction.

Stdlib only, per THE-RULES.md.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import daml_fences as df          # noqa: E402

fails = []


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


def documented():
    text = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    m = re.search(r"<!-- constructs:begin -->(.*?)<!-- constructs:end -->", text, re.S)
    return set(re.findall(r"`([A-Za-z][\w']*)`", m.group(1))) if m else None


print("the README names the constructs the harness recognises")
doc = documented()
check(doc is not None, "README.md has the constructs:begin and constructs:end markers")
doc = doc or set()
tool = set(df.ALL_KINDS)
check(doc >= tool, "every recognised construct is documented (missing: %s)" % sorted(tool - doc))
check(doc - tool <= {"--known-checks"}, "nothing is documented that the tool does not recognise (extra: %s)"
      % sorted(doc - tool))
check(set(df.LEGACY) <= tool, "the legacy pair is a subset of the full list")
print("")
if fails:
    print("FAILED: %d" % len(fails))
    sys.exit(1)
print("the documented construct list and the tool's list are the same.")
