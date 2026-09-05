#!/usr/bin/env python3
"""Break the thing, and require the suite that covers it to go red.

Two independent audits found fifteen assertions in this repository that could
not fail -- checks that passed with authentication deleted, with the QR
encoding a payment request nobody agreed to, with the audit trail never
written, with the verifier unable to detect a tampered chain. Every one was
found the same way: break the subject by hand and see whether anything
noticed. Nothing did.

So "all suites green" meant "the tests agree with the code", which is a much
weaker claim than it reads as, and it is the exact failure this whole project
argues against everywhere else.

tests/mutation.py does this for the Daml fences and tests/mutation_py.py for
the refusals at the edges. Neither covers the pages, the library, the server,
or the test suites themselves -- and all fifteen defects were in that gap.
This closes it.

Each row below is a REAL defect. Apply it, run the suite that claims to cover
it, and that suite must fail. A row that stays green is a suite that would not
notice the defect in production.

    python3 tests/mutation_suite.py            every mutation
    python3 tests/mutation_suite.py verifier   only those matching a word

Slow: one suite run per mutation. That is the price of knowing.
"""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (label, file, find, replace, suite that must go red)
MUTATIONS = [
    ("the page cannot detect a tampered chain",
     "step-3-verify/verifier.html",
     "async function badFrom(rs){ let prev='GENESIS';",
     "async function badFrom(rs){ return 0; } async function unusedBadFrom(rs){ let prev='GENESIS';",
     "node tests/checker_smoke.js"),

    ("the page stops escaping non-ASCII",
     "step-3-verify/verifier.html",
     "return escapeNonAscii(JSON.stringify(o));",
     "return JSON.stringify(o);",
     "node tests/conformance.js"),

    ("the QR encodes a payment request nobody agreed to",
     "step-5-operator/customer.html",
     "    q.addData(text);",
     "    text = 'tron:' + text + '?amount=' + 999;\n    q.addData(text);",
     "python3 tests/cycle_smoke.py"),

    ("the deposit address disappears from the customer page",
     "step-5-operator/customer.html",
     "'<div class=\"val\">' + esc(d.depositAddress) + '</div>' +",
     "'' +",
     "python3 tests/cycle_smoke.py"),

    ("the WhatsApp webhook stops checking signatures",
     "step-7-providers/meta.py",
     "            self._authenticate(headers, raw)",
     "            pass",
     "python3 tests/meta_smoke.py"),

    ("the deposit webhook stops checking the IP allowlist",
     "step-7-providers/breet.py",
     "        if self.require_ip and src_ip not in self.allow_ips:",
     "        if False:",
     "python3 tests/breet_wire_smoke.py"),

    ("the audit trail is never written",
     "step-2-agent/kya_chain.py",
     "        self.receipts.append(r)",
     "        pass",
     "python3 tests/mcp_smoke.py"),

    ("the desk stops persisting anything",
     "step-5-operator/server.py",
     "        if self.store is None:\n            return\n        for entry in self.transcript",
     "        if True:\n            return\n        for entry in self.transcript",
     "python3 tests/store_smoke.py"),

    ("the journal stops refusing an edited history",
     "step-8-store/store.py",
     "        if not ok and strict:",
     "        if False:",
     "python3 tests/store_smoke.py"),

    ("the model is offered a tool that raises its own cap",
     "step-4-mcp/kya_mcp.py",
     '{"name": "open_mandate"',
     '{"name": "increase_spending_limit", "description": "Raise the cap",'
     ' "inputSchema": {"type": "object", "properties": {}}},\n    {"name": "open_mandate"',
     "python3 tests/mcp_smoke.py"),

    ("an unescaped template literal reaches the DOM",
     "step-5-operator/operator.html",
     "$('ledger').textContent = s.ledger;",
     "$('ledger').innerHTML = `<i>${s.ledger}</i>`;",
     "python3 tests/xss_lint.py"),

    ("the bot stops accepting an amount with its unit",
     "step-6-whatsapp/bot.py",
     r"(\d+(?:\.\d+)?)\s*(?:[a-z]{2,5})?",
     r"(\d+(?:\.\d+)?)",
     "python3 tests/bot_smoke.py"),

    ("the package silently defaults the currency again",
     "pkg/src/knowyouragenticai_receipts/__init__.py",
     "    def stamp(self, what: str, amount: str, currency: str, payee: str,",
     "    def stamp(self, what: str, amount: str, payee: str, currency: str = \"CC\",",
     "python3 tests/package_smoke.py"),

    ("a Daml spending fence is deleted",
     "step-1-mandate/daml/KyaMandate.daml",
     '        assertMsg "charge would exceed the cap" (spent + amount <= cap)',
     "",
     "python3 tests/fence_lint.py"),
]


def run(suite):
    """(went_red, first_failing_line)."""
    r = subprocess.run(suite.split(), cwd=ROOT, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    out = r.stdout + r.stderr
    first = next((l.strip() for l in out.splitlines()
                  if l.strip().startswith("FAIL") or "  FAIL" in l), "")
    return r.returncode != 0, first[:74]


def apply_one(path, find, replace):
    """False if the text is not there -- a mutation that does not apply proves
    nothing, and silently counting it as covered is how this fails quietly."""
    full = os.path.join(ROOT, path)
    src = open(full).read()
    if find not in src:
        return False
    open(full, "w").write(src.replace(find, replace, 1))
    return True


def check_one(row, backups):
    label, path, find, replace, suite = row
    for p, b in backups.items():
        shutil.copy(b, os.path.join(ROOT, p))
    if not apply_one(path, find, replace):
        print("  STALE %-52s (text not found in %s)" % (label[:52], path))
        return "stale"
    red, detail = run(suite)
    print("  %-5s %-52s %s" % ("ok" if red else "BLIND", label[:52], suite))
    if red and detail:
        print("        %s" % detail)
    return "ok" if red else "blind"


def take_backups(rows):
    """The only copies of these files while they are deliberately broken."""
    backups = {}
    for p in sorted({m[1] for m in rows}):
        fd, tmp = tempfile.mkstemp(suffix=os.path.basename(p))
        os.close(fd)
        shutil.copy(os.path.join(ROOT, p), tmp)
        backups[p] = tmp
    return backups


def restore(backups):
    for p, b in backups.items():
        shutil.copy(b, os.path.join(ROOT, p))
        os.unlink(b)
    # The generated pages are built from a file that was just mutated, so
    # rebuild them or the next run compares against a broken artefact.
    for mode in ([], ["--fragment"], ["--pages"]):
        subprocess.run(["python3", "step-3-verify/build-standalone.py"] + mode,
                       cwd=ROOT, capture_output=True)


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    rows = [m for m in MUTATIONS if not only or only in m[0] or only in m[1]]
    print("Breaking %d real things, and requiring the suite to notice.\n" % len(rows))
    backups = take_backups(rows)
    results = []
    try:
        for row in rows:
            results.append(check_one(row, backups))
    finally:
        restore(backups)
    return report(rows, results)


def _listing(rows, results, kind):
    return [r[0] for r, v in zip(rows, results) if v == kind]


def report(rows, results):
    blind, stale = _listing(rows, results, "blind"), _listing(rows, results, "stale")
    print()
    if stale:
        print("%d mutation(s) no longer apply -- the code moved and this file "
              "did not, so they proved nothing:" % len(stale))
        for label in stale:
            print("  -", label)
        print()
    if blind:
        print("%d defect(s) NO SUITE NOTICED:" % len(blind))
        for label in blind:
            print("  -", label)
        print("\nEach is something that could ship while every test stayed green.")
    if blind or stale:
        return 1
    print("every one of these breaks something a suite notices.")
    print("that is what makes 'all suites green' worth saying.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
