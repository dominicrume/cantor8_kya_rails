#!/usr/bin/env python3
"""Characterise tools/vote_pipeline.py and tools/post_queue.py, offline.

Both tools had a main() above the complexity ceiling and were split into small
functions on 24 November 2026. A refactor of a tool that prints numbers people
quote is only safe if the output is provably the same, so this runs both mains
against FAKE sources and compares stdout, exit code and files written with
tests/fixtures/pipeline_tools_golden.json, which was recorded from the code as
it stood BEFORE the split (commit 11c7860).

No network and no credential. vote_pipeline's one shell-out, gh(), is replaced
by a function returning fixed JSON. post_queue's run(), fetch(), input(),
clock and paths are replaced the same way, so nothing is copied, opened, logged
or fetched. Everything here is MOCKED data shaped like what GitHub and
Discourse return; it proves the tools' own logic, not the live services.

Run: python3 tests/pipeline_tools_smoke.py
Re-record (only when the behaviour is meant to change):
     python3 tests/pipeline_tools_smoke.py --record
"""
import base64
import builtins
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GOLDEN = os.path.join(HERE, "fixtures", "pipeline_tools_golden.json")


def load(name):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(ROOT, "tools", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


vp = load("vote_pipeline")
pq = load("post_queue")

# ---------------------------------------------------------------- vote data

GITVOTE_YML = """\
automation:
  enabled: false
duration: 21 days
pass_threshold: 51
close_on_passing: true
allowed_voters:
  teams:
    - tsc
"""


def created(when, opener):
    return {"author": {"login": "git-vote"}, "createdAt": when,
            "body": "Vote created by @%s" % opener}


def closed(when, tally, passed, binding):
    rows = "".join("| @%s | %s | %s |\n" % b for b in binding)
    verdict = "passed" if passed else "did not pass"
    body = ("Vote closed. The vote %s.\n| %d | %d | %d | %d |\n%s"
            % (verdict, tally[0], tally[1], tally[2], tally[3], rows))
    return {"author": {"login": "git-vote"}, "createdAt": when, "body": body}


def human(when, who, body):
    return {"author": {"login": who}, "createdAt": when, "body": body}


def b(who, how, stamp):
    return (who, how, stamp)


COMMENTS = {
    942: [created("2026-11-01T09:00:00Z", "chair"),
          closed("2026-11-04T15:30:00Z", (4, 0, 0, 1), True,
                 [b("a1", "In favor", "2026-11-04 15:00:05"),
                  b("a2", "In favor", "2026-11-04 15:05:00"),
                  b("a3", "In favor", "2026-11-04 15:10:00"),
                  b("a4", "In favor", "2026-11-04 15:20:00")])],
    900: [created("2026-10-10T09:00:00Z", "chair"),
          closed("2026-10-28T14:30:00Z", (1, 0, 0, 4), False,
                 [b("a1", "In favor", "2026-10-28 14:00:00")]),
          created("2026-11-02T09:00:00Z", "chair")],
    880: [created("2026-10-11T09:00:00Z", "chair"),
          closed("2026-10-28T14:30:00Z", (1, 2, 0, 2), False,
                 [b("a2", "Against", "2026-10-28 14:05:00"),
                  b("a3", "Against", "2026-10-28 14:08:00"),
                  b("a4", "In favor", "2026-10-28 14:10:00")])],
    866: [created("2026-10-16T09:00:00Z", "chair"),
          closed("2026-11-06T09:00:00Z", (0, 0, 0, 5), False, []),
          created("2026-11-09T09:00:00Z", "chair")],
    870: [created("2026-10-12T09:00:00Z", "other"),
          closed("2026-10-14T16:00:00Z", (3, 0, 0, 2), True,
                 [b("a1", "In favor", "2026-10-14 15:00:00"),
                  b("a2", "In favor", "2026-10-14 15:03:00"),
                  b("a3", "In favor", "2026-10-14 15:06:00")])],
    860: [human("2026-10-09T09:00:00Z", "dominicrume", "Who champions this?\nmore"),
          human("2026-10-10T09:00:00Z", "someone", "Looking."),
          human("2026-10-20T09:00:00Z", "dominicrume", "Ping, any news?")],
    861: [human("2026-10-09T09:00:00Z", "someone", "hello")],
    862: [],
    863: [created("2026-11-09T09:00:00Z", "chair")],
}


def label(*names):
    return [{"name": n} for n in names]


PRS = {
    942: ("Closed four in favour", "MERGED", label("gitvote/passed")),
    900: ("Re-opened after failing", "OPEN", label("gitvote/open")),
    880: ("Failed with objections", "CLOSED", label("gitvote/failed", "x")),
    866: ("Quiet failure re-opened", "OPEN", label("gitvote/open")),
    870: ("Passed by another opener", "MERGED", label("gitvote/passed")),
    860: ("Never had a vote", "OPEN", label("Needs Champion")),
    850: ("Unreadable comments", "OPEN", label("gitvote/open")),
    862: ("No comments at all", "OPEN", []),
    863: ("Open vote, nobody voted yet", "OPEN", label("gitvote/open")),
}


def pr_row(n):
    title, state, labels = PRS[n]
    return {"number": n, "title": title, "state": state, "labels": labels,
            "createdAt": "2026-10-0%dT10:00:00Z" % (n % 9 + 1)}


class FakeGh:
    """Stands in for vote_pipeline.gh. Records nothing, prints nothing."""

    def __init__(self, broken=(), no_config=False, rows=None, no_list=False):
        self.broken, self.no_config = set(broken), no_config
        self.rows, self.no_list = rows, no_list

    def __call__(self, *args):
        if args[0] == "api":
            return self._config()
        if args[:2] == ("pr", "list"):
            return self._list(args)
        if args[:2] == ("pr", "view"):
            return self._view(int(args[2]), args[-1])
        return None

    def _config(self):
        if self.no_config:
            return None
        return base64.b64encode(GITVOTE_YML.encode()).decode() + "\n"

    def _list(self, args):
        if self.no_list:
            return None
        limit = int(args[args.index("--limit") + 1])
        rows = self.rows if self.rows is not None else [
            pr_row(n) for n in sorted(PRS)]
        return json.dumps(rows[:limit])

    def _view(self, n, last):
        if n in self.broken:
            return None
        if last == "comments":
            if n not in COMMENTS:
                return None
            return json.dumps({"comments": COMMENTS[n]})
        return json.dumps(pr_row(n)) if n in PRS else None


def capture(fn):
    out, err = io.StringIO(), io.StringIO()
    code = None
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = fn()
        except SystemExit as e:
            code = "SystemExit:%s" % (e.code,)
        except Exception as e:  # a crash is behaviour too: pin its type
            code = "raised %s: %s" % (type(e).__name__, e)
    return {"stdout": out.getvalue(), "stderr": err.getvalue(),
            "result": code}


def vote_run(argv, **gh_kw):
    vp.gh = FakeGh(**gh_kw)
    old = sys.argv
    sys.argv = ["vote_pipeline.py"] + argv
    try:
        return capture(vp.main)
    finally:
        sys.argv = old


def _wrong_control():
    saved = COMMENTS[942]
    COMMENTS[942] = [created("2026-11-01T09:00:00Z", "chair"),
                     closed("2026-11-04T15:30:00Z", (3, 0, 0, 2), True, [])]
    try:
        return vote_run([])
    finally:
        COMMENTS[942] = saved


def vote_scenarios():
    big = [pr_row(942)] * 2000
    return {
        "vote full survey": lambda: vote_run([]),
        "vote full survey, config unreadable":
            lambda: vote_run([], no_config=True),
        "vote full survey, one proposal unreadable":
            lambda: vote_run([], broken={880}),
        "vote control fails (942 unreadable)":
            lambda: vote_run([], broken={942}),
        "vote control fails (942 wrong tally)": _wrong_control,
        "vote capped list is refused": lambda: vote_run([], rows=big),
        "vote list unreadable": lambda: vote_run([], no_list=True),
        "vote one: with tally and binding rows": lambda: vote_run(["942"]),
        "vote one: no vote ever opened": lambda: vote_run(["860"]),
        "vote one: open vote, no tally": lambda: vote_run(["863"]),
        "vote one: unreadable": lambda: vote_run(["850"]),
        "vote one: config unreadable":
            lambda: vote_run(["942"], no_config=True),
        "vote asks: ours and answered/unanswered": lambda: vote_run(
            ["asks", "860"]),
        "vote asks: never commented": lambda: vote_run(["asks", "861"]),
        "vote asks: unreadable": lambda: vote_run(["asks", "850"]),
        "vote asks: missing argument": lambda: vote_run(["asks"]),
    }


# ---------------------------------------------------------- post_queue data

FORUM_URL = "https://forum.canton.network/t/some-topic/9001"
CAT_URL = "https://forum.canton.network/c/sig/security/20"
PR_URL = "https://github.com/acme/widget/pull/7"
GROUPS_URL = "https://lists.sync.global/g/cip-discuss/topics"
NOW = 1700000000.0  # 2023-11-14 22:13:20 UTC; a fixed clock for the cutoff


def topic_json(last_user, n):
    return json.dumps({"post_stream": {"posts": [
        {"username": "someone", "post_number": 1,
         "created_at": "2026-11-01T10:00:00Z"},
        {"username": last_user, "post_number": n,
         "created_at": "2026-11-05T10:%02d:00Z" % n}]}})


def category_json(mine):
    topics = [{"id": 5, "title": "Old topic",
               "created_at": "2023-01-01T00:00:00",
               "last_poster_username": "someone"}]
    if mine:
        topics.append({"id": 6, "title": "Brand new topic",
                       "created_at": "2023-11-14T21:00:00",
                       "last_poster_username": pq.AUTHOR})
    return json.dumps({"topic_list": {"topics": topics}})


class PqEnv:
    """A scratch drafts tree plus fakes for every outside touchpoint."""

    def __init__(self, drafts, queue, log="", sources=True, check_rc=0,
                 fetches=None, gh_out="dominicrume\n", gh_rc=0, pbcopy_rc=0,
                 answers=(), optional=None, bad_check_for=None):
        self.tmp = tempfile.mkdtemp()
        self.drafts_dir = os.path.join(self.tmp, "drafts")
        self.sources_dir = os.path.join(self.drafts_dir, "sources")
        os.makedirs(self.sources_dir)
        for name, text in drafts.items():
            with open(os.path.join(self.drafts_dir, name), "w") as f:
                f.write(text)
        if sources:
            with open(os.path.join(self.sources_dir, "s1.txt"), "w") as f:
                f.write("source")
        self.log = os.path.join(self.drafts_dir, "posted.log")
        if log:
            with open(self.log, "w") as f:
                f.write(log)
        self.queue, self.optional = queue, optional or []
        self.check_rc, self.bad_check_for = check_rc, bad_check_for
        self.fetches, self.fetch_n = list(fetches or []), 0
        self.gh_out, self.gh_rc, self.pbcopy_rc = gh_out, gh_rc, pbcopy_rc
        self.answers = list(answers)
        self.calls = []

    def run(self, argv, **kw):
        tag = os.path.basename(argv[0]) if argv[0] != sys.executable else (
            os.path.basename(argv[1]))
        self.calls.append(tag + (":" + os.path.basename(argv[2])
                                 if tag == "before_posting.py" else ""))
        if tag == "before_posting.py":
            rc = self.check_rc
            if self.bad_check_for and argv[2].endswith(self.bad_check_for):
                rc = 1
            return subprocess.CompletedProcess(
                argv, rc, "checked ok\nPOST IT AT: x\nAdd --copy to y\nlast\n",
                "warn line\n")
        if tag == "pbcopy":
            return subprocess.CompletedProcess(argv, self.pbcopy_rc)
        if tag == "gh":
            return subprocess.CompletedProcess(argv, self.gh_rc,
                                               self.gh_out, "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    def fetch(self, url):
        self.calls.append("fetch")
        if not self.fetches:
            raise ValueError("no fetch recorded")
        i = min(self.fetch_n, len(self.fetches) - 1)
        self.fetch_n += 1
        return self.fetches[i]

    def input(self, prompt=""):
        print("[prompt] " + prompt, end="")
        if not self.answers:
            raise EOFError
        a = self.answers.pop(0)
        print(a)
        return a


def pq_run(argv, **kw):
    env = PqEnv(**kw)
    saved = {k: getattr(pq, k) for k in
             ("ROOT", "DRAFTS", "SOURCES", "LOG", "QUEUE", "OPTIONAL", "run",
              "fetch")}
    pq.ROOT, pq.DRAFTS, pq.SOURCES, pq.LOG = (
        ROOT, env.drafts_dir, env.sources_dir, env.log)
    pq.QUEUE, pq.OPTIONAL, pq.run, pq.fetch = (
        env.queue, env.optional, env.run, env.fetch)
    old_argv, old_input = sys.argv, builtins.input
    old_strf, old_time = time.strftime, time.time
    sys.argv = ["post_queue.py"] + argv
    builtins.input = env.input
    time.strftime = (lambda fmt, *a: "2026-11-24" if fmt == "%Y-%m-%d"
                     else old_strf(fmt, *a))
    time.time = lambda: NOW
    try:
        res = capture(pq.main)
    finally:
        sys.argv, builtins.input = old_argv, old_input
        time.strftime, time.time = old_strf, old_time
        for k, v in saved.items():
            setattr(pq, k, v)
    res["stdout"] = res["stdout"].replace(env.tmp, "<TMP>")
    res["log"] = open(env.log).read() if os.path.exists(env.log) else None
    res["calls"] = env.calls
    res["leftover_answers"] = env.answers
    return res


def d(url, body="Body text\nsecond line\n"):
    return "Post-To: %s then press Post\n\n%s" % (url, body)


Q1 = [("one.md", "why one")]
Q3 = [("one.md", "why one"), ("two.md", "why two"), ("three.md", "why three")]
OPT = [("opt.md", "not owed")]
THREE = {"one.md": d(FORUM_URL), "two.md": d(PR_URL),
         "three.md": d(GROUPS_URL)}
TWO_FETCH = [topic_json("someone", 2), topic_json("orumedominic", 3)]


def pq_scenarios():
    one = {"one.md": d(FORUM_URL)}
    two = {"two.md": d(PR_URL)}
    return {
        "pq dry run, three drafts": lambda: pq_run(
            ["--dry-run"], drafts=THREE, queue=Q3, optional=OPT),
        "pq no sources": lambda: pq_run([], drafts=THREE, queue=Q3,
                                        sources=False),
        "pq everything already logged": lambda: pq_run(
            [], drafts=THREE, queue=Q3, optional=OPT,
            log="2026-11-01 one.md  (verified)\n2026-11-02 two.md\n"
                "RETRACTED 2026-11-03 three.md\n2026-11-03 three.md\n"),
        "pq RETRACTED line does not count as posted": lambda: pq_run(
            ["--dry-run"], drafts=THREE, queue=Q3,
            log="RETRACTED 2026-11-03 one.md\n2026-11-01 two.md\n"),
        "pq gate fails, queue stops": lambda: pq_run(
            [], drafts=THREE, queue=Q3, check_rc=1),
        "pq gate fails on the second draft": lambda: pq_run(
            [], drafts=THREE, queue=Q3, bad_check_for="two.md",
            fetches=TWO_FETCH, answers=["", ""]),
        "pq no Post-To line": lambda: pq_run(
            [], drafts={"one.md": "just a body\n"}, queue=Q1),
        "pq forum reply posted, confirmed": lambda: pq_run(
            [], drafts=one, queue=Q1, fetches=TWO_FETCH, answers=[""]),
        "pq forum reply, nothing changed": lambda: pq_run(
            [], drafts=one, queue=Q1,
            fetches=[topic_json("orumedominic", 3)], answers=[""]),
        "pq forum reply, not there": lambda: pq_run(
            [], drafts=one, queue=Q1, fetches=[topic_json("someone", 2)],
            answers=[""]),
        "pq forum unreachable, typed yes": lambda: pq_run(
            [], drafts=one, queue=Q1, fetches=[], answers=["", "yes"]),
        "pq forum unreachable, typed no": lambda: pq_run(
            [], drafts=one, queue=Q1, fetches=[], answers=["", "no"]),
        "pq skip then quit": lambda: pq_run(
            [], drafts=THREE, queue=Q3, fetches=[topic_json("someone", 2)],
            answers=["s", "Q"]),
        "pq quit first": lambda: pq_run(
            [], drafts=THREE, queue=Q3, fetches=[topic_json("someone", 2)],
            answers=["q"]),
        "pq github pr confirmed": lambda: pq_run(
            [], drafts=two, queue=[("two.md", "w")], answers=[""],
            gh_out="dominicrume\n"),
        "pq github pr not ours": lambda: pq_run(
            [], drafts=two, queue=[("two.md", "w")], answers=[""],
            gh_out="someone\n"),
        "pq github gh fails": lambda: pq_run(
            [], drafts=two, queue=[("two.md", "w")], answers=["", "yes"],
            gh_rc=1),
        "pq groups.io cannot check": lambda: pq_run(
            [], drafts={"three.md": d(GROUPS_URL)},
            queue=[("three.md", "w")], answers=["", "yes"]),
        "pq new category topic posted": lambda: pq_run(
            [], drafts={"one.md": d(CAT_URL)}, queue=Q1,
            fetches=[category_json(False), category_json(True)],
            answers=[""]),
        "pq new category topic absent": lambda: pq_run(
            [], drafts={"one.md": d(CAT_URL)}, queue=Q1,
            fetches=[category_json(False)], answers=[""]),
        "pq pbcopy fails, full queue, optional printed": lambda: pq_run(
            [], drafts=THREE, queue=Q3, optional=OPT, pbcopy_rc=1,
            fetches=TWO_FETCH, answers=["", "s", "", "yes"]),
        "pq unknown destination": lambda: pq_run(
            [], drafts={"one.md": d("https://example.invalid/x")}, queue=Q1,
            answers=["", "yes"]),
    }


def run_all():
    results = {}
    for name, fn in {**vote_scenarios(), **pq_scenarios()}.items():
        results[name] = fn()
    return results


# Strings the recorded output must contain, or the scenarios are not reaching
# the branches they exist to pin down.
MUST_REACH = [
    "PASS - #942 reads", "REFUSING TO REPORT", "CONFIRMED:", "NOT THERE:",
    "CANNOT CHECK:", "nothing changed", "did NOT pass",
    "NO VOTE HAS EVER BEEN OPENED", "sitting days:", "NO REPLY since",
    "THAT is an unasked question", "Refusing to print numbers",
]


def main():
    results = json.loads(json.dumps(run_all()))
    if "--record" in sys.argv:
        with open(GOLDEN, "w") as f:
            json.dump(results, f, indent=1, sort_keys=True)
        print("recorded %d scenarios to %s" % (len(results), GOLDEN))
        return 0
    with open(GOLDEN) as f:
        golden = json.load(f)
    bad = [n for n in sorted(set(golden) | set(results))
           if results.get(n) != golden.get(n)]
    for n in bad:
        print("FAIL  %s" % n)
    blob = json.dumps(results)
    for m in MUST_REACH:
        if m not in blob:
            bad.append(m)
            print("FAIL  scenario set never reaches: %r" % m)
    if bad:
        print("\n%d problem(s). Behaviour differs from the recording."
              % len(bad))
        return 1
    print("pipeline_tools_smoke: %d scenarios byte-identical to the recording"
          % len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
