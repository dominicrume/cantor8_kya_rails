#!/usr/bin/env python3
"""Everything that must be true before a version goes to PyPI, done not recalled.

CLAUDE.md sets four rules for a release, and they exist because each was broken
once: build from committed code and never the working tree, list every file
that would go public, scan the built artefacts for secrets WITH A POSITIVE
CONTROL proving the scan reads them, and install the artefact into a clean
environment and run it.

This does all four and stops on the first failure. It PUBLISHES NOTHING. A
PyPI version number cannot be reused once taken, so the last step is a person
typing the name and the version.

    python3 tools/release_check.py

The positive control is the part worth explaining. A secret scan that finds
nothing is indistinguishable from a secret scan that is not reading the files.
So a known fake secret is planted in a copy of the built artefact, the same
scan is run, and it must find it. A scan that cannot say yes cannot be trusted
when it says no.
"""
import json
import os
import re
import shutil
import subprocess  # nosec B404 - fixed argv, no shell
import sys
import tarfile
import zipfile
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PKG = os.path.join(ROOT, "pkg")

fails = []


def step(n, what):
    print("\n%s. %s" % (n, what))


def check(ok, what):
    print("   " + ("ok   " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def run(argv, cwd=None):
    return subprocess.run(argv, cwd=cwd or ROOT,  # nosec B603 - literal argv
                          capture_output=True, text=True)


def version():
    s = open(os.path.join(PKG, "pyproject.toml")).read()
    return re.search(r'^version = "([^"]+)"', s, re.M).group(1)


VERSION = version()
NAME = "knowyouragenticai-receipts"
print("release check: %s %s" % (NAME, VERSION))

# ---------------------------------------------------------------- 1. committed
step(1, "the tree is committed, so the artefact matches the history")
dirty = [l for l in run(["git", "status", "--porcelain"]).stdout.splitlines()
         if l.strip() and not l.startswith("??")]
check(not dirty, "nothing uncommitted"
      + ("" if not dirty else ": " + ", ".join(d[3:] for d in dirty[:4])))

# ------------------------------------------------------------ 2. not published
step(2, "this version is not already on PyPI, because a number cannot be reused")
import json  # noqa: E402
import urllib.request  # noqa: E402
try:
    with urllib.request.urlopen(  # nosec B310 - literal host
            "https://pypi.org/pypi/%s/json" % NAME, timeout=20) as r:
        live = json.loads(r.read())
    taken = sorted(live["releases"])
    check(VERSION not in taken,
          "%s is free (taken: %s)" % (VERSION, ", ".join(taken)))
except Exception as e:                       # noqa: BLE001 - offline is an answer
    check(False, "could not reach PyPI to check: %s" % str(e)[:50])

# ------------------------------------------------------- 3. build from a clone
step(3, "build from a CLONE of the committed code, not the working tree")
work = tempfile.mkdtemp(prefix="release-")
clone = os.path.join(work, "src")
os.makedirs(os.path.join(work, "dist"), exist_ok=True)
r = run(["git", "clone", "--quiet", "--depth", "1", "file://" + ROOT, clone])
check(r.returncode == 0, "cloned the repository at HEAD")
built = []
if r.returncode == 0:
    # `build` is not installed and must not be: CLAUDE.md says this project is
    # stdlib only. setuptools IS present, and its PEP 517 backend can be driven
    # directly, which is exactly what `build` would do anyway. Falling back to
    # setup.py would fail differently, because there is no setup.py: the
    # package is pyproject-only by design.
    # One process per artefact. Building the sdist and then the wheel in the SAME
    # process left the wheel in a stray folder (pkg/sdist/), so the gate saw one file,
    # said "built", and never listed or scanned the wheel, which is the artefact most
    # people install. 1.3.1 shipped with that gap in the gate.
    dist = os.path.join(work, "dist")
    out = ""
    for kind in ("build_sdist", "build_wheel"):
        r = run([sys.executable, "-c",
                 "import sys;sys.path.insert(0,'.');"
                 "from setuptools import build_meta as b;"
                 "print(getattr(b, sys.argv[2])(sys.argv[1]))", dist, kind],
                cwd=os.path.join(clone, "pkg"))
        out += r.stdout + r.stderr
    os.makedirs(dist, exist_ok=True)
    built = sorted(os.listdir(dist))
    check(any(b.endswith(".tar.gz") for b in built) and any(b.endswith(".whl") for b in built),
          "built BOTH a wheel and an sdist: %s" % (", ".join(built) or "NOTHING: " + out.strip()[-160:]))

# ------------------------------------------------- 4. every file that goes out
step(4, "every file that would go public, listed")
members = []
if built:
    sdist = [b for b in built if b.endswith(".tar.gz")]
    if sdist:
        with tarfile.open(os.path.join(work, "dist", sdist[0])) as t:
            members = [m.name for m in t.getmembers() if m.isfile()]
    for m in sorted(members):
        print("      " + m.split("/", 1)[-1])
    check(bool(members), "%d files" % len(members))
    unexpected = [m for m in members
                  if any(bad in m for bad in (".env", "id_rsa", ".pem", ".key",
                                              "secret", "__pycache__"))]
    check(not unexpected, "nothing that looks private"
          + ("" if not unexpected else ": %s" % unexpected[:3]))
    wheels = [b for b in built if b.endswith(".whl")]
    if wheels:
        with zipfile.ZipFile(os.path.join(work, "dist", wheels[0])) as z:
            wnames = z.namelist()
        bad = [m for m in wnames if any(x in m for x in (".env", "id_rsa", ".pem", ".key",
                                                          "secret", "__pycache__"))]
        check(len(wnames) > 0 and not bad, "the wheel lists %d files and nothing looks private%s"
              % (len(wnames), "" if not bad else ": %s" % bad[:3]))

# -------------------------------------------- 5. secret scan, positive control
step(5, "scan the built artefact for secrets, and prove the scan can say yes")
PATTERNS = [r"C8_CLIENT_SECRET\s*=\s*['\"][^'\"]{12,}",
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
            r"gh[pousr]_[A-Za-z0-9]{20,}",
            r"pypi-[A-Za-z0-9_\-]{30,}"]


def scan(text):
    return [p for p in PATTERNS if re.search(p, text)]


if members:
    sdist_path = os.path.join(work, "dist",
                              [b for b in built if b.endswith(".tar.gz")][0])
    with tarfile.open(sdist_path) as t:
        blob = "".join(
            (t.extractfile(m).read().decode("utf-8", "ignore"))
            for m in t.getmembers() if m.isfile())
    check(not scan(blob), "the real artefact is clean")
    # The control: the same scan, over the same bytes, plus one planted secret.
    planted = blob + '\nC8_CLIENT_SECRET = "not-a-real-secret-abcdefghijkl"\n'
    hits = scan(planted)
    check(bool(hits),
          "and the scan FINDS a planted secret, so 'clean' means something")

# --------------------------------------------- 6. install clean and run it
step(6, "install into a clean environment and actually run it")
if built:
    venv = os.path.join(work, "venv")
    r = run([sys.executable, "-m", "venv", venv])
    py = os.path.join(venv, "bin", "python")
    check(os.path.exists(py), "made a clean virtual environment")
    if os.path.exists(py):
        wheel = [b for b in built if b.endswith(".whl")]
        art = os.path.join(work, "dist", (wheel or built)[0])
        r = run([py, "-m", "pip", "install", "--quiet", art])
        check(r.returncode == 0, "installed %s" % os.path.basename(art)
              + ("" if r.returncode == 0 else ": " + (r.stdout + r.stderr)[-140:]))
        r = run([py, "-m", "knowyouragenticai_receipts", "selftest"])
        out = r.stdout + r.stderr
        check(r.returncode == 0 and "CONFORMANT" in out,
              "selftest passes in that environment: %s"
              % next((l for l in out.splitlines() if "CONFORMANT" in l),
                     out.strip()[-90:]))
        r = run([py, "-c", "import knowyouragenticai_receipts as k;"
                 "print(k.__version__);"
                 "d=k.disclose(k.Policy(cap='1.00',currency='USD',allow=['a'])"
                 ".open().receipts);print(k.check_disclosure(d))"])
        check(VERSION in r.stdout and "True" in r.stdout,
              "the NEW code is what got installed: %s"
              % (r.stdout.strip().replace("\n", " ")[:70] or r.stderr[-70:]))

# ------------------------ 6b. the install routes the README tells a user to type
# pkg/README.md gives three ways to register the MCP server. Until this step, none of
# them was run from the installed wheel: step 6 ran `selftest`, not the server. A user
# who follows the README must get a server that answers AND names the package and
# version that was installed, so a log line can never be mistaken for another project's.
def handshake(argv, cwd):
    """The serverInfo dict from `initialize`, or None if the command did not answer."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    msg = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    try:
        r = subprocess.run(argv, input=msg + "\n", cwd=cwd, env=env,  # nosec B603
                           capture_output=True, text=True, timeout=30)
        return json.loads(r.stdout.splitlines()[0])["result"]["serverInfo"]
    except (OSError, ValueError, IndexError, KeyError, subprocess.SubprocessError):
        return None


def names_us(info, version):
    return bool(info) and info.get("name") == NAME and info.get("version") == version


step("6b", "the README's install routes, run from the installed wheel")
if built and os.path.exists(py):
    quiet = tempfile.mkdtemp(prefix="kya-route-")
    console = os.path.join(venv, "bin", "kya-receipts-mcp")
    routes = (("python -m knowyouragenticai_receipts mcp",
               [py, "-m", "knowyouragenticai_receipts", "mcp"]),
              ("kya-receipts-mcp", [console]))
    for label, argv in routes:
        info = handshake(argv, quiet)
        check(names_us(info, VERSION),
              "`%s` answers and says it is %s %s (got %s)" % (label, NAME, VERSION, info))
    check(not names_us({"name": "kya", "version": VERSION}, VERSION),
          "control: a server that calls itself plain 'kya' is NOT accepted")
    check(handshake([os.path.join(quiet, "no-such-command")], quiet) is None,
          "control: a command that does not exist is NOT reported as working")
    shutil.rmtree(quiet, ignore_errors=True)

# ---------------------------------------------------------------- 7. what CI would say
# 1.3.1 passed steps 1 to 6 and then failed CI, because CI runs `mypy --strict` on the
# package (it ships py.typed, which is a promise) and this gate did not. A gate that
# says "ready" for something CI refuses is worse than no gate. This runs the same
# command, on the same clean clone, and fails loudly if it cannot.
step(7, "the type check CI runs on the package, because py.typed is a promise")
if r.returncode == 0 and os.path.isdir(clone):
    probe = run([sys.executable, "-m", "mypy", "--version"])
    if probe.returncode != 0:
        check(False, "mypy is not installed, and CI runs it: python3 -m pip install mypy")
    else:
        r = run([sys.executable, "-m", "mypy", "--strict",
                 os.path.join(clone, "pkg", "src", "knowyouragenticai_receipts")])
        check(r.returncode == 0, "mypy --strict is clean on the committed package: %s"
              % (r.stdout.strip().splitlines() or ["(no output)"])[-1][:90])

shutil.rmtree(work, ignore_errors=True)

print()
if fails:
    print("NOT READY - %d:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("=" * 66)
print("%s %s is ready." % (NAME, VERSION))
print()
print("NOTHING HAS BEEN PUBLISHED. A PyPI version cannot be reused, so the")
print("last step is a person saying the name and the number:")
print()
print("    publish %s %s" % (NAME, VERSION))
print("=" * 66)
