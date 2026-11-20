#!/usr/bin/env python3
"""Turn a sealed findings record into a page a customer can read.

    python3 tools/assurance_page.py docs/findings/canton-stablecoin-stablecoin.json report.html

tools/assurance.py produces the record: each authorisation check in a Daml
package is made vacuous in turn and the tests re-run, and a check that no test
notices is UNCOVERED. The record is the evidence, but a person deciding whether to
fix something reads a page. This renders one, from the record and nothing else.

It refuses to render a record whose seal chain does not verify. A page made from
a record that cannot be checked would be a claim about nothing.

Every string from the record goes through html.escape. The page is one file, no
script, no network. It follows the system light or dark setting.

Stdlib only, per THE-RULES.md.
"""
import html
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "step-2-agent"))
from kya_chain import Chain  # noqa: E402  (the seal math the verifier uses)

NOT_PROVEN = (
    "This is a coverage finding, not a vulnerability. A check with no failing test "
    "may still be correct; it means nothing would tell you if it stopped being so.",
    "A check can be exercised by a test that does not go red when it is removed. "
    "This measures whether a named test fails, which is the standard that matters "
    "when someone edits the contract.",
    "Only the constructs listed in the record were tried, at the one commit it names.",
    "It says nothing about the design, the privacy model or anything outside the "
    "contracts that were tested.",
)

CSS = """
:root{--bg:#fbfbfd;--card:#fff;--ink:#1d1d1f;--sub:#5f5f64;--line:#d2d2d7;--accent:#0058b0;--bad:#b00020;--ok:#1d6b34}
@media (prefers-color-scheme:dark){:root{--bg:#000;--card:#1c1c1e;--ink:#f5f5f7;--sub:#a1a1a6;--line:#38383a;--accent:#2997ff;--bad:#ff6b6b;--ok:#5ad27a}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.47 -apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",Arial,sans-serif;-webkit-font-smoothing:antialiased}
main{max-width:720px;margin:0 auto;padding:72px 24px 96px}
h1{font-size:44px;line-height:1.1;letter-spacing:-.022em;margin:0 0 12px;font-weight:700;text-wrap:balance}
h2{font-size:24px;letter-spacing:-.01em;margin:56px 0 16px;font-weight:600}
.lede{color:var(--sub);font-size:21px;margin:0 0 40px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:24px}
.stat b{display:block;font-size:40px;line-height:1;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.stat span{color:var(--sub);font-size:15px}
.bad b{color:var(--bad)} .ok b{color:var(--ok)}
.file{margin:0 0 28px}
.file h3{font-size:15px;color:var(--sub);font-weight:600;margin:0 0 8px;letter-spacing:.02em}
ul{list-style:none;margin:0;padding:0;background:var(--card);border:1px solid var(--line);border-radius:18px}
li{padding:14px 20px;border-top:1px solid var(--line)}
li:first-child{border-top:0}
code{font:14px/1.4 ui-monospace,"SF Mono",Menlo,monospace;overflow-wrap:anywhere}
.where{display:block;color:var(--sub);font-size:14px;margin-top:2px}
.note{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:20px 24px}
.note p{margin:0 0 10px}.note p:last-child{margin:0}
.seal{font:13px/1.5 ui-monospace,"SF Mono",Menlo,monospace;overflow-wrap:anywhere;color:var(--sub)}
a{color:var(--accent)}
:focus-visible{outline:3px solid var(--accent);outline-offset:3px}
"""


def e(value):
    return html.escape(str(value), quote=True)


def load(path):
    with open(path) as f:
        receipts = json.load(f)
    if not isinstance(receipts, list) or not receipts:
        raise ValueError("the record is empty or not a list of receipts")
    return receipts


def verified(receipts):
    chain = Chain()
    chain.receipts = receipts
    try:
        return chain.verify()[0]
    except (KeyError, TypeError):
        return False


def split(receipts):
    by = {k: [r for r in receipts if r.get("outcome") == k]
          for k in ("UNCOVERED", "COVERED", "NOT TESTABLE")}
    return by


def headline(counts, total):
    gaps = counts["UNCOVERED"]
    if gaps == 0:
        return "Every one of the %d checks has a test that notices its removal" % total
    return "%d of %d checks have no test that notices their removal" % (gaps, total)


def stat(css, number, label):
    return '<div class="stat %s"><b>%d</b><span>%s</span></div>' % (css, number, e(label))


def stats(counts):
    parts = [stat("bad" if counts["UNCOVERED"] else "ok", counts["UNCOVERED"], "no test notices if it is removed"),
             stat("ok", counts["COVERED"], "a named test fails without it")]
    if counts["NOT TESTABLE"]:
        parts.append(stat("", counts["NOT TESTABLE"], "could not be tested"))
    return '<div class="stats">%s</div>' % "".join(parts)


def group_by_file(receipts):
    files = {}
    for r in receipts:
        files.setdefault(r.get("payee", "unknown file"), []).append(r)
    return files


def gap_item(r):
    return '<li><code>%s</code><span class="where">line %s</span></li>' % (e(r["what"]), e(r.get("amount", "?")))


def covered_item(r):
    return '<li><code>%s</code><span class="where">fails without it: %s</span></li>' % (
        e(r["what"]), e(str(r.get("rule", "")).replace(" goes red", "")))


def section(title, receipts, item):
    if not receipts:
        return ""
    blocks = ["<h2>%s</h2>" % e(title)]
    for name, rows in sorted(group_by_file(receipts).items()):
        blocks.append('<div class="file"><h3>%s</h3><ul>%s</ul></div>' % (
            e(name), "".join(item(r) for r in rows)))
    return "".join(blocks)


def seal_block(receipts):
    return ('<h2>The record behind this page</h2><div class="note">'
            "<p>%d entries, each sealed to the one before. The chain verified when this page was made.</p>"
            '<p class="seal">head seal %s</p>'
            "<p>Check it yourself: <code>python3 tools/assurance_page.py record.json out.html</code> "
            "refuses to write a page if any entry was changed.</p></div>" % (
                len(receipts), e(receipts[-1]["seal"])))


def limits_block():
    return ('<h2>What this does not prove</h2><div class="note">%s</div>' %
            "".join("<p>%s</p>" % e(line) for line in NOT_PROVEN))


def render(receipts):
    by = split(receipts)
    counts = Counter({k: len(v) for k, v in by.items()})
    first = receipts[0]
    total = sum(counts.values())
    body = "".join((
        "<h1>%s</h1>" % e(headline(counts, total)),
        '<p class="lede">%s. Reviewed %s.</p>' % (e(first.get("instrument", "unknown package")),
                                                  e(str(first.get("at", ""))[:10])),
        stats(counts),
        section("Checks nobody would notice losing", by["UNCOVERED"], gap_item),
        section("Checks a test protects", by["COVERED"], covered_item),
        limits_block(), seal_block(receipts)))
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            "<title>%s</title><style>%s</style></head><body><main>%s</main></body></html>" % (
                e("Guard test review, " + str(first.get("instrument", ""))), CSS, body))


def main(argv):
    if len(argv) != 3:
        print("usage: assurance_page.py RECORD.json OUT.html")
        return 2
    try:
        receipts = load(argv[1])
    except (OSError, ValueError) as err:
        print("cannot read the record: %s" % err)
        return 2
    if not verified(receipts):
        print("REFUSED: the record's seal chain does not verify, so no page was written.")
        return 1
    with open(argv[2], "w") as f:
        f.write(render(receipts))
    print("wrote %s from a record that verifies (%d entries)" % (argv[2], len(receipts)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
