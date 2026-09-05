# KYA Receipt Chain — one page

**A verifiable record of what an agent was *refused*, not only what it was
allowed — with the spending rules enforced in a Daml choice body and the record
bound to the ledger it came from.**

Requesting **1,200,000 CC development plus 250,000 CC for an independent Daml
review at M2**, quoted separately as a third-party cost, released on milestone
acceptance. 32 weeks. Full proposal: [`docs/dev-fund-proposal.md`](dev-fund-proposal.md).

---

## The problem, stated narrowly

Give an autonomous agent — or a human operator in another country — the
authority to pay, and today the answer everywhere is a key. A key has no cap, no
counterparty list, no expiry and no revocation. When the agent is wrong, or is
talked into something, there is nothing between it and the float.

Logs do not fix this. A log is written by the party you are trying to check,
records only what succeeded, and can be edited afterwards. What an auditor asks
for is the opposite: **what was attempted and stopped, in a record its author
cannot rewrite.**

## What already exists, and is running

| | |
| --- | --- |
| **92** | Daml test scripts; every choice we wrote is exercised |
| **30** | spending fences mutation-tested — delete one, a named test goes red |
| **3** | independent implementations of the format, conformant on 16 shared vectors |
| **22** | threats documented, including six the design does not defend |

- **Deployed and vetted on Cantor8 DevNet.** Package `kya-rails-mandate` 1.1.0
  passed Canton's upgrade check against its predecessor. Cap, counterparty
  allow-list, expiry, revocation and per-period limits are assertions in the
  `Charge` choice body — refused before a transaction can exist, so there is
  nothing to roll back.
- **Refusals returned by the validator, not by our code.** Two payouts inside
  the mandate accepted; then over-cap, unapproved payee, expired and
  post-revocation all refused, each quoting the assertion that stopped it.
- **The record is bound to its origin.** A hash chain proves nothing was edited;
  it says nothing about who wrote it, and a forged chain verifies green in all
  three implementations. The principal therefore publishes the chain head **and
  the receipt count** on-ledger — a truncated chain still verifies and only the
  count catches it. A forged chain now verifies perfectly *and* the ledger
  answers `NOT ANCHORED`.
- **Canton Coin moves under the mandate.** Authorised payouts settled; the
  payout to an account outside the allow-list moved nothing, because the charge
  was refused before a transfer existed.

## Check it in one command, on your own validator

Nothing above needs to be taken on trust.

```bash
export C8_CLIENT_SECRET=...     # yours, not ours
python3 tests/prove.py
```

It runs with **your** credentials against **your** DevNet, asks Canton to break
its own rules, then forges a receipt chain in front of you and shows the ledger
naming it as not ours. It writes a mandate and an anchor; it moves no coin
unless you pass `--move-coin`. Everything else is a read.

## Milestones

| | Deliverable | Weeks | CC |
| --- | --- | --- | --- |
| M1 | Specification hardening and a third implementation | 6 | 240,000 |
| M2 | Mandate library, per-period limits | 8 | 360,000 |
| M2a | Independent Daml review — third-party cost | — | 250,000 |
| M3 | Agent integration and reference deployment | 6 | 300,000 |
| M4 | Adoption, v1.1, workshop material | 12 | 300,000 |
| | **Total** | **32** | **1,450,000** |

Sized against awards this Committee has already made: an individual delivering
payment streams at 900,000 + 200,000, and a settlement reference implementation
at 1,100,000. This covers a longer period than either, and sits well below the
2,260,000 requested for a team delivering language SDKs.

Work to date has been unfunded and no retrospective payment is sought for it. It
is offered as evidence that the milestones are deliverable.

## What this does not claim

A proposal listing only its strengths should not be believed, so:

- **A stolen principal key defeats everything.** Out of scope, and the largest
  hole in the design.
- **Anchoring stops substitution, not deletion.** A chain can still be discarded
  entirely; publishing makes swapping it detectable, not withholding it.
- **No external adopter yet.** The three implementations are the applicant's
  own. The third was written from the specification alone rather than translated
  from the others — which tests whether the prose is sufficient, and it exposed
  an ambiguity that is now fixed and covered by a vector. That is rigour, not
  third-party uptake, and is not offered as such. M4 exists to change it.

---

Rume Dominic (O'Rume Dominic Uririe) · Aston University · creator of the KYA
Framework. Also filed: four findings against the Cantor8 hackathon toolkit, with
fixes, including a default-argument binding that sends the wrong ledger user and
returns a 403 naming neither the user nor the cause.
