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

    ("a route stops rejecting infinity as an amount",
     "step-5-operator/server.py",
     "    if number != number or number in (float(\"inf\"), float(\"-inf\")):",
     "    if False:",
     "python3 tests/route_fuzz.py"),

    ("the error boundary around every route is removed",
     "step-5-operator/server.py",
     "        except Exception as e:                       # noqa: BLE001 - the boundary",
     "        except ZeroDivisionError as e:",
     "python3 tests/route_fuzz.py"),

    ("an unknown payee crashes instead of being recorded",
     "step-2-agent/agent.py",
     "        return NAMES.get(role, role)",
     "        return NAMES[role]",
     "python3 tests/operator_smoke.py"),

    ("the customer page calls a downed desk a missing deal",
     "step-5-operator/customer.html",
     "  if (res.status === 404){",
     "  if (!res.ok){",
     "node tests/frontend_offline.js"),

    ("the operator page goes silent when the desk stops answering",
     "step-5-operator/operator.html",
     "    setLink(false, 'The connection failed.');\n    return {error: 'the desk could not be reached, so nothing was sent'};",
     "    throw e;",
     "node tests/frontend_offline.js"),

    ("one malformed line ends the model's session with the wallet",
     "step-4-mcp/kya_mcp.py",
     "    if not isinstance(msg, dict):",
     "    if False:",
     "python3 tests/mcp_smoke.py"),

    ("an unusable store path becomes a traceback again",
     "step-8-store/store.py",
     "            raise Unusable(_why_unusable(path, e)) from e",
     "            raise",
     "python3 tests/store_smoke.py"),

    ("the wallet stops writing receipts through to its journal",
     "step-4-mcp/kya_mcp.py",
     "            self.store.receipt(receipt)",
     "            pass",
     "python3 tests/mcp_survives_kill.py"),

    ("a crash resets the agent's cap",
     "step-4-mcp/kya_mcp.py",
     "            self.ledger.resume(mandate)",
     "            pass",
     "python3 tests/mcp_survives_kill.py"),

    ("the desk's allow-list stops reaching the mandate",
     "step-2-agent/agent.py",
     '                  "allowed": list(ALLOWED if allowed is None else allowed),',
     '                  "allowed": list(ALLOWED),',
     "python3 tests/desk_config_smoke.py"),

    ("a boolean is accepted as a spending cap",
     "step-9-desk/desk_config.py",
     "    if isinstance(value, bool) and bool not in kinds:",
     "    if False:",
     "python3 tests/desk_config_smoke.py"),

    ("the customer page stops fitting a phone",
     "step-5-operator/customer.html",
     '<meta name="viewport" content="width=device-width, initial-scale=1">',
     "",
     "python3 tests/a11y_lint.py"),

    ("the payout button loses its keyboard focus ring",
     "step-5-operator/operator.html",
     "  a:focus-visible, button:focus-visible, [tabindex]:focus-visible,",
     "  a:no-such-state, [tabindex]:no-such-state,",
     "python3 tests/a11y_lint.py"),

    ("the payee list stops coming from the desk's settings",
     "step-5-operator/server.py",
     '                "recipients": self.payees(),',
     '                "recipients": [{"key": k, "name": k} for k in ("customer", "partner")],',
     "python3 tests/desk_view_smoke.py"),

    ("the operating view stops showing why something was refused",
     "step-5-operator/desk.html",
     "    + (showRule ? '<div class=\"rule\">' + esc(r.rule) + '</div>' : '')",
     "    + ''",
     "node tests/frontend_offline.js"),

    ("the verifier's text goes invisible against its own background",
     "step-3-verify/verifier.html",
     "color:var(--page-ink); min-height:100vh; }",
     "color:var(--ink); min-height:100vh; }",
     "python3 tests/contrast_lint.py"),

    ("the bundled desk loses its settings and its journal",
     "step-9-desk/desk_config.py",
     '    for candidate in (os.path.join(os.getcwd(), "desk.json"), DEFAULT_PATH):',
     "    for candidate in (DEFAULT_PATH,):",
     "python3 tests/bundle_smoke.py"),

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
    # Every generated artefact is built from a file that was just mutated, so
    # rebuild them all or the next run compares against a broken one -- and,
    # worse, a stale one gets committed.
    #
    # dist/kya-desk.py was missing from this list and was committed built from
    # MUTATED source: the mutation that deletes the settings loader's
    # working-directory lookup ran, bundle_smoke rebuilt the bundle to test it,
    # the source was restored, and the bundle was not. Somebody downloaded that
    # bundle, put desk.json beside it, and was told "NO desk.json" with the file
    # in plain sight. The tool that hunts this exact failure shipped it.
    for mode in ([], ["--fragment"], ["--pages"]):
        subprocess.run(["python3", "step-3-verify/build-standalone.py"] + mode,  # nosec B603 B607
                       cwd=ROOT, capture_output=True)
    subprocess.run(["python3", "tools/build-desk.py"],  # nosec B603 B607 - literal argv
                   cwd=ROOT, capture_output=True)


def selected(only):
    """The rows a filter names, or a refusal.

    A filter that matches nothing used to print "Breaking 0 real things" and
    then "every one of these breaks something a suite notices" -- true, and
    worthless: a mistyped filter reported success. Returning None makes it an
    exit code instead.
    """
    rows = [m for m in MUTATIONS if not only or only in m[0] or only in m[1]]
    if rows:
        return rows
    print("No mutation matches %r. Nothing was tested." % only)
    print("Names available:")
    for m in MUTATIONS:
        print("  -", m[0])
    return None


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    rows = selected(only)
    if rows is None:
        return 1
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
