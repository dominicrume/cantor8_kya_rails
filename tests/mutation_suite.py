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
import time
import json
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

    ("a commit goes through while a mutation run is still in progress",
     "tools/pre-commit",
     'if [ -d ".mutation-in-progress" ]; then',
     'if [ -d ".never-exists" ]; then',
     "python3 tests/mutation_guard_smoke.py"),

    ("a killed harness run against somebody else's code is never healed",
     "tools/daml_mutate.py",
     "                shutil.copy(bak, os.path.join(src, rel))   # heal",
     "                pass   # heal",
     "python3 tests/mutation_guard_smoke.py"),

    ("a mutation left in a file is no longer noticed at the commit gate",
     "tools/mutation_fingerprints.py",
     "    if replace and replace in cur and find not in cur:",
     "    if False:",
     "python3 tests/mutation_guard_smoke.py"),

    ("a refusal can be deleted from a disclosure unnoticed",
     "pkg/src/knowyouragenticai_receipts/disclose.py",
     "    if e.get(\"n\") != index:",
     "    if False:",
     "python3 tests/disclosure_smoke.py"),

    ("an entry can hide its outcome again",
     "pkg/src/knowyouragenticai_receipts/disclose.py",
     "    if not e.get(\"outcome\"):",
     "    if False:",
     "python3 tests/disclosure_smoke.py"),

    ("a refusal can be withheld while promising to show them all",
     "pkg/src/knowyouragenticai_receipts/disclose.py",
     "        if e.get(WITHHELD) and refusals_only(e):",
     "        if False:",
     "python3 tests/disclosure_smoke.py"),

    ("a shown entry can be edited after sealing",
     "pkg/src/knowyouragenticai_receipts/disclose.py",
     "    if recomputed != e.get(\"seal\"):",
     "    if False:",
     "python3 tests/disclosure_smoke.py"),

    ("the leak check stops warning what a withheld entry gives away",
     "pkg/src/knowyouragenticai_receipts/disclose.py",
     "        if len(value) < 4 or value not in shown_text:",
     "        if True:",
     "python3 tests/disclosure_smoke.py"),

    ("a chain can assert its own assurance level again",
     "pkg/src/knowyouragenticai_receipts/__init__.py",
     "    return ANCHORED if anchor_confirmed else SELF_ATTESTED",
     "    return str(receipts[0].get('ledger', SELF_ATTESTED))",
     "python3 tests/assurance_level_smoke.py"),

    ("the page stops naming what it actually established",
     "step-3-verify/verifier.html",
     "+'recomputed in this browser.<br>Assurance: <b>self-attested</b> '",
     "+'recomputed in this browser. '",
     "node tests/checker_smoke.js"),

    ("an unsubstantiated independence claim stops being flagged",
     "step-3-verify/verifier.html",
     "    if(!claims.length) return '';",
     "    return '';",
     "node tests/checker_smoke.js"),

    ("the scan stops searching for one of the two fence words",
     "tools/ecosystem_scan.py",
     'FENCES = ("assertMsg", "ensure")',
     'FENCES = ("assertMsg",)',
     "python3 tests/ecosystem_scan_smoke.py"),

    ("a file matched by both words is counted twice",
     "tools/ecosystem_scan.py",
     "    return {k: len(v) for k, v in found.items()}, None",
     "    return {k: len(v) * 2 for k, v in found.items()}, None",
     "python3 tests/ecosystem_scan_smoke.py"),

    ("the harness goes back to mutating the tests it is measuring",
     "tools/daml_mutate.py",
     '    root = os.path.join(pkg, under) if under else os.path.join(pkg, "daml")',
     '    root = os.path.join(pkg, "daml")',
     "python3 tests/assurance_smoke.py"),

    ("an async agent is recorded before it actually runs",
     "pkg/src/knowyouragenticai_receipts/guard.py",
     "        if inspect.iscoroutinefunction(fn):",
     "        if False:",
     "python3 tests/release_readiness.py"),

    ("the cap check stops being atomic",
     "pkg/src/knowyouragenticai_receipts/guard.py",
     "    with policy.lock:",
     "    if True:",
     "python3 tests/release_readiness.py"),

    ("a **kwargs tool loses its amount again",
     "pkg/src/knowyouragenticai_receipts/guard.py",
     "        if param.kind is inspect.Parameter.VAR_KEYWORD:",
     "        if False:",
     "python3 tests/release_readiness.py"),

    ("a tampered chain can be loaded and extended",
     "pkg/src/knowyouragenticai_receipts/__init__.py",
     "        ok, bad = chain.verify()\n        if not ok:\n            raise BrokenChain(\n                \"%s does not verify",
     "        ok, bad = True, 0\n        if not ok:\n            raise BrokenChain(\n                \"%s does not verify",
     "python3 tests/release_readiness.py"),

    ("the desk goes back to dropping outcomes it does not know",
     "step-5-operator/desk.html",
     "  const other = rs.filter(r => r.outcome !== 'REFUSED' && r.outcome !== 'ACCEPTED');",
     "  const other = [];",
     "python3 tests/desk_view_smoke.py"),

    ("the operator screen calls an unknown outcome 'paid' again",
     "step-5-operator/operator.html",
     "                            : r.outcome === 'ACCEPTED' ? 'paid &middot; '",
     "                            : true ? 'paid &middot; '",
     "python3 tests/desk_view_smoke.py"),

    ("a refusal is recorded but the payment goes through anyway",
     "pkg/src/knowyouragenticai_receipts/guard.py",
     "    if not allowed:\n        raise Refused(rule, receipt)",
     "    if not allowed:\n        pass",
     "python3 tests/policy_smoke.py"),

    ("the policy stops being the first entry in the chain",
     "pkg/src/knowyouragenticai_receipts/policy.py",
     '            outcome=POLICY,',
     '            outcome="NOTE",',
     "python3 tests/policy_smoke.py"),

    ("the cap stops being written into the sealed policy",
     "pkg/src/knowyouragenticai_receipts/policy.py",
     '        bits = ["cap=%s %s" % (self.cap, self.currency),',
     '        bits = ["cap=(see contract)",',
     "python3 tests/policy_smoke.py"),

    ("a self-attested refusal is labelled like a ledger one",
     "pkg/src/knowyouragenticai_receipts/guard.py",
     'SELF_ATTESTED = "self-attested (the operator\'s own process refused)"',
     'SELF_ATTESTED = "canton devnet (an independent party refused)"',
     "python3 tests/policy_smoke.py"),

    ("the policy renders as a refusal on the public page",
     "step-3-verify/verifier.html",
     "const NEUTRAL = {POLICY:1};",
     "const NEUTRAL = {};",
     "node tests/checker_smoke.js"),

    ("the action stops calling a file that exists",
     "action.yml",
     '$GITHUB_ACTION_PATH/tools/assurance_report.py',
     '$GITHUB_ACTION_PATH/tools/report.py',
     "python3 tests/action_smoke.py"),

    ("the action stops uploading the record it produced",
     "action.yml",
     "        if-no-files-found: error",
     "        if-no-files-found: ignore",
     "python3 tests/action_smoke.py"),

    ("the CI summary rounds an uncovered fence away",
     "tools/assurance_report.py",
     'bad = [r for r in receipts if r["outcome"] == "UNCOVERED"]',
     'bad = []',
     "python3 tests/action_smoke.py"),

    ("an audit drops the fences that came back covered",
     "tools/assurance.py",
     "    for row in rows:\n        stamp_one(chain, row, subject, tools)",
     "    for row in rows:\n        if row[0] != 'ok':\n            stamp_one(chain, row, subject, tools)",
     "python3 tests/assurance_smoke.py"),

    ("an uncovered fence is relabelled as covered on the way to the report",
     "tools/assurance.py",
     '    outcome = {"ok": "COVERED", "UNCOVERED": "UNCOVERED",',
     '    outcome = {"ok": "COVERED", "UNCOVERED": "COVERED",',
     "python3 tests/assurance_smoke.py"),

    ("the rule behind a verdict stops reaching the record",
     "tools/assurance.py",
     "        rule=detail[:160],",
     '        rule="see report",',
     "python3 tests/assurance_smoke.py"),

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

    ("the unverified account is recorded as having received coin",
     "docs/devnet-balances.json",
     '    "kya-unverified-1": 0.0\n  },\n  "must_hold"',
     '    "kya-unverified-1": 0.3\n  },\n  "must_hold"',
     "python3 tests/balance_lint.py"),

    ("the float stops balancing",
     "docs/devnet-balances.json",
     '    "kya-agent-1": 1.4,',
     '    "kya-agent-1": 1.9,',
     "python3 tests/balance_lint.py"),

    ("a README count drifts from the file that produces it",
     "README.md",
     "**553** requests",
     "**500** requests",
     "python3 tests/balance_lint.py"),

    ("the DevNet check goes back to a hardcoded threshold",
     "tests/devnet_check.py",
     "NEEDED = needed()",
     "NEEDED = 3.5",
     "python3 tests/balance_lint.py"),

    ("a covered fence goes back to being painted red",
     "step-3-verify/verifier.html",
     "const GOOD = {ACCEPTED:1, COVERED:1};",
     "const GOOD = {ACCEPTED:1};",
     "node tests/checker_smoke.js"),

    ("a line number goes back to being rendered as money",
     "step-3-verify/verifier.html",
     "const isMoney = r => r.currency && r.currency !== 'N/A';",
     "const isMoney = r => true;",
     "node tests/checker_smoke.js"),

    ("the verifier stops drawing where the chain broke",
     "step-3-verify/verifier.html",
     "          +drawChain(rs, bad));",
     "          );",
     "node tests/checker_smoke.js"),

    # SPEC 6b. A disclosure is the file a regulated issuer actually hands over,
    # so every check that makes it worth handing over has to be shown to be
    # load-bearing, in the browser as well as in the library.
    ("the page stops recognising a disclosure and judges it as a chain",
     "step-3-verify/verifier.html",
     "    if(looksLikeDisclosure(asDoc)){",
     "    if(false && looksLikeDisclosure(asDoc)){",
     "node tests/checker_smoke.js"),

    ("the browser stops noticing that an entry was removed",
     "step-3-verify/verifier.html",
     "    if(e.n !== at) return {ok:false, why:'entry at position '+at+' is numbered '+e.n+",
     "    if(false) return {ok:false, why:'entry at position '+at+' is numbered '+e.n+",
     "node tests/checker_smoke.js"),

    ("the browser stops re-sealing the entries it is shown",
     "step-3-verify/verifier.html",
     "      if(await sha256(stableStringify(e.body)+prev) !== e.seal)",
     "      if(false)",
     "node tests/checker_smoke.js"),

    ("the browser stops holding a disclosure to its own promise",
     "step-3-verify/verifier.html",
     "  if(doc.disclosing === 'every entry whose outcome is not ACCEPTED'){",
     "  if(false){",
     "node tests/checker_smoke.js"),

    ("the browser shows the verdict but not the refusals",
     "step-3-verify/verifier.html",
     "          +discloseCards(asDoc));",
     "          );",
     "node tests/checker_smoke.js"),

    ("a disclosure can withhold a refusal while promising to show them all",
     "pkg/src/knowyouragenticai_receipts/disclose.py",
     "    if doc.get(\"disclosing\") != EVERY_REFUSAL:",
     "    if True:",
     "python3 tests/disclosure_smoke.py"),

    ("the producer stops being told that a running total leaks the payments",
     "pkg/src/knowyouragenticai_receipts/disclose.py",
     "    out += _running_total_leak(receipts, withheld_ns, shown_text)",
     "",
     "python3 tests/disclosure_smoke.py"),

    # The refusal as a ledger fact. `Charge` aborts and leaves nothing behind;
    # `TryCharge` records and commits. Two copies of the same rules is the
    # price, and every way that can go wrong is broken here on purpose.
    #
    # The first row is the one that would cost real money: if TryCharge stops
    # checking the allow-list, it is not a recording version of Charge, it is a
    # way around it.
    ("TryCharge becomes a back door around the allow-list",
     "step-1-mandate/daml/KyaMandate.daml",
     '  | not (payee `elem` m.allowed) = Some "payee is not on the allow-list"',
     "",
     "python3 tests/daml_tests.py"),

    ("recording a refusal also moves the money",
     "step-1-mandate/daml/KyaMandate.daml",
     "            kept <- create this\n",
     "            kept <- create this with spent = spent + amount\n",
     "python3 tests/daml_tests.py"),

    ("a refused attempt stops being handed back as refused",
     "step-1-mandate/daml/KyaMandate.daml",
     "              refusal = Some refused",
     "              refusal = None",
     "python3 tests/daml_tests.py"),

    ("the recorded reason drifts from the rule that fired",
     "step-1-mandate/daml/KyaMandate.daml",
     '  | m.spent + amount > m.cap     = Some "charge would exceed the cap"',
     '  | m.spent + amount > m.cap     = Some "a routine limit"',
     "python3 tests/fence_parity.py"),

    ("the rules stop firing in the order Charge states them",
     "step-1-mandate/daml/KyaMandate.daml",
     '  | amount <= 0.0                = Some "amount must be positive"\n'
     '  | m.spent + amount > m.cap     = Some "charge would exceed the cap"',
     '  | m.spent + amount > m.cap     = Some "charge would exceed the cap"\n'
     '  | amount <= 0.0                = Some "amount must be positive"',
     "python3 tests/fence_parity.py"),

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


PROGRESS = os.path.join(ROOT, ".mutation-in-progress")


def heal(progress=None):
    """Put back whatever a killed run left mutated, BEFORE anything else.

    restore() runs in a finally, and a SIGKILL -- which is what a timeout
    delivers -- never runs a finally. Twice in one night that left a file
    mutated in the working tree: a Daml spending fence deleted, and the D1
    balances reading the opposite of the claim. The second one was committed
    and pushed, because the backups were in a random temp directory nobody
    could find and nothing at the commit gate knew a run had been interrupted.

    So backups now live in a KNOWN place inside the repository, with a
    manifest, and this runs first: if the directory exists, a previous run
    died, and its files are put back from the manifest before a single new
    mutation is made. tools/pre-commit refuses to commit while it exists.
    """
    progress = progress or PROGRESS
    manifest = os.path.join(progress, "manifest.json")
    if not os.path.isdir(progress):
        return 0
    healed = 0
    if os.path.exists(manifest):
        for rel, bak in json.load(open(manifest)).get("files", {}).items():
            if os.path.exists(bak):
                shutil.copy(bak, os.path.join(ROOT, rel))
                healed += 1
    shutil.rmtree(progress, ignore_errors=True)
    if healed:
        print("  healed %d file(s) a previous, interrupted run left mutated" % healed)
    return healed


def take_backups(rows, progress=None):
    """The only copies of these files while they are deliberately broken --
    in a known directory, with a manifest, so an interrupted run can be undone
    by heal() and cannot be committed past tools/pre-commit."""
    progress = progress or PROGRESS
    os.makedirs(progress, exist_ok=True)
    backups = {}
    for i, p in enumerate(sorted({m[1] for m in rows})):
        bak = os.path.join(progress, "%03d-%s.bak" % (i, os.path.basename(p)))
        shutil.copy(os.path.join(ROOT, p), bak)
        backups[p] = bak
    with open(os.path.join(progress, "manifest.json"), "w") as f:
        json.dump({"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "files": backups}, f, indent=2)
    return backups


def restore(backups, progress=None):
    progress = progress or PROGRESS
    for p, b in backups.items():
        shutil.copy(b, os.path.join(ROOT, p))
    # The directory going away IS the "run finished cleanly" signal.
    shutil.rmtree(progress, ignore_errors=True)
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
    heal()
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
