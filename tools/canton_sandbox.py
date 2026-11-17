"""Build what a tool needs from source, start a real Canton, and stop it.

Shared by tools/prove_refusal_on_sandbox.py and tools/can_the_auditor_tell.py.

WHY THIS EXISTS. On 13 November 2026 an application for a security role told a
stranger to run

    git clone https://github.com/dominicrume/cantor8_kya_rails
    cd cantor8_kya_rails && python3 tools/prove_refusal_on_sandbox.py

and the command had never been run from a clean clone. Doing it, for the first
time, failed on the first step:

    damlc: ../.daml/dist/kya-rails-mandate-1.1.1.dar: openBinaryFile:
    does not exist

The test package depends on a DAR the mandate package builds, and .daml/ is
build output, ignored by git. Every run on the author's machine had passed
because the author's machine already held that file. The tool built one
package of two and nothing noticed, including tools/unpublished.py, which
checks that a promised file answers 200 on GitHub and never that the promised
command runs.

The same hole sat under a forum post. A reply on topic 9114 told a reader to
run tools/can_the_auditor_tell.py, which expected a sandbox the reader would
have had to build and start by hand.

So the dependency order is written down once, here, and a tool names the chain
it needs instead of assuming the files exist.
"""
import json
import os
import shutil
# B404 is suppressed below: driving the daml CLI is this module's whole job.
import subprocess  # nosec B404
import signal
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUIET = "--no-legacy-assistant-warning"

# Each chain lists packages in the order they must be built, because each one
# names the one before it as a data-dependency. Read from the daml.yaml files:
#   step-1-mandate/test    -> ../.daml/dist/kya-rails-mandate-1.1.1.dar
#   step-0-refusal         -> interface/.daml/dist/canton-journal-interface-1.0.0.dar
#   step-0-refusal/test    -> both of the above
MANDATE_CHAIN = ["step-1-mandate", "step-1-mandate/test"]
REFUSAL_CHAIN = ["step-0-refusal/interface", "step-0-refusal",
                 "step-0-refusal/test"]


def say(msg):
    print(msg, flush=True)


# What the ledger answers while the DAR given to `daml sandbox --dar` is still
# being uploaded and vetted. Canton writes its port file BEFORE that finishes,
# so a command sent the moment the port file appears can arrive too early. Found
# 17 November 2026: the same tool passed in a working tree and failed twice from
# a fresh clone, once with each of these two answers. The DAR was byte for byte
# the same in both, so the difference was timing, not the code.
NOT_READY = ("PACKAGE_NAMES_NOT_FOUND", "JSON_API_PACKAGE_SELECTION_FAILED",
             "not consistently vetted")


def when_packages_ready(attempt, timeout=120, pause=2,
                        sleep=time.sleep, clock=time.monotonic):
    """Run attempt() until it stops failing because the DAR is not ready yet.

    Only the answers in NOT_READY are retried, and only for `timeout` seconds. A
    command that fails for any other reason fails at once, so a real error is
    never hidden behind a wait. The caller's attempt() must be safe to repeat,
    which a command the ledger refused is: nothing was created.
    """
    started = clock()
    while True:
        try:
            return attempt()
        except SystemExit as err:
            late = clock() - started >= timeout
            if late or not any(m in str(err.code) for m in NOT_READY):
                raise
            sleep(pause)


def have_daml():
    if shutil.which("daml") is None:
        say("daml is not on PATH. Install the Daml SDK, then re-run.")
        return False
    return True


def build_chain(chain):
    """daml build each package in order. False, with the reason, on failure."""
    for rel in chain:
        say("building %s" % rel)
        # B603 and B607: literal argv, shell=False, every element a string.
        r = subprocess.run(  # nosec B603 B607
            ["daml", "build", QUIET], cwd=os.path.join(ROOT, rel),
            capture_output=True, text=True)
        if r.returncode != 0:
            say("  build failed in %s:\n    %s"
                % (rel, (r.stderr or r.stdout).strip()[-400:]))
            return False
    return True


class Sandbox:
    """A real Canton participant, sequencer and mediator, started clean.

    Started clean on every run because party hints are fixed: a second run
    against a live ledger dies with 'Party already exists', which looks like
    a test failure and is not one.
    """

    def __init__(self, dar, extra=()):
        self.tmp = tempfile.mkdtemp(prefix="kya-sandbox-")
        self.portfile = os.path.join(self.tmp, "ports.json")
        self.proc = None
        self.ports = None
        self.dar = dar
        self.extra = list(extra)

    def start(self, wait=180):
        """Start Canton and wait for its port file. True once it is ready."""
        say("starting a real Canton sandbox (participant, sequencer, mediator)")
        # B603 only. The argument list is built with `+ self.extra`, so bandit
        # cannot see a literal and does not raise B607 here. Suppressing an id
        # it did not raise is itself a bandit warning.
        self.proc = subprocess.Popen(  # nosec B603
            ["daml", "sandbox", QUIET, "--dar", self.dar,
             "--canton-port-file", self.portfile] + self.extra,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
        for _ in range(wait):
            if self.proc.poll() is not None:
                say("  the sandbox exited before it was ready. Is another")
                say("  Canton already holding port 6865?")
                return False
            if os.path.exists(self.portfile) and os.path.getsize(self.portfile):
                with open(self.portfile) as fh:
                    self.ports = json.load(fh)["sandbox"]
                say("  ledger API on port %d" % self.ports["ledgerApi"])
                return True
            time.sleep(1)
        say("  the sandbox did not become ready within %d seconds" % wait)
        return False

    def stop(self):
        """Stop it, and remove the temp directory whether or not it started."""
        if self.proc is not None and self.proc.poll() is None:
            self._signal(signal.SIGTERM)
            try:
                self.proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self._signal(signal.SIGKILL)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _signal(self, sig):
        try:
            os.killpg(os.getpgid(self.proc.pid), sig)
        except (ProcessLookupError, PermissionError):
            self.proc.terminate()
