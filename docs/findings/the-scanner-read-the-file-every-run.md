# My scanner read the file every run and missed the breach

*24 October 2026. Every claim here is one command. The commands are at the bottom.*

**Published at
<https://dominicrume.github.io/cantor8_kya_rails/writing/defeated-by-punctuation.html>.**

That is a plain URL on the public web, served by GitHub Pages out of `docs/`,
with no account and no sharing setting between a reader and the page. It was
first put behind a share toggle on another service, which is not publishing:
a link most people cannot open is a draft with extra steps.

On 13 September an assistant debugging a failed push printed a live GitHub
token into my terminal. I wrote a rule that day. It says: never run a command
whose output is a credential, and it forbids `gh auth token` by name.

I then wrote a scanner to enforce it. It reads every tracked file on every
run. It has a positive control, because a scanner that finds nothing in a
clean repository looks exactly like a scanner that finds nothing at all.

Yesterday I found two of my own files running the command the rule forbids.

The scanner had read both of them, every run, for days. It passed every time.

Here is the line it could not see, and which you must never run:

```python
subprocess.run(["gh", "auth", "token"], capture_output=True)
```

The scanner searched for that command as plain text. The line above does not
contain it. It contains `gh`, then a quote, a comma, a space, then `auth`.

The rule was right. The scanner was right. The file was read. The match was
defeated by punctuation.

## Why the control did not save me

My positive control planted a file containing the forbidden command in the
form a shell script would use, which you must never run either:

```sh
gh auth token > /tmp/x
```

It matched, so the scan reported that it could see a real violation, and I
believed it. But a control only proves the scan can catch breaches **shaped
like the control**. Mine was shaped like a shell script. The breach was shaped
like a Python list.

The fix is four lines. Strip list punctuation, then match against both forms:

```python
def as_argv(line):
    for ch in "\"',[]()":
        line = line.replace(ch, " ")
    return " ".join(line.split())
```

And then plant both shapes in the control, not one.

I checked the fix the only way worth checking a test: I deleted it and
confirmed the control went red. It prints `the scan cannot find a planted one,
so 'clean' means nothing`. Then I put it back.

## The second one was worse, because it blamed the wrong thing

A different check in the same repository counts the Daml test scripts and
compares the number against the one printed in my README. For two days it
failed in CI with this:

```
FAIL daml scripts: README says 165, the file has 103
```

That reads like a stale claim. It is the exact kind of thing I have a rule
against. So I went to correct the README.

The README was right.

The check builds two Daml packages and counts the scripts in each. One of them
depends on an interface package that the check never built, and it ignored
`daml build`'s exit code. On a clean checkout the build failed, the test run
found nothing, the total came back 103 instead of 165, and the check reported
that as a false claim in my documentation.

A swallowed exit code was presented to me as dishonesty in my own writing.

It now builds in dependency order, and a failed build returns `-1` and prints
the compiler error. The failure message went from naming an innocent file to
naming the actual fault.

## The pattern

Three checks, all written carefully, all with a stated purpose, all wrong in
the same way: **each one reported confidently about something it had not
actually looked at.**

The scanner reported on text when the breach was in structure. The counter
reported on a claim when the fault was in a build. A third, my build
dashboard, reported `40 of 41 green` while a mutation sweep was running in
another process with files deliberately broken on disk. Three different
numbers in an hour, none of them measured on a quiet tree.

What they share is not a bug. It is that the thing doing the checking was
never checked in the form the failure would actually arrive in.

So the question I now ask any test I write is not "does it pass" and not even
"does it fail when I break the code". It is narrower than that:

**What shape will the real breach have, and have I ever planted that shape?**

A control in the wrong shape is worse than no control, because it buys
confidence at full price and delivers none.

## Check it yourself

Everything above is in one public repository, pushed before this was written.

```sh
git clone https://github.com/dominicrume/cantor8_kya_rails
cd cantor8_kya_rails

# the scanner, with both control shapes
python3 tests/security_lint.py

# break the fix on purpose; the control must go red
python3 - <<'EOF'
p = "tests/security_lint.py"
s = open(p).read().replace("if cmd in line or cmd in flat:", "if cmd in line:")
open(p, "w").write(s)
EOF
python3 tests/security_lint.py        # "the scan cannot find a planted one"
git checkout -- tests/security_lint.py

# the counter, from a clean state, in dependency order
rm -rf step-0-refusal/interface/.daml/dist step-0-refusal/.daml/dist
python3 tests/balance_lint.py         # 165, not 103

# the whole sweep, on a quiet tree
python3 tools/dashboard.py
```

The commit is
[f3b693a](https://github.com/dominicrume/cantor8_kya_rails/commit/f3b693a).
Its message says what was wrong, in the open, with the reason, because a
correction found by a reader costs more than one declared by the author.

## The limit of this

None of it ran on Canton DevNet. I do not have a credential yet. These are
local checks over Daml packages and Python, and that is all they are.

What is on a public registry is the Daml work they guard, and that part is
reproducible: the two published packages rebuild byte for byte from committed
source, and the digests match what a stranger pulls anonymously.

---

*Rume Dominic. Creator of the Know Your AgenticAI framework. Third place,
Cantor8 Build on Canton, 29 August 2026.*
