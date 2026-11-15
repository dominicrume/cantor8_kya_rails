#!/usr/bin/env python3
"""Find the runtime checks in a Daml source file, and say what it could not see.

    python3 tools/daml_fences.py FILE.daml [--known-checks require,requireMatchExpected]

WHY THIS EXISTS. tools/daml_mutate.py found checks with one regex that
recognised only `assertMsg` and `ensure`. OpenZeppelin's current Daml library
writes its checks as `require`, `requireMatchExpected` and `unless ... fail`,
so on their `packages/` directory the harness saw about 5 of 36. This module
is the discovery step with the construct set generalised, kept PURE (text in,
list out, no SDK) so it can be tested in every clone without Daml installed.

THE LEXING STRATEGY, and why a regex is not enough. A line-start regex is
provably wrong in four ways: a check-looking line inside a `{- -}` block
comment; the word inside a string literal; an operator such as `-->` mistaken
for a comment; and a statement whose extent only layout can tell you. So
comments and string contents are first BLANKED (same length, newlines kept, so
every line number and column still points at the original), and discovery runs
on what is left.

THE HONESTY REQUIREMENT. Every line that carries a check-like word is either
a recognised check or an entry in the `unseen` list with a reason. Nothing is
silently dropped. A reader of a result can then tell "covered 24 of 62" from
"covered 24 of the 24 the tool could see".

WHAT IT DOES NOT SEE, said up front: checks written through macros or CPP; a
helper it cannot resolve (the caller can name one with `known`); a result bound
with `<-` (deleting it would not compile); a guard inside a `case` or `if`
branch (the effect, not the guard); qualified calls such as `Mod.require`.

Stdlib only, per THE-RULES.md.
"""
import re
import sys

# Symbol characters that can make `--` an operator rather than a comment. The
# dash itself is excluded, a run of dashes is handled separately.
OPS = set("!#$%&*+./<=>?@\\^|~:")

LEGACY = ("assertMsg", "ensure")
# The standard library's own checks: recognised without being told.
BUILTIN = ("assertMsg", "ensure", "assert", "assertDeadlineExceeded",
           "assertWithinDeadline", "unless", "when")
# Library helpers that are checks only if somebody says so. `require` is a
# function from a library (OpenZeppelin takes it from the vendored Splice token
# standard utils), not a language construct, and a project can define its own
# `require` that checks nothing. So these are recognised only when the caller
# names them, or when the package defines one whose body can refuse.
HELPERS = ("require", "require'", "requireMatchExpected", "requireSuccess")
ALL_KINDS = BUILTIN + HELPERS
# What a helper's BODY must contain for the helper to count as a check. Not the
# helper's own name, which every definition contains.
CAN_REFUSE = re.compile(r"(?<![\w'])(assertMsg|assert|fail|abort|error|assertFail|"
                        r"throw|failWithStatus|unless|when)(?![\w'])")
FAILS = re.compile(r"\b(fail|abort|error|assertFail|throw|failWithStatus)\b")
_NAMES = "|".join(re.escape(n) for n in
                  sorted(BUILTIN + HELPERS, key=len, reverse=True))
ANY = re.compile(r"(?<![\w'])(%s|abort|fail|error|assertFail|throw|failWithStatus)(?![\w'])" % _NAMES)
STATEMENT = re.compile(r"^(\s*)((?:[A-Z]\w*\.)*)(%s)(?![\w'])(?!\s*:)" % _NAMES)
BOUND = re.compile(r"^\s*(?:[\w']+|_|\([^)]*\))\s*<-\s*(?:[A-Z]\w*\.)*(%s)(?![\w'])" % _NAMES)
BARE_FAIL = re.compile(r"^\s*(fail|abort|error|assertFail|throw|failWithStatus)\b")


# --- blanking comments and string contents --------------------------------

def _dashes_start_comment(src, i):
    """True when the dashes at i open a line comment, not an operator."""
    j = i
    while j < len(src) and src[j] == "-":
        j += 1
    before = src[i - 1] if i else " "
    after = src[j] if j < len(src) else " "
    return j - i >= 2 and before not in OPS and after not in OPS


def _block_end(src, i):
    """Index just past the nested {- -} comment starting at i."""
    depth, j = 0, i
    while j < len(src):
        if src.startswith("{-", j):
            depth, j = depth + 1, j + 2
        elif src.startswith("-}", j):
            depth, j = depth - 1, j + 2
            if depth == 0:
                return j
        else:
            j += 1
    return len(src)


def _string_end(src, i):
    """Index just past the string literal opening at i. Stops at a newline, so
    one stray quote cannot swallow the rest of the file."""
    j = i + 1
    while j < len(src) and src[j] not in '"\n':
        j += 2 if src[j] == "\\" else 1
    return min(j + 1, len(src)) if j < len(src) and src[j] == '"' else j


def _char_end(src, i):
    """Index past a char literal at i, or i + 1 when it is an identifier prime."""
    if i and (src[i - 1].isalnum() or src[i - 1] in "_'"):
        return i + 1
    m = re.compile(r"'(\\.|[^\\\n'])'").match(src, i)
    return m.end() if m else i + 1


def _blank(chars, i, j):
    for k in range(i, min(j, len(chars))):
        if chars[k] != "\n":
            chars[k] = " "


def mask(src):
    """The source with comments and string contents replaced by spaces."""
    chars, i = list(src), 0
    while i < len(src):
        c, j = src[i], i + 1
        if src.startswith("{-", i):
            j = _block_end(src, i)
            _blank(chars, i, j)
        elif c == "-" and _dashes_start_comment(src, i):
            j = src.find("\n", i)
            j = len(src) if j < 0 else j
            _blank(chars, i, j)
        elif c == '"':
            j = _string_end(src, i)
            _blank(chars, i + 1, j - 1)
        elif c == "'":
            j = _char_end(src, i)
            _blank(chars, i + 1, j - 1)
        i = j
    return "".join(chars)


# --- layout ----------------------------------------------------------------

def span(lines, i):
    """[start, end) of the statement beginning at line i.

    Daml uses layout: a statement continues while the following lines are
    indented MORE than it. Identical to daml_mutate.span, so the legacy and the
    generalised discovery agree on where a statement ends.
    """
    base = len(lines[i]) - len(lines[i].lstrip())
    j = i + 1
    while j < len(lines) and lines[j].strip():
        if len(lines[j]) - len(lines[j].lstrip()) <= base:
            break
        j += 1
    return i, j


# --- helper definitions ----------------------------------------------------

def _def_spans(mlines):
    """{name: (first line, past-the-end line)} for helpers defined at column 0.

    The body of `require` itself holds an `unless ... fail`. Mutating THAT would
    make every call site vacuous at once, which is not a test of any one check,
    so a helper's own definition is never mutated.
    """
    out = {}
    for i, line in enumerate(mlines):
        m = re.match(r"^(%s)\s*:" % "|".join(re.escape(n) for n in HELPERS), line)
        if not m:
            continue
        j = i + 1
        while j < len(mlines) and (not mlines[j].strip() or mlines[j][0] in " \t"
                                   or mlines[j].startswith(m.group(1))):
            j += 1
        out[m.group(1)] = (i, j)
    return out


def defined_helpers(texts):
    """Helper names defined in any of these sources whose body can refuse.

    A `require` that only formats a string is not a check. One whose body calls
    a failing primitive is, and then every call to it is a check.
    """
    found = set()
    for text in texts:
        mlines = mask(text).split("\n")
        for name, (a, b) in _def_spans(mlines).items():
            body = "\n".join(mlines[a:b]).split("=", 1)
            if len(body) == 2 and CAN_REFUSE.search(body[1]):
                found.add(name)
    return found


# --- discovery -------------------------------------------------------------

def _classify(mline, mtext, known):
    """(kind or None, reason). The kind when this line starts a recognised
    check, otherwise why it is not one."""
    m = STATEMENT.match(mline)
    if not m:
        return None, "not a statement start"
    qualifier, kind = m.group(2), m.group(3)
    if kind in HELPERS and kind not in known:
        return None, "unresolved helper `%s`: pass it as a known check if it is one" % kind
    if qualifier and kind in ("unless", "when", "ensure"):
        return None, "qualified call"
    if kind in ("unless", "when") and not FAILS.search(mtext):
        return None, "flow control: `%s` whose body never fails" % kind
    return kind, ""


def _unseen_reason(mline):
    """Why a check-like line that is not a recognised statement is unseen."""
    for pattern, why in ((BOUND, "bound result: deleting it would not compile"),
                         (BARE_FAIL, "an unconditional failure: the effect, "
                                     "not a guard")):
        if pattern.match(mline):
            return why
    return "check-like word in a form this tool does not recognise"


def _look(lines, mlines, i, kinds, known):
    """(kind, end, reason) for line i. `kind` is set only for a recognised,
    requested check; otherwise `reason` says why a statement line was not one,
    and is empty for a line that is not a statement at all."""
    is_statement = bool(STATEMENT.match(mlines[i]))
    a, b = span(lines, i) if is_statement else (i, i + 1)
    kind, reason = _classify(mlines[i], "\n".join(mlines[a:b]), known)
    if kind is not None and kind not in kinds:
        return None, b, "kind not requested"
    return kind, b, (reason if is_statement else "")


def _scan(lines, mlines, skip, kinds, known):
    """(found, why): the recognised checks, and the specific reason for every
    statement line that was looked at and not recognised."""
    found, inside, why = [], set(), {}
    for i in range(len(mlines)):
        if i in skip or i in inside:
            continue
        kind, end, reason = _look(lines, mlines, i, kinds, known)
        if kind:
            found.append((i + 1, kind, end + 1))
            inside.update(range(i + 1, end))
        elif reason:
            why[i] = reason
    return found, why


def helper_def_lines(source):
    """[(line, name)] for every line of a check helper's own definition that
    carries a check word. They are never mutated, and a count that left them
    out would be a count of something other than the source."""
    mlines = mask(source).split("\n")
    out = []
    for name, (a, b) in _def_spans(mlines).items():
        out += [(i + 1, name) for i in range(a, b) if ANY.search(mlines[i])]
    return out


def discover(source, kinds=ALL_KINDS, known=frozenset()):
    """(found, unseen) for one source file.

    found:  [(line, kind, end)] 1-based start, exclusive 1-based end, in order.
    unseen: [(line, reason, text)] every check-like line that is NOT in found.
    """
    mlines = mask(source).split("\n")
    lines = source.split("\n")
    skip = set()
    for a, b in _def_spans(mlines).values():
        skip.update(range(a, b))
    found, why = _scan(lines, mlines, skip, kinds, known)
    return found, _unseen(mlines, lines, skip, found, why)


def _unseen(mlines, lines, skip, found, why):
    covered = set()
    for start, _kind, end in found:
        covered.update(range(start - 1, end - 1))
    out = []
    for i, mline in enumerate(mlines):
        if i in skip or i in covered or mline.lstrip().startswith("import "):
            continue
        if ANY.search(mline):
            out.append((i + 1, why.get(i) or _unseen_reason(mline), lines[i].strip()))
    return out


def neuter(line, kind):
    """The replacement for the FIRST line of a statement of this kind, keeping
    its indent. The whole layout span is replaced by this one line."""
    indent = line[:len(line) - len(line.lstrip())]
    return indent + {"assertMsg": 'assertMsg "mutated" True',
                     "ensure": "ensure True",
                     "assert": "assert True"}.get(kind, "pure ()")


def main(argv):
    if len(argv) < 1:
        print(__doc__.splitlines()[0])
        return 2
    known = frozenset()
    if "--known-checks" in argv:
        known = frozenset(argv[argv.index("--known-checks") + 1].split(","))
    src = open(argv[0], encoding="utf-8").read()
    found, unseen = discover(src, known=known)
    for line, kind, end in found:
        print("  %-22s %s:%d-%d" % (kind, argv[0], line, end - 1))
    for line, why, text in unseen:
        print("  NOT SEEN %-34s %s:%d  %s" % (why[:34], argv[0], line, text[:40]))
    print("%d recognised, %d not seen" % (len(found), len(unseen)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
