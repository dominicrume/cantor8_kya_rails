#!/usr/bin/env python3
"""Run everything, and write down what actually held.

There was no single place to look. Thirty suites, a Daml package, a mutation
harness and three implementations, and the only way to know the state of any of
it was to run commands one at a time and remember the answers. That is fine for
the person who wrote them and useless for everybody else -- including the person
who wrote them, three weeks later.

This runs each suite, records the result, and writes a page. It does not cache
and it does not read a stored answer: every number on the page came from a
command that ran on this machine in the last few minutes, and the page says when.

    python3 tools/dashboard.py            everything, including the slow parts
    python3 tools/dashboard.py --fast     skip mutation testing (~2 min faster)
    python3 tools/dashboard.py --open     write it and open it

Output: docs/build.html. It is a BUILD REPORT, not a dashboard -- it answers
"did the suites pass". The operating view is /desk on a running desk, which is
where the float, the refusals and the payout form live.
"""
import html
import json
import os
import re
import shlex
import subprocess  # nosec B404 - a harness runs commands; that is what it is
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "build.html")

# (command, group, what a green result actually means)
SUITES = [
    ("python3 tests/conformance.py", "The format",
     "the Python implementation agrees with all 16 conformance vectors"),
    ("node tests/conformance.js", "The format",
     "the JavaScript implementation agrees, byte for byte, with the Python one"),
    ("cd impl/go && go run .", "The format",
     "a third implementation, in Go, agrees with both"),
    ("python3 tests/conformance_any.py -- python3 impl/pipe/reference.py", "The format",
     "any executable can be graded through a pipe, in any language"),

    ("python3 tests/fence_lint.py", "The ledger",
     "every spending fence is present in the Daml"),
    ("python3 tests/anchor_smoke.py", "The ledger",
     "a forged chain verifies internally and still answers NOT ANCHORED"),

    ("python3 tests/mcp_smoke.py", "The agent",
     "the model cannot overspend, redirect, or outlive a revoke -- and cannot end its own session"),
    ("python3 tests/mcp_survives_kill.py", "The agent",
     "SIGKILL loses no receipts, and buys the agent no cap"),
    ("python3 tests/bot_smoke.py", "The agent",
     "the WhatsApp bot reads an amount the way a person writes one"),

    ("python3 tests/bundle_smoke.py", "The desk",
     "the whole desk runs from one file, with no repository and nothing installed"),
    ("python3 tests/desk_view_smoke.py", "The desk",
     "the operating view shows the float, the refusals and the rule for each"),
    ("python3 tests/desk_config_smoke.py", "The desk",
     "settings are refused when wrong, and enforced by the ledger when right"),
    ("python3 tests/operator_smoke.py", "The desk",
     "every refusal the desk answers is also on its record"),
    ("python3 tests/cycle_smoke.py", "The desk",
     "the deal cycle holds at every join a real desk lost money on"),
    ("python3 tests/store_smoke.py", "The desk",
     "a quote outlives the process, and an edited journal refuses to load"),
    ("python3 tests/route_fuzz.py", "The desk",
     "553 malformed requests: nothing dropped, nothing 500s, every 400 names its field"),

    ("python3 tests/assurance_smoke.py", "The desk",
     "an audit's findings are sealed, so softening one breaks the client's own check"),

    ("node tests/checker_smoke.js", "The page",
     "drop a file and it is checked -- and a non-chain is never called tampered"),
    ("node tests/frontend_offline.js", "The page",
     "neither screen goes silent, or tells the reader something untrue about their money"),
    ("node tests/origin_smoke.js", "The page",
     "the page says where a chain came from, not only that it holds"),
    ("python3 tests/contrast_lint.py", "The page",
     "no text anywhere is invisible against its own background"),
    ("python3 tests/a11y_lint.py", "The page",
     "every page is a document, readable on a phone, and usable without a mouse"),
    ("python3 tests/standalone_smoke.py", "The page",
     "the standalone build has not drifted from the source page"),

    ("python3 tests/meta_smoke.py", "The doors",
     "the WhatsApp webhook refuses unsigned, wrongly signed and replayed calls"),
    ("python3 tests/meta_wire_smoke.py", "The doors",
     "and refuses them over a real socket, not just in a unit test"),
    ("python3 tests/breet_smoke.py", "The doors",
     "the deposit webhook checks its secret and its IP allowlist"),
    ("python3 tests/breet_wire_smoke.py", "The doors",
     "including the X-Forwarded-For spoof that defeats a naive allowlist"),

    ("python3 tests/security_lint.py", "The rules",
     "no bandit finding in production code"),
    ("python3 tests/complexity_lint.py", "The rules",
     "every function is under the ceiling, or says in writing why not"),
    ("python3 tests/deadcode_lint.py", "The rules",
     "nothing unreachable, and no import silently overwritten"),
    ("python3 tests/xss_lint.py", "The rules",
     "every innerHTML interpolation goes through esc()"),
    ("python3 tests/privacy_matrix.py --check", "The rules",
     "who signs, observes and is excluded is documented for every contract"),
        ("python3 tests/balance_lint.py", "The page",
     "the float adds up, and every number the README shows a judge is still true"),

("python3 tests/readme_citations.py", "The rules",
     "every line of Daml the README shows a judge is still that line"),
    ("python3 tests/devhub_entry_check.py", "The rules",
     "the Developer Hub listing passes every rule the Foundation publishes"),
    ("python3 tests/package_smoke.py", "The rules",
     "the installable package refuses what it should refuse"),

    ("python3 tests/mutation_py.py", "The tests, tested",
     "every refusal at the edges is covered by a named test"),
    ("python3 tests/mutation_suite.py", "The tests, tested",
     "23 real defects introduced on purpose; every one makes its suite go red"),
]

SLOW = ("mutation_suite", "route_fuzz", "mcp_survives_kill")


def split(cmd):
    """(argv, cwd). A leading "cd DIR && " becomes a working directory rather
    than a shell. Passing these strings to a shell would work and would still
    be wrong: the moment one of these commands takes an argument from anywhere
    but this file, shell=True is a hole, and nobody remembers to fix it then."""
    cwd = ROOT
    if cmd.startswith("cd "):
        where, _, cmd = cmd.partition(" && ")
        cwd = os.path.join(ROOT, where[3:].strip())
    return shlex.split(cmd), cwd


def run(cmd):
    """(ok, seconds, output). Never raises -- a suite that explodes is a result."""
    argv, cwd = split(cmd)
    start = time.time()
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True,  # nosec B603 - argv from this file
                           text=True, timeout=600,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        return p.returncode == 0, time.time() - start, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return False, time.time() - start, "timed out after 600s"
    except OSError as e:
        return False, time.time() - start, "could not start: %s" % e


def headline(output):
    """The one number worth putting on a card, if the suite printed one."""
    for pattern in (r"(\d+) dropped, (\d+) server errors",
                    r"(\d+ of \d+)", r"(\d+/\d+)",
                    r"(\d+) answered, (\d+) recorded"):
        m = re.search(pattern, output)
        if m:
            return " ".join(m.groups())
    passes = output.count("PASS ")
    return "%d checks" % passes if passes else ""


def daml_facts():
    """The ledger numbers, read from a real run rather than remembered."""
    test_dir = os.path.join(ROOT, "step-1-mandate", "test")
    if not os.path.isdir(test_dir):
        return None
    try:
        p = subprocess.run(  # nosec B603 B607 - argv is literal; daml is on PATH
            ["daml", "test", "--all", "--show-coverage", "--no-legacy-assistant-warning"],
            cwd=test_dir, capture_output=True, text=True, timeout=1800)
    except (OSError, subprocess.TimeoutExpired):
        return None                    # no Daml toolchain here; say so, do not guess
    out = p.stdout + p.stderr
    scripts = out.count(": ok,")
    m = re.search(r"(\d+) \(\s*([\d.]+)%\) exercised in any tests", out)
    return {"scripts": scripts, "failed": len(re.findall(r": (failed|error)", out)),
            "exercised": m.group(1) if m else "?", "percent": m.group(2) if m else "?",
            "ok": p.returncode == 0 and scripts > 0}


def versions():
    """What is built here, which is not the same as what is vetted on DevNet."""
    out = {"built": "?", "sdk": "?"}
    try:
        for line in open(os.path.join(ROOT, "step-1-mandate", "daml.yaml")):
            if line.startswith("version:"):
                out["built"] = line.split(":", 1)[1].strip()
            if line.startswith("sdk-version:"):
                out["sdk"] = line.split(":", 1)[1].strip()
    except OSError:
        pass
    return out


CSS = """
:root{--bg:#0e1114;--card:#161b21;--line:#242c34;--ink:#e6eaee;--dim:#95a0ab;
      --ok:#4ea87e;--bad:#d4574c;--warn:#c99a3e;--accent:#6ea8d8}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
     font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"Helvetica Neue",sans-serif}
.wrap{max-width:64rem;margin:0 auto;padding:2.5rem 1.1rem 5rem}
h1{font-size:1.9rem;margin:0 0 .35rem;letter-spacing:-.02em}
.sub{color:var(--dim);margin:0 0 2rem}
.top{display:grid;gap:1px;background:var(--line);border:1px solid var(--line);
     border-radius:8px;overflow:hidden;grid-template-columns:repeat(auto-fit,minmax(9.5rem,1fr));
     margin-bottom:2rem}
.top div{background:var(--card);padding:.95rem 1rem}
.big{font-size:1.7rem;font-weight:650;letter-spacing:-.02em;
     font-variant-numeric:tabular-nums;line-height:1.1}
.lbl{color:var(--dim);font-size:12px;text-transform:uppercase;letter-spacing:.09em;
     margin-top:.25rem}
h2{font-size:.78rem;text-transform:uppercase;letter-spacing:.13em;color:var(--dim);
   margin:2rem 0 .7rem;font-weight:600}
table{width:100%;border-collapse:collapse;background:var(--card);
      border:1px solid var(--line);border-radius:8px;overflow:hidden}
td{padding:.6rem .85rem;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
td.s{width:1%;white-space:nowrap;font-weight:650;font-size:12px;letter-spacing:.06em}
td.n{width:1%;white-space:nowrap;color:var(--dim);font-size:12.5px;
     font-variant-numeric:tabular-nums;text-align:right}
td.c{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;
     color:var(--accent);white-space:nowrap;width:1%}
.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}
.why{color:var(--dim);font-size:13.5px}
.note{background:var(--card);border:1px solid var(--line);border-left:2px solid var(--warn);
      border-radius:6px;padding:.85rem 1rem;color:var(--dim);font-size:13.5px;margin:1.4rem 0}
.note b{color:var(--ink)}
a{color:var(--accent)}
a:focus-visible,button:focus-visible{outline:2px solid var(--accent);outline-offset:2px;
  border-radius:3px}
@media (prefers-reduced-motion: reduce){
  *,*::before,*::after{animation-duration:.001ms !important;
    transition-duration:.001ms !important;scroll-behavior:auto !important}
}
footer{color:var(--dim);font-size:12.5px;margin-top:2.5rem;line-height:1.7}
pre{background:var(--card);border:1px solid var(--line);border-radius:6px;
    padding:.7rem .9rem;overflow-x:auto;font-size:12.5px;color:var(--dim);margin:.5rem 0 0}
"""


def rows(results):
    """One table per group, in the order the groups first appear."""
    out, seen = [], []
    for cmd, group, _why, _ok, _secs, _head in results:
        if group not in seen:
            seen.append(group)
    for group in seen:
        out.append("<h2>%s</h2><table>" % html.escape(group))
        for cmd, g, why, ok, secs, head in results:
            if g != group:
                continue
            out.append(
                '<tr><td class="s %s">%s</td><td class="c">%s</td>'
                '<td class="why">%s</td><td class="n">%s</td><td class="n">%.1fs</td></tr>'
                % ("ok" if ok else "bad", "PASS" if ok else "FAIL",
                   html.escape(cmd.replace("python3 tests/", "").replace("node tests/", "")),
                   html.escape(why), html.escape(head), secs))
        out.append("</table>")
    return "\n".join(out)


def cards(results, daml, vers):
    """The five numbers worth seeing before reading a single row."""
    green, total = sum(1 for r in results if r[3]), len(results)
    dim = "<span style='color:var(--dim)'>"
    daml_ok = "ok" if daml and daml["ok"] else "warn"
    return [
        ("%d%s/%d</span>" % (green, dim, total), "suites green",
         "ok" if green == total else "bad"),
        ("%d%s/92</span>" % (daml["scripts"] if daml else 0, dim),
         "daml attack scripts", daml_ok),
        ((daml["exercised"] + "/42") if daml else "not run", "choices exercised", daml_ok),
        (vers["built"], "package built", "ok"),
        (vers["sdk"], "daml sdk", "ok"),
    ]


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>KYA Rails - build report</title><style>%s</style></head><body>
<main class="wrap">
<h1>KYA Rails: build report</h1>
<p class="sub">This is a build report, not an operating view &mdash; it answers
"did the suites pass", which is a question for whoever changes the code. The
screen an operator actually works from is <b>/desk</b> on a running desk: the
float, what was refused and why, and the payout form.<br><br>
Every number below came from a command that ran on this machine at
%s. Nothing here is cached, and nothing is remembered from a previous run.</p>
<div class="top">%s</div>
<div class="note"><b>Built is not the same as deployed.</b> This repository builds
<b>%s</b> on SDK <b>%s</b>. What is vetted on Cantor8 DevNet is <b>1.1.0</b>, built on
3.4.10 — a different package id, because a different compiler produces a different
fingerprint. 1.1.1 is tested but not yet uploaded, and this line will say so until
it is.</div>
%s
<h2>Reproduce any of it</h2>
<pre>git clone https://github.com/dominicrume/cantor8_kya_rails
cd cantor8_kya_rails
python3 tools/dashboard.py          # regenerates this page from scratch
cd step-1-mandate/test &amp;&amp; daml test # the 92 attack scripts</pre>
<footer>
<b>%s</b> &middot; whole run took %.0f seconds &middot; generated %s<br>
Live verifier: <a href="./">dominicrume.github.io/cantor8_kya_rails</a> &middot;
Source: <a href="https://github.com/dominicrume/cantor8_kya_rails">github.com/dominicrume/cantor8_kya_rails</a><br>
A green row means the named command exited zero. It does not mean the thing is
correct — it means a test that is capable of failing did not fail. Which tests are
capable of failing is what the last group measures.
</footer></main></body></html>"""


def render(results, daml, vers, seconds):
    green = sum(1 for r in results if r[3])
    allok = green == len(results) and (daml is None or daml["ok"])
    top = "".join('<div><div class="big %s">%s</div><div class="lbl">%s</div></div>'
                  % (cls, val, lbl) for val, lbl, cls in cards(results, daml, vers))
    stamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    return PAGE % (CSS, stamp, top, vers["built"], vers["sdk"], rows(results),
                   "ALL GREEN" if allok else "SOMETHING IS RED", seconds, stamp)


def run_all(suites):
    """Every suite, in order, printing as it goes so a slow run is not silent."""
    results = []
    for cmd, group, why in suites:
        ok, secs, out = run(cmd)
        print("  %-5s %-52s %.1fs" % ("ok" if ok else "FAIL", cmd[:52], secs))
        results.append((cmd, group, why, ok, secs, headline(out)))
    return results


def chosen(fast):
    if not fast:
        return SUITES
    return [s for s in SUITES if not any(k in s[0] for k in SLOW)]


def main(argv):
    fast = "--fast" in argv
    suites = chosen(fast)
    print("running %d suites%s" % (len(suites), " (--fast)" if fast else ""))
    started = time.time()
    results = run_all(suites)

    print("  reading the ledger...")
    daml = None if fast else daml_facts()
    open(OUT, "w").write(render(results, daml, versions(), time.time() - started))

    green = sum(1 for r in results if r[3])
    print("\n%d/%d green -> %s" % (green, len(results), os.path.relpath(OUT, ROOT)))
    if "--open" in argv:
        subprocess.run(["open", OUT], check=False)  # nosec B603 B607 - literal argv
    return 0 if green == len(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
