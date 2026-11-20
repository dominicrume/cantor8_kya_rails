---
name: kya-guard-review
description: Use when the user wants to know whether their Daml tests would notice if a security check (an ensure clause or an assertMsg) were removed, asks "do my tests protect my guards", wants a coverage review of Daml contracts before shipping, or asks to write the missing tests. Runs the KYA guard review through the kya-check MCP server on a temporary copy, so the project is never edited.
---

# KYA guard review

Delete each `ensure` and `assertMsg` in a Daml package in turn, re-run the tests,
and list the checks that no test notices losing.

## Before you start

- The `kya-check` MCP server must be connected. If its tools are missing, tell the
  user to run, from the kya-rails folder:
  `claude mcp add kya-check -- python3 "$PWD/step-4-mcp/kya_check_mcp.py"`
- The Daml SDK must be on PATH, and the project's tests must already pass.
- You need two folders: the package with the contracts, and the package with the
  test scripts. Ask if you do not know which they are. Do not guess a parent folder.

## Run it

1. Call `kya_guard_review_start` with `src` and `test`. It answers at once with a
   `job_id`. The review runs on a temporary copy and takes minutes.
2. Tell the user it is running and that their project is not being touched.
3. Call `kya_guard_review_status` every so often until `state` is not `running`.
4. If `state` is `failed`, show `log_tail` and say what it means: usually the tests
   did not pass on the baseline.
5. If `finished`, report plainly: how many checks, how many have a named test, and
   list each unprotected check with its file and line. Give the path of the report.

## What to say, and what not to

- Say what it is: a coverage finding. A check with no failing test may still be
  correct. It means nothing would tell you if it stopped being so.
- Say what it does not prove. `does_not_prove` is in the result; read it out.
- Do not call a finding a vulnerability. Do not say the code is secure when every
  check is covered.
- Do not edit the harness, the record or the report. If the record does not verify,
  the server refuses to return it. Report that; do not work around it.

## If the user asks you to write the missing tests

Ask first. Then, for each unprotected check, write one test that fails without it
and nothing else. Use the rule's own message, because `submitMustFail` cannot tell
the rule you meant from another rule that fires on the same input:

```daml
refusedWith : Text -> SubmitOptions -> Commands a -> Script ()
refusedWith rule who cmds = do
  result <- trySubmit who cmds
  case result of
    Left (FailureStatusError fs) ->
      assertMsg ("refused, but not by the rule named \"" <> rule <> "\": " <> fs.message)
                (rule `isInfixOf` fs.message)
    Left _ -> assertMsg "refused by something other than a failed check in the choice" False
    Right _ -> assertMsg ("ACCEPTED, but the rule \"" <> rule <> "\" should have refused it") False
```

Pair every refusal with a control that is accepted, so a test cannot pass because its
setup was already broken. A failed `ensure` reads "Template precondition violated".
Then run the review again and show the before and after counts.
