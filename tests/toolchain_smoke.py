#!/usr/bin/env python3
"""The sandbox and dashboard tools must pick daml or dpm per package.

    python3 tests/toolchain_smoke.py

Daml's classic `daml` assistant is deprecated and removed in SDK 3.5, where only
`dpm` builds. tools/daml_mutate.toolchain_for reads the sdk-version in a
package's daml.yaml and answers which one. tools/canton_sandbox.py and
tools/dashboard.py used to call `daml` unconditionally, so a 3.5 package reported
"does not build" for code that builds fine.

This puts fake `daml` and `dpm` executables on a temporary PATH. Each one
appends the argv and working directory it was given to a log and exits 0, so
the exact command line each tool chose can be asserted without a Daml SDK and
without starting a ledger. MOCKED: the shims stand in for the real assistants;
what is real here is the argv chosen, and `dpm build|test|sandbox --help` was
read on dpm 3.5.8 to check every flag used exists.

Stdlib only, per THE-RULES.md.
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import canton_sandbox as cs  # noqa: E402
import dashboard  # noqa: E402

QUIET = "--no-legacy-assistant-warning"
fails = []

SHIM = """#!%s
import json, os, sys
with open(os.environ["SHIM_LOG"], "a") as fh:
    fh.write(json.dumps([os.path.basename(sys.argv[0]), os.getcwd(),
                         sys.argv[1:]]) + "\\n")
if "--canton-port-file" in sys.argv:
    port = sys.argv[sys.argv.index("--canton-port-file") + 1]
    with open(port, "w") as fh:
        json.dump({"sandbox": {"ledgerApi": 1}}, fh)
    import time
    time.sleep(60)
"""


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


def make_packages(base, version):
    """All five packages of both chains, each with the given sdk-version."""
    for rel in cs.MANDATE_CHAIN + cs.REFUSAL_CHAIN:
        os.makedirs(os.path.join(base, rel), exist_ok=True)
        with open(os.path.join(base, rel, "daml.yaml"), "w") as fh:
            fh.write("sdk-version: %s\nname: p\n" % version)


def make_shims(bindir, names):
    os.makedirs(bindir, exist_ok=True)
    for name in names:
        path = os.path.join(bindir, name)
        with open(path, "w") as fh:
            fh.write(SHIM % sys.executable)
        os.chmod(path, 0o700)


def calls(log):
    if not os.path.exists(log):
        return []
    with open(log) as fh:
        return [json.loads(line) for line in fh]


class World:
    """A temp tree, shims on PATH, and a log. Restores everything on exit."""

    def __init__(self, version, shims=("daml", "dpm")):
        self.dir = os.path.realpath(tempfile.mkdtemp(prefix="kya-toolchain-"))
        self.tree = os.path.join(self.dir, "tree")
        self.log = os.path.join(self.dir, "log")
        make_packages(self.tree, version)
        make_shims(os.path.join(self.dir, "bin"), shims)
        self.saved = (os.environ.get("PATH"), os.environ.get("SHIM_LOG"),
                      cs.ROOT, dashboard.ROOT)

    def __enter__(self):
        os.environ["PATH"] = os.path.join(self.dir, "bin")
        os.environ["SHIM_LOG"] = self.log
        cs.ROOT = dashboard.ROOT = self.tree
        return self

    def __exit__(self, *exc):
        os.environ["PATH"] = self.saved[0]
        if self.saved[1] is None:
            os.environ.pop("SHIM_LOG", None)
        else:
            os.environ["SHIM_LOG"] = self.saved[1]
        cs.ROOT, dashboard.ROOT = self.saved[2], self.saved[3]
        shutil.rmtree(self.dir, ignore_errors=True)

    def pkg(self, rel):
        return os.path.join(self.tree, rel)


def quiet(fn, *a):
    """Run fn with stdout captured; return (result, what it printed)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        out = fn(*a)
    return out, buf.getvalue()


def run_sandbox(world, rel):
    dar = os.path.join(world.pkg(rel), ".daml", "dist", "x-1.0.0.dar")
    sb = cs.Sandbox(dar, extra=["--json-api-port", "7575"])
    try:
        started, _ = quiet(sb.start, 10)
    finally:
        sb.stop()
    return started, dar, sb.portfile


def era(version, tool, other):
    print("sdk-version %s: the assistant must be %s, never %s"
          % (version, tool, other))
    with World(version) as w:
        ok, _ = quiet(cs.build_chain, cs.MANDATE_CHAIN)
        check(ok, "build_chain succeeds with the shim")
        got = calls(w.log)
        flag = [QUIET] if tool == "daml" else []
        want = [[tool, w.pkg(rel), ["build"] + (flag)]
                for rel in cs.MANDATE_CHAIN]
        check(got == want, "build argv and cwd per package: %s" % got)
        check(not any(c[0] == other for c in got),
              "%s is never called for build" % other)
        os.remove(w.log)
        started, dar, port = run_sandbox(w, "step-1-mandate/test")
        got = calls(w.log)
        # The sandbox is started from the caller's directory, as it always was.
        want = [[tool, os.path.realpath(os.getcwd()),
                 ["sandbox"] + flag + ["--dar", dar, "--canton-port-file", port,
                                       "--json-api-port", "7575"]]]
        check(started and got == want, "sandbox argv: %s" % got)
        check(not any(c[0] == other for c in got),
              "%s is never called for sandbox" % other)
        os.remove(w.log)
        quiet(dashboard.daml_facts)
        got = calls(w.log)
        test_dir = w.pkg("step-1-mandate/test")
        want = [[tool, w.pkg("step-1-mandate"), ["build"] + flag],
                [tool, test_dir, ["test"] + flag + ["--all", "--show-coverage"]]]
        check(got == want, "dashboard build then test argv: %s" % got)
        check(not any(c[0] == other for c in got),
              "%s is never called by the dashboard" % other)


def missing_tool():
    print("a missing tool is named, with the install help")
    with World("3.5.8", shims=("daml",)) as w:
        ok, out = quiet(cs.have_daml, cs.MANDATE_CHAIN)
        check(ok is False, "3.5 package without dpm: not ok")
        check("dpm is not on PATH" in out and cs.DPM_HELP in out,
              "message names dpm and the help URL: %r" % out)
        check("daml is not on PATH" not in out, "message does not blame daml")
    with World("3.4.11", shims=("dpm",)) as w:
        ok, out = quiet(cs.have_daml, cs.MANDATE_CHAIN)
        check(ok is False, "3.4 package without daml: not ok")
        check("daml is not on PATH" in out and cs.DPM_HELP in out,
              "message names daml and the help URL: %r" % out)
        check("dpm is not on PATH" not in out, "message does not blame dpm")
    with World("3.4.11", shims=("daml",)) as w:
        ok, out = quiet(cs.have_daml)
        check(ok is True and out == "", "3.4 with daml only: ok, silent")
    with World("3.5.8", shims=("dpm",)) as w:
        ok, _ = quiet(cs.have_daml)
        check(ok is True, "3.5 with dpm only, no chain given: ok")


def one_chain_only():
    print("the check asks only for what the chain needs")
    with World("3.4.11", shims=("daml",)) as w:
        with open(os.path.join(w.pkg("step-0-refusal"), "daml.yaml"), "w") as fh:
            fh.write("sdk-version: 3.5.8\n")
        ok, _ = quiet(cs.have_daml, cs.MANDATE_CHAIN)
        check(ok is True, "mandate chain (3.4) does not need dpm")
        ok, out = quiet(cs.have_daml, cs.REFUSAL_CHAIN)
        check(ok is False and "dpm is not on PATH" in out,
              "refusal chain (one 3.5 package) needs dpm")
        ok, out = quiet(cs.have_daml)
        check(ok is False and "dpm is not on PATH" in out,
              "no chain given: every package of both chains is asked about")


def mixed_packages():
    print("each package decides for itself, inside one tool")
    with World("3.4.11") as w:
        with open(os.path.join(w.pkg("step-1-mandate/test"), "daml.yaml"), "w") as fh:
            fh.write("sdk-version: 3.5.8\n")
        quiet(dashboard.daml_facts)
        got = [(c[0], c[2][0]) for c in calls(w.log)]
        check(got == [("daml", "build"), ("dpm", "test")],
              "dashboard: mandate builds with daml, its test package with dpm: %s" % got)


def unreadable_version():
    print("no readable sdk-version keeps the classic assistant")
    with World("3.5.8") as w:
        os.remove(os.path.join(w.pkg("step-1-mandate"), "daml.yaml"))
        argv = cs.assistant_argv(w.pkg("step-1-mandate"), "build")
        check(argv == ["daml", "build", QUIET], "argv: %s" % argv)


def main():
    era("3.4.11", "daml", "dpm")
    era("3.5.8", "dpm", "daml")
    missing_tool()
    one_chain_only()
    mixed_packages()
    unreadable_version()
    print("")
    if fails:
        print("FAILED: %d" % len(fails))
        return 1
    print("all toolchain checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
