# KYA guard review as an MCP server

Your own agent (Claude Code, Cursor, anything that speaks MCP) asks whether your Daml
tests would notice if a check were removed. It runs on your machine, on a temporary
copy of your project, and tells you which checks nothing protects.

Install, from the kya-rails folder:

```
claude mcp add kya-check -- python3 "$PWD/step-4-mcp/kya_check_mcp.py"
```

Install the skill, so the agent knows when and how to use it:

```
mkdir -p ~/.claude/skills && cp -R "$PWD/step-4-mcp/skills/kya-guard-review" ~/.claude/skills/
```

Then ask: "Do my Daml tests protect my checks?" and give it the two package folders.

## What it promises

| Promise | Held by |
|---|---|
| Your project is never edited. The review works on a copy. | `tests/check_mcp_smoke.py`: the tree is byte-for-byte identical after, though the runner edits its copy |
| A symlink inside your project cannot make the review touch a file outside it | the same test, with a symlink pointing at a file outside the project |
| Only Daml files are copied: `*.daml`, `daml.yaml`, `multi-package.yaml`, `*.dar`. Never a symlink. An allowlist, not a list of secrets to skip | the same test checks exactly which files arrive |
| The copy is deleted when the job ends, on cancel, and when the server is stopped | the same test; a hard kill leaves a copy, and the next start removes copies older than a day |
| A folder that is your home or the system temp folder is refused, a project over 200 MB or 20,000 files is refused, and two packages in separate folders need a `multi-package.yaml` at their common root | the same test |
| A record whose seal chain does not verify, or is empty, is never returned | the same test |
| Text that comes from your project is returned as untrusted data, with control characters stripped and each field capped | the same test |
| Two reviews at most run at once, a timeout says it timed out, and cancel stops the whole process group | the same test |

## What passes through your agent

The review runs on your machine. But your agent reads the result, so **the findings (check
text, file names, line numbers) pass through your agent's model provider.** Your source
files do not, unless your agent chooses to read them. I have not checked whether the Daml
SDK itself fetches anything over the network during a build. Until that is checked, the
accurate claim is "this server makes no network call", not "nothing leaves your machine".

## What it does not do

- It needs the Daml SDK on PATH, and your tests must already pass.
- It is not an audit. It reports a coverage finding, not a vulnerability.
- The seal chain shows the record was not edited after it was made. It does not show who made it.
- **It has no billing.** Nothing here counts or charges uses. A counter on the customer's
  own machine would be a record the customer writes about themselves, so metering would
  have to be a service we run, and payment belongs outside this repository.
- The smoke test uses a fake runner (MOCKED) so it takes seconds. The real review,
  through this server, on a real package, is a separate run.
- Trail of Bits' Mewt also mutation-tests Daml (open source). They find different things;
  see `docs/findings-openzeppelin.md`, "On Mewt".

## Tools

| Tool | Does |
|---|---|
| `kya_guard_review_start` | copies the package, starts the review, returns a `job_id` at once |
| `kya_guard_review_status` | `running`, `failed` with the end of the log, or `finished` with counts, each unprotected check, a readable report and what the review does not prove |
| `kya_guard_review_cancel` | stops the review and deletes the copy |
