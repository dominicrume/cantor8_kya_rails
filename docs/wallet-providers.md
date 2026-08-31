# Where do the addresses come from?

**Every address in this repository is a placeholder.** They are well-formed
examples with no keys behind them. Nothing here custodies anything, and the
system cannot receive a real deposit until that changes.

This is the gap between "the rules are tested" and "the desk is running", and
it is the largest one left.

## What the system needs from a provider

For each asset and network the desk trades:

1. **A receive address it controls** — for `DepositBook`, where customers send
2. **The ability to send** — for `ReleaseCrypto` on the reverse leg
3. **A confirmation signal** — did a deposit actually land, and is it final
4. **Segregation** — the desk's float distinguishable from a customer's deposit

Point 3 is the one people underestimate. Confirming a deposit by looking at a
block explorer on a phone is the operator making a judgement call, which is
the class of failure this whole project exists to remove. A provider that
pushes a webhook on confirmation is not a convenience; it is the difference
between the fence being enforced and being remembered.

## The three shapes, and what each costs

**Self-custody.** The desk holds the keys. Complete control, no counterparty,
and the entire operational security burden: key generation, backup, signing,
and the fact that a compromised laptop is a total loss. Viable for a desk with
a real security practice; ruinous without one.

**A custody provider.** Institutional wallet infrastructure with policy
engines and multi-approval. This is the shape that matches KYA Rails most
closely — their approval rules and the mandate say the same thing at two
layers. Expect business onboarding, due diligence, and pricing built for firms
larger than a starting desk.

**Exchange sub-accounts.** What most small desks actually use, because it is
free and immediate. The cost is counterparty risk (their solvency and their
freeze policy become yours), plus terms that frequently prohibit third-party
deposits — which is precisely what an OTC desk receives. Read that clause
before building on it.

## Shortlist as of August 2026

Named because a shortlist is more useful than a principle, and **every one of
these must be verified against your own case** — availability, terms and
pricing move faster than this file, and the questions below are how you check.

**Nigeria-facing, crypto in and naira out.** This is the shape that matches
the desk's forward leg most closely: accept a deposit, settle to a Nigerian
bank account, one API.

- **Breet** — 12+ assets, USDT and USDC across TRC20, ERC20, Solana, BNB,
  Polygon, Arbitrum and Base; wallet generation, payouts and **real-time
  deposit webhooks**; settles to NGN and GHS bank accounts. Custodial, so
  their solvency and freeze policy become yours.
- **Quidax Developer API** — buy, sell, hold and accept, with webhooks for
  deposits, withdrawals and fills. A Nigerian exchange, so read the
  third-party-deposit clause carefully.
- **XPayr** — worth understanding precisely, because it is **not a Breet
  alternative**. It describes itself as non-custodial infrastructure *for
  checkout and confirmation, not a custodial merchant wallet*: EVM, TRON and
  Solana, 0.5% per transaction plus gas, and **no naira settlement at all**.
  You bring your own wallet and your own off-ramp. What it gives you is the
  confirmation signal — which makes it a **deposit feed**, the crypto-side
  twin of a bank feed, rather than a way to receive and settle.
- **Coinremitter** — narrower, USDT TRC20 focused, invoices and withdrawals.

**Institutional custody.** The shape that matches KYA Rails most closely,
because a policy engine and a mandate say the same thing at two layers.
Expect institutional onboarding, due diligence and pricing built for firms
larger than a starting desk. Worth a conversation once volume justifies it,
not before.

**And the trade-off that actually matters.** Decentralising the crypto leg
does not decentralise the business. The naira sits in bank accounts, banks
freeze accounts far more readily than crypto processors do, and non-custodial
protects the half of the flow that is not the bottleneck. Choose custody on
key-management capability, not on ideology.

**A note on the trade-off.** The Nigeria-facing providers above are fast to
integrate and remove the custody burden. What they do not remove is
concentration: if the provider freezes, the desk stops. A desk of any size
eventually wants two, and the fences in this repository are indifferent to
which one is behind an address — which is the point of putting the rules on a
ledger rather than in an integration.

## Questions to ask any provider

- Which assets **and networks** — TRC20 and ERC20 USDT are different answers
- **Deposit webhooks on confirmation**, or must you poll?
- How many confirmations before a deposit is treated as final?
- Can you generate a **unique address per deal**? That solves attribution at
  the wallet layer instead of relying on the quote reference alone
- Memo/tag handling on chains that need one
- **Do the terms permit third-party deposits?** An OTC desk receives money from
  its customers. Many consumer terms forbid exactly that
- Withdrawal approval controls, and whether they can require a second person
- Nigeria and UK: which entity holds the funds, and under which regime
- What happens on a freeze, and who decides

## Where Canton sits, and the part that changes the plan

Canton Coin is separate from all of the above. An exchange account is not a
Canton party and cannot hold a mandate; a party needs a validator node.

**Canton MainNet is invite-only.** New validators require sponsorship and
approval — you cannot simply stand one up, and no amount of engineering
shortens that. The routes are:

1. **Node-as-a-Service.** An approved provider operates a white-label
   validator for you. The fastest path, and the realistic one for a desk this
   size.
2. **A custody provider with Canton pre-integrated.** Some already offer
   validator access alongside custody.
3. **Your own validator.** Production-grade environment, Kubernetes-based
   deployment recommended, plus the sponsorship and approval above.

This is why "launch on MainNet today" is not available even setting the
regulatory question aside: the network itself has a gate, and the queue for it
is not a technical queue.

**One useful consequence.** The Protocol Development Fund proposal and the
validator sponsorship question go to overlapping people. A Tech & Ops
Committee champion is worth asking about both.

## Until this is answered

The honest position, and it belongs in any demo:

> The rules are tested and the cycle is modelled end to end. The addresses are
> placeholders. No wallet provider is connected, so nothing here can receive or
> send real value on any chain except Canton DevNet, where it has been done and
> the balances checked.

That sentence costs nothing to say and is worth more than a claim that does
not survive one question.


## The Breet adapter, and one thing to raise with them

[`step-7-providers/breet.py`](../step-7-providers/breet.py) turns their
deposit webhook into a `ConfirmDepositSeen`. It is mostly refusals, because an
endpoint that confirms deposits is an endpoint that causes payouts.

**A note on their authentication.** Breet sends an `x-webhook-secret` header
to be compared against the secret in your dashboard. That is a **bearer
credential, not a signature**: anyone who obtains it can forge a confirmation,
and unlike an HMAC it is not bound to the request body, so it cannot tell you
the payload was not altered in transit. It is what the provider offers, so it
is what we check — with a constant-time comparison, alongside their IP
allowlist, and never as the only thing between a message and a payout.

The adapter therefore matches **every field against a deal we already hold**
before confirming anything: the address must be one we issued, the asset and
amount must match the quote, the event must be `trade.completed`, and
`isWrongAssetDeposit` refuses outright. A forged webhook with a stolen secret
still cannot invent a deal.

**Worth asking Breet for:** a **unique deposit address per trade**. Two open
deals sharing an address is ambiguous by construction, and the adapter refuses
rather than guessing which one the money belongs to — which is correct, and
also a customer waiting. A per-deal address removes the ambiguity at the
wallet layer instead of relying on the quote reference alone.

**And an HMAC signature.** Worth raising as a product request; a shared secret
is the weakest of the common schemes.
