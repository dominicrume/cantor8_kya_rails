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

**I am not naming vendors.** Which providers serve Nigeria and the UK, at what
price, under what terms, changes faster than this document can, and the wrong
answer here is expensive. What follows is how to interrogate whichever ones
you shortlist.

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

## Where Canton sits

Canton Coin is separate from all of the above. A Canton party needs a
**validator node** or a hosted validator; an exchange account is not a Canton
party and cannot hold a mandate. Moving the desk's own CC under a mandate on
MainNet requires that node first.

## Until this is answered

The honest position, and it belongs in any demo:

> The rules are tested and the cycle is modelled end to end. The addresses are
> placeholders. No wallet provider is connected, so nothing here can receive or
> send real value on any chain except Canton DevNet, where it has been done and
> the balances checked.

That sentence costs nothing to say and is worth more than a claim that does
not survive one question.
