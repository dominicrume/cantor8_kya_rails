---
name: secret-hygiene
description: Credential handling for this repository, written after two live leaks. Use before running any authenticated command, any diagnostic against an authenticated endpoint, any release, or anything touching tokens, addresses or ledger credentials. The test is not which command it is, it is whether a secret went in.
---

# Secret hygiene

Two credentials have been printed into transcripts here. Both commands looked
safe. The abstraction that failed was the list of forbidden commands.

## A secret in means tainted out

Whenever a credential is passed **into** a command, its output is tainted until
proven otherwise, and it is never printed. Not the body, not the verbose log, not
the error. Print the HTTP status, a boolean, a length, or a named response header.
Nothing else.

    python3 tools/authed.py <source> <url> [headers...]

It discards the body with `curl -o /dev/null` **before** it can be seen, rather
than fetching it and filtering after, because a filter can be forgotten and a
discard cannot. If a field is genuinely needed from a response body, add a named
extractor to that tool that returns a boolean or a length, never the value.

## Three traps, all real

- **Token exchanges hand the credential back.** `ghcr.io/token` returns the base64
  of the PAT you sent it as its bearer token. A request that looks like a
  permissions check returns the secret.
- **`--verbose`, `--debug` and `-v` on anything authenticated** print the
  Authorization header.
- **Error messages quote the request.** A failing authenticated call often echoes
  what it sent.

## Never run

`git credential-* get`, `gh auth token`, `cat ~/.netrc`, `env | grep -i secret`.
To check whether a credential exists, print its length or a boolean.

The dates matter because they show the pattern. On 13 September 2026 an assistant
debugging a failed push ran `git credential-osxkeychain get` and printed a live
GitHub OAuth token. The rule then said "no secrets in this repo", every scanner
reads files, and nothing covered a command whose entire purpose is to emit a
credential to stdout. On 23 October 2026, **hours after reading a rule forbidding
exactly that**, a diagnostic against ghcr.io's token endpoint printed a live
classic PAT. The command was not on the forbidden list because the forbidden list
was the wrong abstraction.

## When it happens anyway

Say so immediately, name the credential, and tell the owner to revoke it before
anything else. A leaked secret reported in the same minute is an incident. One
noticed later is a breach.

## Addresses are credentials too

No wallet address a wallet would accept may exist anywhere in this tree,
including in a doc, a comment, a test fixture or a commit about to be made.

    python3 tests/no_real_addresses.py

It decodes Base58Check, EIP-55 and bech32 and fails on anything spendable, with
positive controls proving the validators and the walk can both say yes. This
exists because the customer screen served the USDT TRC20 contract address, where
coin is unrecoverable, for two weeks behind a QR code, a "Send exactly" label and
a copy button, with nothing saying it was a demo. It survived three audits,
including two run the same day it was found.

## Do not escalate scope on your own

`gh auth refresh` is the owner's decision. When a token lacks a scope, report the
limit and the alternative. On 9 November 2026 reading the Dev Fund project board
needed `read:project` and reading team membership needed `admin:org`. Both were
reported as limits rather than escalated, and the board is public in a browser.

## Releases

Build from committed code and never the working tree. List every file that would
go public. Scan the built artefacts for secrets **with a positive control proving
the scan reads them**. Install the artefact into a clean environment and run it.
A PyPI version number cannot be reused once taken.

Nothing is published to PyPI, npm, GitHub Pages or any public index unless the
exact package name and version has been stated and approved in that message.
"Publish it" is not approval. "Publish knowyouragenticai-receipts 1.0.0" is.

## Feedback contract

Report: which commands received a credential, what was printed from each (status,
boolean, length or header name only), and a one-line confirmation that no body or
verbose output was displayed. If a secret was exposed, that sentence comes first,
before anything else in the reply.
