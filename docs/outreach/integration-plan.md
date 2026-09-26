# How the integration milestone gets done

The Dev Fund milestone is **two Canton applications the applicant does not
own**. The package that makes a yes cheap exists. Nobody has been asked.

This is the plan for asking: who, when, what, and what makes us stop.

## Who: Moonsong Labs, and it is not close

`Moonsong-Labs/canton-vaults` and `Moonsong-Labs/canton-apps`. Both public.

Checked, not assumed:

- **184 `assertMsg` fences in production code**, tests excluded. Every one is
  a refusal that leaves nothing on the ledger.
- They are **reference implementations**. `canton-apps` describes itself as
  reference implementations for stablecoin issuance with programmable transfer
  restrictions. Other people copy reference implementations, so anything
  adopted there propagates.
- **Federico_Rodriguez works there**, is a Canton Community Tech Partner, and
  read this design unprompted on the forum, found the real hole, and specified
  the fix. He is already convinced of the idea.
- Moonsong has been a listed **Canton Ecosystem Service Provider** since June
  2026 and sells Canton engineering to financial institutions.

### The one example to lead with

`canton-vaults/patterns/01-vault-access/daml/AccessRequest.daml`, lines 36-38:

```daml
assertMsg "attestation is from another manager"
assertMsg "attestation is for another depositor"
assertMsg "attestation does not cover this vault"
```

A depositor is refused access to a vault. The transaction aborts. **Nothing is
written.** A custodian asked "show me everyone who was refused access to this
vault last quarter" has their own logs and nothing else.

One file. Three lines. Not a survey of their repository.

## When: after the CIP float, not before

The float asks for an **opinion**. This asks for **work in their codebase**.
Those are different sizes of request and doing the big one first spends the
relationship.

Order:

1. Float the CIP idea on `cip-discuss`. Costs them a reply.
2. If Federico engages there, or on the forum thread, the door is open.
3. Only then, the integration ask.

If the float gets no response at all in two weeks, ask anyway. A quiet mailing
list is not a no.

## What: ask, do not deliver

**Do not audit their 184 fences and arrive with a report.** That is exactly the
`daml-finance` mistake this project already made and wrote a rule about:
uninvited work aimed at someone whose help you need is pressure wearing the
costume of a contribution.

Ask whether it is wanted. Offer one file. Let them say where.

Paste this, on the forum thread where he already replied, not in a new one:

```
Separate question, and no pressure either way.

I looked at canton-vaults. In AccessRequest.daml a depositor refused
access to a vault leaves nothing behind, because the assertMsg aborts the
transaction.

Would a pull request adding a refusal record to that one file be useful
to you? Or is it the wrong shape for a reference implementation?

I would rather ask than send something you did not want. If yes, one
file, one pattern, and you tell me where it belongs.
```

## The second integration

One is not two. Candidates, in order, all public and all active this month:

| | why | risk |
|---|---|---|
| `SynfiniDLT/daml-tokenization-toolkit` | 8 stars, real tokenization infrastructure, the most-used non-vendor Canton repo found | no relationship at all |
| `intelliDean/refcanton` | private debt refinancing, pushed today, a refused refinancing is a real audit question | one person, may go quiet |
| Pearl Digital P3 contracts | he invited us to look, and it is a stablecoin issuer | GitLab repo is private, and he has not replied in 13 days |

**Not OpenZeppelin.** Checked: every pull request ever merged into
`canton-contracts` is from their own staff. One outside contributor has one
unmerged PR. The three findings issues we filed there have had no reply in
nineteen days. It is the wrong door, however good the fit looks.

## What makes us stop

Written down now, while it is cheap to be honest.

- **Two refusals from Moonsong** and it is not the right target, whatever the
  code says.
- **No integration accepted by 31 December 2026** and the milestone does not
  hold. The proposal should say so rather than carry a promise.
- **Any sign we are pushing.** One ask, one follow-up if invited, then stop.
  THE-RULES: an update is welcome, a debt collector is not.
