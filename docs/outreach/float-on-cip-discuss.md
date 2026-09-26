# Float it on cip-discuss before writing the CIP

**Where:** https://lists.sync.global/g/cip-discuss/topics (join is open to anyone)
**Status:** not sent.

## Why this and not a finished CIP

`cip-0000` says it plainly: talk to the community early, because floating an
idea before writing a full CIP saves time. A finished CIP arriving cold from a
name nobody knows is easy to ignore. A short question is not.

## What the research says, so this is not a guess

- **118 CIPs exist. None of them mentions a refusal, a rejected attempt, or a
  record of a blocked action.** The eight that say "audit" mean security audits,
  auditors as institutional actors, or audited uptime. There is no prior art.
- **CIPs are open to any author.** The ballot sits with Super Validators, but
  the writing does not.
- **Standards Track needs a design document AND a reference implementation.**
  The reference implementation is the expensive half and it already exists:
  `canton-refusal-record` 1.0.0, one module, no dependencies beyond
  `daml-prim` and `daml-stdlib`, eight scripts including a lending protocol and
  a collateral engine using it.
- The gate is **two SV sponsors**. That is the same gate as everything else
  here, and it is people rather than a regex this time.

Paste this:

```
118 CIPs, and none of them covers what happens to a refused action.

In Daml a failed assertMsg aborts the transaction. So a blocked action
leaves nothing behind. What settled is on the ledger. What a rule stopped
is only in the application's own logs, written by the operator, about the
operator.

EU AI Act Article 12 and DORA both ask an institution to evidence that a
control operated. A control that operates produces refusals.

The pattern that fixes it is small. Do not abort. Commit either way.

If the rule passes, do the thing. If it fails, create a record and do
nothing else. Both paths commit. The id and the time then come from the
ledger. A named auditor observes the record. Nobody else does.

I have a reference implementation. MIT, one module, no dependencies
beyond daml-prim and daml-stdlib. The code is here.

https://github.com/dominicrume/cantor8_kya_rails/tree/main/step-0-refusal

Does this belong in a Standards Track CIP? Or is it better left as a
library people copy?
```

## Why it ends there

One question, and it is a real one. It might genuinely be better as a library:
a CIP that nobody adopts is worse than a package two teams use. Asking lets
somebody say so before a month goes into the wrong artefact.

It also does not ask anyone to sponsor anything. Sponsorship is a thing people
offer after they believe you, not a thing you request from strangers.

## The same question, separately, to one person

Federico_Rodriguez is a Canton Community Tech Partner and reviewed this design
already. Asking his OPINION is not asking him for a favour, and giving an
opinion on whether something belongs in the CIP process is close to the job.

If the list is quiet for a week, that is the second place to ask, on the
existing thread at forum.canton.network/t/9114 rather than in a new one.
