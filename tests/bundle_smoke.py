#!/usr/bin/env python3
"""The single-file desk, run the way a stranger would run it.

The verifier already clears the bar this file exists to enforce: drop a file on
a page, no install, no account, no terminal. The desk did not. Every
conversation about trying it ended with "clone the repo, work out which file,
run Python", and most people stop at the first clause.

So dist/kya-desk.py is built, copied to a directory that has nothing to do with
this repository, and started there. If it needs the repo, it fails here.

Two bugs this caught on the first run, both invisible from inside the repo:

  the journal was written into the temp folder the pages are unpacked to, so
  the audit trail vanished with the process;

  desk.json sitting right beside the bundle was ignored, because the settings
  loader resolved a path relative to its own module -- which in a bundle means
  nothing. It printed "Unconfigured desk" with the file in plain sight.

Run: python3 tests/bundle_smoke.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUNDLE = os.path.join(ROOT, "dist", "kya-desk.py")
PORT = "8481"
BASE = "http://127.0.0.1:" + PORT

fails = []


def check(ok, what):
    print("  " + ("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def get(path):
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


def build():
    """Rebuild, and require the committed artefact to have been current.

    dist/kya-desk.py is tracked, so a stale one is a stale one shipped. It
    happened: mutation_suite mutates a source, rebuilds the bundle to test the
    mutation, restores the source and did NOT rebuild -- so the committed
    bundle was built from code with a fence deleted. The download worked, found
    no desk.json sitting beside it, and said so.

    Comparing the hash before and after a rebuild is the whole guard.
    """
    was = digest(BUNDLE)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build-desk.py")],
                       capture_output=True, text=True, cwd=ROOT)
    check(r.returncode == 0, "tools/build-desk.py builds the bundle")
    check(os.path.exists(BUNDLE), "dist/kya-desk.py exists")
    check(was is None or was == digest(BUNDLE),
          "the committed bundle was already current -- rebuilding it changed nothing")


def digest(path):
    if not os.path.exists(path):
        return None
    import hashlib
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def elsewhere():
    """A directory containing the bundle and nothing else."""
    d = tempfile.mkdtemp(prefix="kya-elsewhere-")
    shutil.copy(BUNDLE, os.path.join(d, "kya-desk.py"))
    return d


def offline_checks(d):
    print("\nbefore it is even started")
    r = subprocess.run([sys.executable, "kya-desk.py", "--example"],
                       cwd=d, capture_output=True, text=True)
    check(r.returncode == 0, "--example prints a settings file")
    try:
        cfg = json.loads(r.stdout)
        check("money" in cfg and "counterparties" in cfg,
              "and it is valid JSON with the fields the desk needs")
    except ValueError:
        check(False, "--example output is valid JSON")
        cfg = None
    r = subprocess.run([sys.executable, "kya-desk.py", "--sources"],
                       cwd=d, capture_output=True, text=True)
    check(r.returncode == 0 and "def " in r.stdout,
          "--sources prints the code inside it, so the file is still readable")
    check(len(r.stdout) > 50000,
          "and prints all of it, not a summary (%d chars)" % len(r.stdout))
    return cfg


def running_checks(d):
    print("\nrunning, in a directory with two files in it")
    check(sorted(os.listdir(d)) == ["desk.json", "kya-desk.py"],
          "nothing but the bundle and its settings: %s" % sorted(os.listdir(d)))

    env = dict(os.environ, KYA_PORT=PORT, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.Popen([sys.executable, "kya-desk.py"], cwd=d, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        for _ in range(60):
            try:
                get("/api/state")
                break
            except Exception:
                time.sleep(0.25)
        serve(d)
    finally:
        proc.terminate()
        proc.wait(timeout=10)
    # The journal must survive the process, in the operator's directory and not
    # in the temp folder the pages were unpacked to.
    check(os.path.exists(os.path.join(d, "kya-desk.db")),
          "the journal is written where the operator is standing, and outlives the run")


def serve(d):
    for path, what in (("/desk", "the operating view"),
                       ("/c", "the customer page"),
                       ("/", "the operator screen")):
        code, _ = get(path)
        check(code == 200, "%s is served (%s)" % (what, path))

    state = json.loads(get("/api/state")[1])
    check(state["desk"]["name"] == "VOREM Desk",
          "it reads desk.json from the directory it was started in, not the repo")
    check([r["key"] for r in state["recipients"]] == ["customer", "partner"],
          "and takes its allow-list from there")

    post("/api/open", {"cap": 5.0})
    ok = post("/api/request", {"amount": 1.0, "payee": "customer", "what": "invoice 41"})
    check(ok.get("outcome") == "ACCEPTED", "a payment inside the mandate is accepted")
    no = post("/api/request", {"amount": 1.0, "payee": "Nobody Ltd", "what": "urgent"})
    check(no.get("outcome") == "REFUSED" and "allow-list" in no.get("rule", ""),
          "and an unknown payee is refused BY THE LEDGER, from a single file")
    check("receipt" in no and no["receipt"]["seal"],
          "with the refusal sealed into the chain")


def main():
    print("the whole desk, in one file, run from somewhere else entirely")
    build()
    if fails:
        return report()
    d = elsewhere()
    cfg = offline_checks(d)
    if cfg:
        open(os.path.join(d, "desk.json"), "w").write(json.dumps(cfg))
        running_checks(d)
    shutil.rmtree(d, ignore_errors=True)
    return report()


def report():
    print()
    if fails:
        print("BUNDLE SMOKE FAILED - %d:" % len(fails))
        for f in fails:
            print("  -", f)
        return 1
    print("one file, no repository, no install: it configures, runs, serves,")
    print("refuses, and leaves its audit trail where the operator can find it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
