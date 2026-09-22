# Pending update to the Canton Developer Hub listing

**Hold until [PR #160](https://github.com/canton-network-devs/Canton-Developer-Hub/pull/160)
is reviewed.** That one fixes link rendering for nineteen entries including
ours. Filing a third pull request at the same organisation, before the second
has been looked at, is volume rather than contribution.

`docs/dev-hub-entry.json` deliberately still matches the live listing, so
`tests/devhub_entry_check.py` keeps testing something true.

## Why it needs changing

The live description opens "Spending mandate for an AI agent enforced as
assertMsg fences in a Daml choice body". That is a feature list, and it reads
as a platform competing with the rails that already exist and are built by
people with banking licences. The position is the opposite: the layer
underneath one.

## The replacement

Their rule is one to two sentences, so this is two.

```
The evidence layer that sits under an agent platform: a platform decides what
an agent may do, and Know Your AgenticAI records what it tried and was
REFUSED, sealed so a counterparty can check it without trusting the operator.
Limits are enforced as assertMsg fences in a Daml choice body, every attempt
becomes a hash-chained receipt including the refused ones, the chain verifies
in a browser with no wallet or install, and refusals can be disclosed on their
own without the accepted payments behind them.
```

Nothing else in the entry changes. The five links stay as they are.
