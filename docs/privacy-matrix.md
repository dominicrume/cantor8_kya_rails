# Privacy matrix

Who signs each contract, who observes it, and who is **excluded**. The
exclusions are the design: on Canton a non-observer receives nothing —
not an encrypted payload, not a hash, zero bytes — so a party absent
from a row cannot see that the contract exists.

*Generated from the Daml by `tests/privacy_matrix.py`. CI fails if this
file drifts from the source, because a privacy claim written by hand is
a claim and one read out of the contracts is a fact.*

| Contract | Signatories | Observers | Excluded |
| --- | --- | --- | --- |
| `DepositBook` | `principal` | `operator` | `depositFeed`, **everyone else** |
| `DepositInstruction` | `operator` | `customer`, `depositFeed` | **everyone else** |
| `OffTakerBook` | `principal` | `operator` | **everyone else** |
| `SupplyLeg` | `operator` | — | **everyone else** |
| `NairaBook` | `principal` | `operator` | `bankFeed`, **everyone else** |
| `InboundDeal` | `operator` | `customer`, `principal`, `bankFeed` | **everyone else** |
| `Release` | `operator` | `customer` | **everyone else** |
| `ChargeRecord` | `owner`, `spender` | `payee` | **everyone else** |
| `KyaMandate` | `owner`, `spender` | — | **everyone else** |
| `KyaMandateProposal` | `owner` | `spender` | **everyone else** |
| `Settlement` | `operator` | `customer` | **everyone else** |
| `PayoutBook` | `principal` | `operator` | **everyone else** |
| `Quote` | `operator` | `customer` | **everyone else** |

## What the exclusions buy

**The operator never sees the desk's margin.** `KyaMandate` and the books
are signed by the principal; an operator observes only what it must act on.

**A payee sees their own payment and nothing else.** `ChargeRecord` has
`observer payee`, so a counterparty can verify what they were paid without
gaining sight of the cap, the float, or any other payee.

**A watcher cannot see a quote.** This is the structural difference from a
public chain, where a deposit address is monitorable by anyone and that is
what makes a false claim cheap to fabricate. On Canton the counterpart to a
deal is visible only to its parties.

**A feed sees one deal and can confirm one fact.** The bank feed and the
deposit feed observe only the deals they must confirm, and neither can pay
anyone. Narrow sight and narrow authority, deliberately matched.

**The customer sees their own deal.** `DepositInstruction` and `Release`
carry `observer customer`, so "you sent me the wrong address" and "I was
never paid" are questions with answers on the ledger rather than arguments
in a chat log.

