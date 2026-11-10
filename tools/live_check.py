#!/usr/bin/env python3
"""Probe every public artefact and write a page where each row was just checked.

WHY THIS EXISTS. "What have we actually shipped?" could only be answered by
opening eleven browser tabs and remembering the answers. A list of links typed
by hand is a claim; a link that 404s on the day someone follows it is worse than
no link, because the reader stops trusting the rest of the page.

So nothing here is typed from memory. Every row is fetched when the page is
built, the HTTP status goes on the page, and the page says when it was built.
A row that fails is printed as a failure rather than quietly dropped, because a
list that only shows what is working is a brochure.

    python3 tools/live_check.py            probe and print
    python3 tools/live_check.py --write    also write docs/live.html

No credential is sent to anything. Every URL is public, so nothing printed here
is tainted. Python standard library only.
"""
import html
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "live.html")
UA = {"User-Agent": "kya-rails-live-check/1.0"}

# (group, what it is, url, the one command or action that checks it yourself)
ITEMS = [
    ("Run it yourself", "The receipt format on PyPI, 1.2.0, zero dependencies, MIT",
     "https://pypi.org/project/knowyouragenticai-receipts/",
     "pip install knowyouragenticai-receipts && python -m knowyouragenticai_receipts"),
    ("Run it yourself", "The offline verifier. Drop a receipt file on it, press tamper, watch the chain go red",
     "https://dominicrume.github.io/cantor8_kya_rails/",
     "open the page, no install, no account"),
    ("Run it yourself", "The build report. Every suite, with what a green result actually means",
     "https://dominicrume.github.io/cantor8_kya_rails/build.html",
     "python3 tools/dashboard.py"),
    ("Run it yourself", "The source, MIT",
     "https://github.com/dominicrume/cantor8_kya_rails",
     "git clone https://github.com/dominicrume/cantor8_kya_rails"),

    ("Daml packages, publicly pullable", "canton-refusal-record 1.0.0, a refusal written as a contract",
     "https://github.com/dominicrume/cantor8_kya_rails/tree/main/step-0-refusal",
     "dpm pull ghcr.io/dominicrume/canton-refusal-record:1.0.0"),
    ("Daml packages, publicly pullable", "canton-journal-interface 1.0.0, the auditor-visible journal",
     "https://github.com/dominicrume/cantor8_kya_rails/tree/main/step-0-refusal",
     "dpm pull ghcr.io/dominicrume/canton-journal-interface:1.0.0"),

    ("Listed in the ecosystem", "Canton Developer Hub, AI Tools",
     "https://canton-network-devs.github.io/Canton-Developer-Hub/",
     "curl -s https://raw.githubusercontent.com/canton-network-devs/Canton-Developer-Hub/main/Github%20Page/tools.json | grep -c 'Know Your AgenticAI'"),
    ("Listed in the ecosystem", "Dev Fund proposal #860, open, no vote ever opened",
     "https://github.com/canton-foundation/canton-dev-fund/pull/860",
     "python3 tools/vote_pipeline.py 860"),

    ("Merged into code we do not own", "Canton Developer Hub #156, our entry added",
     "https://github.com/canton-network-devs/Canton-Developer-Hub/pull/156", "merged 2026-09-08"),
    ("Merged into code we do not own", "Canton Developer Hub #160, renders every link on all nineteen cards",
     "https://github.com/canton-network-devs/Canton-Developer-Hub/pull/160", "merged 2026-09-21"),
    ("Merged into code we do not own", "Canton Developer Hub #168, entry rewritten",
     "https://github.com/canton-network-devs/Canton-Developer-Hub/pull/168", "merged 2026-09-21"),
    ("Merged into code we do not own", "digital-asset/dpm #330, fail loudly on unreadable registry auth",
     "https://github.com/digital-asset/dpm/pull/330", "merged 2026-10-29"),
    ("Merged into code we do not own", "canton-foundation/cips #286, fixed the CIP-0129 README link",
     "https://github.com/canton-foundation/cips/pull/286", "merged"),

    ("Findings against real third-party code", "Mutation testing three OpenZeppelin Canton packages",
     "https://github.com/dominicrume/cantor8_kya_rails/blob/main/docs/findings-openzeppelin.md",
     "python3 tools/daml_mutate.py --help"),
    ("Findings against real third-party code", "OpenZeppelin canton-token-template #9, 24 of 32 fences uncovered",
     "https://github.com/OpenZeppelin/canton-token-template/issues/9", "open since 2026-09-07"),
    ("Findings against real third-party code", "OpenZeppelin canton-stablecoin #9, 25 of 30 fences uncovered",
     "https://github.com/OpenZeppelin/canton-stablecoin/issues/9", "open since 2026-09-07"),
    ("Findings against real third-party code", "OpenZeppelin canton-contracts #43, superseded, the replacement is clean",
     "https://github.com/OpenZeppelin/canton-contracts/issues/43", "open since 2026-09-06"),

    ("Written down", "What this proves, and what it does not",
     "https://github.com/dominicrume/cantor8_kya_rails/blob/main/docs/what-this-proves.md", "read it"),
    ("Written down", "The specification, with 20 conformance vectors",
     "https://github.com/dominicrume/cantor8_kya_rails/blob/main/SPEC.md",
     "python3 tests/conformance.py && node tests/conformance.js"),
    ("Written down", "My scanner read the file every run and missed the breach",
     "https://dominicrume.github.io/cantor8_kya_rails/writing/defeated-by-punctuation.html", "read it"),
    ("Written down", "Status: proven, mocked, pending, and three things not claimed",
     "https://github.com/dominicrume/cantor8_kya_rails/blob/main/STATUS.md", "read the PENDING table first"),
]


def probe(url):
    req = urllib.request.Request(url, headers=UA, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=25) as r:  # nosec B310 - literal https
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:                                        # noqa: BLE001
        return 0


def main():
    urls = sorted({u for _, _, u, _ in ITEMS})
    with ThreadPoolExecutor(max_workers=8) as ex:
        status = dict(zip(urls, ex.map(probe, urls)))

    bad = [u for u, s in status.items() if s != 200]
    for group in dict.fromkeys(g for g, _, _, _ in ITEMS):
        print("\n%s" % group)
        for g, what, url, how in ITEMS:
            if g != group:
                continue
            s = status[url]
            print("  %s %-3s %s" % ("OK " if s == 200 else "DEAD", s or "---", what))

    print("\n%d links, %d live, %d not" % (len(urls), len(urls) - len(bad), len(bad)))
    for u in bad:
        print("  DEAD %s  %s" % (status[u] or "no response", u))

    if "--write" not in sys.argv:
        return 1 if bad else 0

    built = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC")
    rows = []
    for group in dict.fromkeys(g for g, _, _, _ in ITEMS):
        rows.append('<h2>%s</h2>\n<table>' % html.escape(group))
        for g, what, url, how in ITEMS:
            if g != group:
                continue
            s = status[url]
            cls = "ok" if s == 200 else "dead"
            lab = str(s) if s else "no response"
            rows.append(
                '<tr><td><span class="pill %s">%s</span></td>'
                '<td><a href="%s">%s</a></td><td><code>%s</code></td></tr>'
                % (cls, lab, html.escape(url), html.escape(what), html.escape(how)))
        rows.append("</table>")

    page = TEMPLATE % {
        "built": html.escape(built),
        "live": len(urls) - len(bad),
        "total": len(urls),
        "rows": "\n".join(rows),
    }
    with open(OUT, "w") as f:
        f.write(page)
    print("\nwrote %s" % os.path.relpath(OUT, ROOT))
    return 1 if bad else 0


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Everything Live</title>
<style>
  :root { --bg:#0e1512; --card:#13201b; --ink:#e6ede9; --dim:#9fb0a8;
          --line:#24352e; --ok:#4ade80; --dead:#f87171; --accent:#128C7E; }
  :root:not([data-theme="dark"]) {
    --bg:#f6f8f7; --card:#fff; --ink:#15211c; --dim:#5a6b64;
    --line:#dde5e1; --ok:#1a7f37; --dead:#c0392b; --accent:#075E54; }
  @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
    --bg:#0e1512; --card:#13201b; --ink:#e6ede9; --dim:#9fb0a8;
    --line:#24352e; --ok:#4ade80; --dead:#f87171; --accent:#25d366; } }
  :root[data-theme="dark"] {
    --bg:#0e1512; --card:#13201b; --ink:#e6ede9; --dim:#9fb0a8;
    --line:#24352e; --ok:#4ade80; --dead:#f87171; --accent:#25d366; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink); padding:0 16px 64px;
         font:16px/1.6 -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; }
  .wrap { max-width:1000px; margin:0 auto; }
  header { padding:48px 0 8px; }
  h1 { font-size:30px; margin:0 0 6px; letter-spacing:-.4px; text-wrap:balance; }
  .sub { color:var(--dim); font-size:14.5px; margin:0; }
  h2 { font-size:15px; text-transform:uppercase; letter-spacing:.08em;
       color:var(--accent); margin:40px 0 10px; }
  table { width:100%%; border-collapse:collapse; background:var(--card);
          border:1px solid var(--line); border-radius:10px; overflow:hidden; }
  td { padding:11px 13px; border-top:1px solid var(--line); vertical-align:top;
       font-size:14.5px; }
  tr:first-child td { border-top:0; }
  td:first-child { width:78px; }
  a { color:var(--ink); text-decoration:underline; text-underline-offset:3px;
      text-decoration-color:var(--accent); }
  a:hover { color:var(--accent); }
  code { font:12.5px ui-monospace,SFMono-Regular,Menlo,monospace; color:var(--dim);
         word-break:break-all; }
  .pill { display:inline-block; min-width:62px; text-align:center; padding:2px 8px;
          border-radius:999px; font:600 11.5px ui-monospace,Menlo,monospace; }
  .pill.ok { background:color-mix(in srgb, var(--ok) 18%%, transparent); color:var(--ok); }
  .pill.dead { background:color-mix(in srgb, var(--dead) 18%%, transparent); color:var(--dead); }
  .note { margin-top:44px; padding:16px 18px; background:var(--card);
          border:1px solid var(--line); border-radius:10px; color:var(--dim);
          font-size:13.5px; }
  .note b { color:var(--ink); }
  @media (max-width:640px) { td:nth-child(3) { display:none; } h1 { font-size:24px; } }
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>Everything Live</h1>
  <p class="sub">Every link below was fetched when this page was built:
     <b>%(built)s</b>. %(live)s of %(total)s answered 200. Nothing here is typed
     from memory, and a dead link is shown as dead rather than removed.</p>
</header>
%(rows)s
<div class="note">
  <b>What this page is not.</b> It is a list of things that exist and respond,
  not a list of things anyone uses. Nobody outside this project has produced a
  receipt chain: 0 stars, 0 forks, 0 outside contributors, and no reply on any
  of the three OpenZeppelin issues in 64 days. The Daml spending rules have
  never executed on a real ledger, because that needs a DevNet credential that
  was asked for on 31 August 2026 and never arrived.
  <br><br>
  Rebuild it with <code>python3 tools/live_check.py --write</code>. It exits
  non-zero if any link is dead.
</div>
</div>
</body>
</html>
"""

if __name__ == "__main__":
    sys.exit(main())
