#!/usr/bin/env python3
"""The operating view, exercised as a screen an operator has to act from.

There was a page called "dashboard" before this one and it was a build report:
thirty rows of PASS, answering "did the suites pass", which is a question for
whoever changes the code. Nothing to click, nothing to decide, and not one
number about money. It has been renamed to what it is.

/desk answers a different question -- what do I do next -- so this checks the
things an operator needs before touching real money:

  the float is on the page, and it is the desk's real cap
  the refusals are shown WITH the rule that produced them
  the payee list is the one from desk.json, not a hardcoded pair
  a mocked ledger and an unsaved journal are impossible to miss

Run: python3 tests/desk_view_smoke.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SERVER = os.path.join(ROOT, "step-5-operator", "server.py")
PORT = "8477"
BASE = "http://127.0.0.1:" + PORT

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def get(path):
    if not path.startswith("/"):
        raise ValueError(path)
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return r.status, r.read().decode()


def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def settings():
    """A desk.json with a counterparty deliberately turned OFF, so the payee
    list has something to get wrong."""
    cfg = {
        "desk": {"name": "VOREM Desk", "operator": "Rume Dominic"},
        "money": {"cap": 5.0, "period_limit": 2.0, "period_seconds": 86400,
                  "rate": 1250.0, "band": [1000.0, 1500.0]},
        "counterparties": [
            {"id": "customer", "name": "Chidi Okafor",
             "account": "GTB 0123456789", "allowed": True},
            {"id": "partner", "name": "Settlement partner",
             "account": "UBA 2233445566", "allowed": False},
        ],
    }
    path = os.path.join(tempfile.mkdtemp(), "desk.json")
    open(path, "w").write(json.dumps(cfg))
    return path


def page_checks(page):
    print("\nthe page an operator works from")
    check("<title>Desk" in page, "/desk is served and is the desk view")
    for what, needle in (
            ("the float", 'id="remaining"'),
            ("a payout form", 'id="send"'),
            ("a payee list", 'id="payee"'),
            ("the refusals", 'id="refused"'),
            ("what was paid", 'id="paid"'),
            ("a revoke control", 'id="revoke"')):
        check(needle in page, "it has %s" % what)
    check('aria-live' in page, "and regions that change announce themselves")
    # A build report is not an operating view, and the old page claimed to be
    # one. Check what the page RENDERS, not what its comments say -- the first
    # version of this check failed on the source comment explaining that this
    # page is deliberately not a build report.
    visible = re.sub(r"<!--.*?-->", "", page, flags=re.S)
    visible = re.sub(r"/\*.*?\*/", "", visible, flags=re.S)
    check("PASS" not in visible and "suites green" not in visible,
          "it is NOT a list of passing tests")


def shows_the_desk(state):
    """The screen is this desk's, not a demo's."""
    check(state["desk"]["name"] == "VOREM Desk",
          "the desk is named from desk.json, not hardcoded")
    keys = [r["key"] for r in state["recipients"]]
    check(keys == ["customer"],
          "the payee list is the ALLOW-LIST from settings, not a fixed pair (%s)" % keys)
    check(state["recipients"][0]["name"] == "Chidi Okafor",
          "and shows the counterparty's real name, not the demo role")
    check(abs(state["cap"] - 5.0) < 1e-9 and abs(state["remaining"] - 4.0) < 1e-9,
          "the float is the desk's real cap and what is left (%.1f of %.1f)"
          % (state["remaining"], state["cap"]))


def shows_the_refusals(state):
    """The half of the record that exists nowhere else."""
    refused = [r for r in state["receipts"] if r["outcome"] == "REFUSED"]
    check(len(refused) == 2, "both refusals are on the record (%d)" % len(refused))
    check(all(r.get("rule") for r in refused),
          "and every one carries the rule that produced it")
    check(any("allow-list" in r["rule"] for r in refused),
          "including the payee nobody has heard of")
    check(any("cap" in r["rule"] for r in refused), "and the one over the cap")
    check(all(r.get("seal") for r in refused),
          "each sealed, so a refusal cannot be quietly removed later")


def data_checks(state):
    print("\nwhat it is showing")
    shows_the_desk(state)
    shows_the_refusals(state)

    print("\nwhat must be impossible to miss")
    check(state["storage"]["mode"] == "EPHEMERAL",
          "the desk reports that nothing is being saved")
    check("MOCKED" in state["ledger"], "and that this is the mock rail")


def main():
    cfg = settings()
    env = dict(os.environ, KYA_PORT=PORT, KYA_DESK=cfg, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.Popen([sys.executable, SERVER, "--ephemeral"], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for _ in range(40):
        try:
            get("/api/state")
            break
        except Exception:
            time.sleep(0.25)
    try:
        post("/api/open", {"cap": 5.0, "period_limit": 2.0, "period_seconds": 86400})
        post("/api/request", {"amount": 1.0, "payee": "customer", "what": "invoice 41"})
        post("/api/request", {"amount": 9.0, "payee": "customer", "what": "over the cap"})
        post("/api/request", {"amount": 1.0, "payee": "Fraudster Ltd", "what": "urgent"})

        status, page = get("/desk")
        check(status == 200, "GET /desk answers 200")
        page_checks(page)
        data_checks(json.loads(get("/api/state")[1]))
    finally:
        proc.terminate()
        proc.wait(timeout=10)

    print()
    if fails:
        print("DESK VIEW FAILED - %d:" % len(fails))
        for f in fails:
            print("  -", f)
        return 1
    print("the operating view shows the float, the refusals and their rules, and")
    print("the counterparties this desk was actually configured with.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
