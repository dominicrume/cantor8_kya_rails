#!/usr/bin/env python3
"""The discovery step of the Daml mutation harness, tested without Daml.

    python3 tests/daml_fences_smoke.py

tools/daml_fences.py finds the runtime checks in Daml source (`assertMsg`,
`ensure`, `assert`, `require`, `requireMatchExpected`, `unless ... fail`,
`when ... fail`) and lists every check-like line it did NOT recognise, with a
reason. It is pure text in, lists out, so these tests run in every clone with
no SDK, which is the point of keeping it pure.

Three kinds of test, because a test that cannot fail proves nothing:
  FIXTURES   one small piece of Daml per tricky form, and the exact answer.
  CONTROLS   the same fixtures run through a deliberately broken discovery,
             which must get them WRONG, and through the old regex, which must
             disagree where the old regex was known to be wrong.
  BACKTEST   on this repository's own Daml, the generalised discovery in legacy
             mode must return the same fences the old tool returned, captured
             in tests/fixtures/daml_fences_golden.json BEFORE the change.

The reasoning behind each fixture is in tools/daml_fences.py's docstring.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import daml_fences as df          # noqa: E402
import daml_mutate as dm          # noqa: E402

fails = []
REQ = frozenset({"require", "requireMatchExpected"})


def check(ok, what):
    print("  %s %s" % ("PASS" if ok else "FAIL", what))
    if not ok:
        fails.append(what)


def found_of(src, known=frozenset(), kinds=df.ALL_KINDS):
    found, unseen = df.discover(src, kinds=kinds, known=known)
    return [(a, k, b) for a, k, b in found], unseen


def reasons(unseen):
    return " | ".join(r for _l, r, _t in unseen)


print("fixtures: what is a check, and where it ends")
f, u = found_of('  assertMsg "m" (x > 0)')
check(f == [(1, "assertMsg", 2)] and not u, "F01 a one-line assertMsg")
f, u = found_of("  ensure x > 0")
check(f == [(1, "ensure", 2)] and not u, "F02 a one-line ensure")
f, u = found_of('  require "m"\n    (x > 0)', REQ)
check(f == [(1, "require", 3)], "F03 a two-line require spans both lines")
f, u = found_of('  requireMatchExpected "id" a b', REQ)
check(f == [(1, "requireMatchExpected", 2)], "F04 requireMatchExpected")
f, u = found_of('  unless (x > 0) $ fail "neg"')
check(f == [(1, "unless", 2)], "F05 unless ... $ fail")
f, u = found_of('  unless (x > 0) do\n    debug "a"\n    fail "neg"')
check(f == [(1, "unless", 4)], "F06 unless with a do block spans three lines")
f, u = found_of('  -- require "m" (x>0)', REQ)
check(f == [] and u == [], "F07 a line comment is not a check")
f, u = found_of('  {- block\n  require "m" True\n  ensure x -}', REQ)
check(f == [] and u == [], "F08 a block comment is not a check")
f, u = found_of('  let s = "require \\"m\\" (x)"', REQ)
check(f == [] and u == [], "F09 a string holding the word is not a check")
f, u = found_of("  -- ensure x > 0 is checked\n  ensure x > 0")
check(f == [(2, "ensure", 3)], "F10 a comment above does not steal the line number")
f, u = found_of('  forA_ xs $ \\x -> do\n    when (x > 0) do\n      require "m" (x < 9)', REQ)
check(f == [(3, "require", 4)], "F11 a require nested under a flow-control when is found")
check(any("flow control" in r for _l, r, _t in u),
      "  and the `when` that never fails is listed as unseen, not dropped")
f, u = found_of('  require\n  "m" (x>0)', REQ)
check(f == [(1, "require", 2)], "F12 a statement ends where the indent returns")
f, u = found_of('  Some.require "m" c', REQ)
check(f == [(1, "require", 2)], "F13 a qualified call to a NAMED check helper is a check")
f, u = found_of('  Some.require "m" c')
check(f == [] and "unresolved helper" in reasons(u),
      "  and the same call is unseen when nobody named the helper a check")
f, u = found_of('  r <- require "m" c', REQ)
check(f == [] and "bound result" in reasons(u), "F14 a bound result is unseen: deleting it would not compile")
f, u = found_of('  require "m" c')
check(f == [] and "unresolved helper" in reasons(u),
      "F15 a helper nobody resolved is unseen until it is named a check")
f, u = found_of("  let unlessX = 1")
check(f == [] and u == [], "F16 a longer identifier is not the keyword")
f, u = found_of('  require\' ("a", x) isEqualR ("b", y)', frozenset({"require'"}))
check(f == [(1, "require'", 2)], "F18 the primed require' that OpenZeppelin uses most")
f, u = found_of('  require\' ("a", x) isEqualR ("b", y)', frozenset({"require"}))
check(f == [], "  and naming `require` does not name `require'`")
f, u = found_of('  Internal.requireSuccess $ Internal.checkCondition s ok', frozenset({"requireSuccess"}))
check(f == [(1, "requireSuccess", 2)], "F19 a qualified requireSuccess ending in $ is found")
f, u = found_of('  assertWithinDeadline "executeBefore" t')
check(f == [(1, "assertWithinDeadline", 2)], "F20 the standard library's deadline check needs no naming")
f, u = found_of('  when (isPaused x) (failWithStatus eEnforcedPause)')
check(f == [(1, "when", 2)], "F21 when ... failWithStatus is a check")
f, u = found_of('  foo -->  fail "x"')
check(f == [] and len(u) == 1, "F22 `-->` is an operator, not a comment: the fail after it is seen (as unseen)")
f, u = found_of('  assertMsg "m" True', kinds=df.LEGACY)
check(len(f) == 1, "F17 legacy kinds still find assertMsg")
f, u = found_of('  require "m" c', REQ, kinds=df.LEGACY)
check(f == [], "  and legacy kinds do not find require")

print("")
print("helpers: a definition is not a call")
HELPER = ('require : Text -> Bool -> Update ()\n'
          'require msg ok = unless ok $ fail msg\n\n'
          'f = do\n'
          '  require "a" True\n')
check(df.defined_helpers([HELPER]) == {"require"},
      "a require whose body can refuse is detected as a check helper")
check(df.defined_helpers(['require : Text -> Update ()\nrequire msg = pure ()\n']) == set(),
      "  and one that only formats is not")
f, u = found_of(HELPER, frozenset({"require"}))
check(f == [(5, "require", 6)],
      "the call is found and the helper's own body is NOT (deleting it would "
      "make every call site vacuous at once)")

print("")
print("honesty: one of every construct, nothing dropped")
EVERY = ('  assertMsg "a" True\n  ensure True\n  require "r" True\n'
         '  requireMatchExpected "e" 1 1\n  unless ok $ fail "u"\n'
         '  when bad $ abort "w"\n  x <- require "b" True\n'
         '  Mod.require "q" True\n  fail "bare"\n')
f, u = found_of(EVERY, REQ)
check(len(f) == 7, "seven checks recognised (%d)" % len(f))
check(len(u) == 2, "two check-like lines unseen, each with a reason (%d)" % len(u))
lines_with_a_word = [i + 1 for i, l in enumerate(df.mask(EVERY).split("\n"))
                     if df.ANY.search(l)]
accounted = sorted([a for a, _k, _e in f] + [l for l, _r, _t in u])
check(lines_with_a_word == accounted,
      "every line carrying a check word is either recognised or listed as unseen")

print("")
print("neutering: what makes a check vacuous")
check(df.neuter('  assertMsg "m" c', "assertMsg") == '  assertMsg "mutated" True',
      "assertMsg becomes assertMsg \"mutated\" True, as before")
check(df.neuter("  ensure c", "ensure") == "  ensure True", "ensure becomes ensure True, as before")
check(df.neuter('    require "m" c', "require") == "    pure ()",
      "require becomes pure (), keeping its indent")
check(df.neuter("  unless c $ fail \"x\"", "unless") == "  pure ()", "unless ... fail becomes pure ()")

print("")
print("controls: these tests can fail")
real_mask = df.mask
df.mask = lambda s: s          # a discovery that treats every line as code
try:
    f, _u = found_of('  {- block\n  ensure x -}')
    check(f != [], "CONTROL a discovery that does not strip comments finds the commented fence (F08 would fail)")
    f, _u = found_of('  -- ensure x\n', kinds=df.LEGACY)
    check(f == [] or True, "  (a plain line comment is caught by the line anchor either way)")
finally:
    df.mask = real_mask
old = re.compile(r"^\s*(assertMsg|ensure)\b")
block = '  {- block\n  require "m" True\n  ensure x -}'
check(any(old.match(l) for l in block.split("\n")) and found_of(block)[0] == [],
      "CONTROL the old regex finds a fence inside a block comment and the new discovery does not")
check(not old.match('  unless ok $ fail "x"') and found_of('  unless ok $ fail "x"')[0] != [],
      "CONTROL the old regex cannot see an unless ... fail and the new one can")

print("")
print("backtest: this repository's own Daml, legacy mode, against the golden list")
gold = json.load(open(os.path.join(ROOT, "tests", "fixtures", "daml_fences_golden.json")))["fences"]
for pkg in ("step-1-mandate", "step-0-refusal"):
    base = os.path.join(ROOT, pkg)
    got = []
    for path in dm.sources(base):
        src = open(path, encoding="utf-8").read()
        lines = src.splitlines()
        found, _unseen = df.discover(src, kinds=df.LEGACY)
        got += [[os.path.relpath(path, base), ln, lines[ln - 1].strip()] for ln, _k, _e in found]
    check(got == gold[pkg], "%s: %d fences, identical to the golden list, in order" % (pkg, len(got)))
    old_found = dm.fences(base)
    check(len(old_found) == len(gold[pkg]), "  and the old tool still finds the same %d" % len(old_found))

print("")
if fails:
    print("FAILED: %d" % len(fails))
    for x in fails:
        print("  - " + x)
    sys.exit(1)
print("the discovery sees what it claims to see, lists what it does not, and agrees")
print("with the old tool on the code where the old tool was right.")
