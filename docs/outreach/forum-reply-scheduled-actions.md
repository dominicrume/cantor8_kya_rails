# Reply to Archana Nigam, forum 9314

**Thread:** https://forum.canton.network/t/implementing-scheduled-and-recurring-actions-in-daml-3-5
**Posted:** 17 October 2026, 09:41, by `nigam_archana`. App Development. **Zero replies.**

Her use cases are EOD trade close, monthly interest payments, and maturity
settlement. All three are regulated, repeating financial processes.

## Why answer this one

She asked four direct technical questions and nobody has answered any of them
in two days. Two of them land on exactly what this repository is about, and the
other two have first-party documented answers that most people get wrong.

Every claim below is a quote from a current primary source or a stated
observation. Nothing is from memory.

## The two claims to hedge, and why

- **No release note announces the removal of Daml Triggers.** The deprecation
  notice is in the 2.10 docs, and the absence from 3.x is established by the
  source tree and the docs sitemap, not by a Digital Asset statement. So the
  post says what was observed rather than claiming a documented removal.
- **Vacuumlabs' delegated automation is an unfunded Dev Fund proposal seeking
  a champion, not shipped code.** Calling it a product would be false and would
  also embarrass them.

---

## THE POST

Archana, taking your four in order.

**1. Built-in scheduler: no.** The docs are explicit about why:

> "Daml code has no independent thread of execution. Contracts on the ledger
> are passive records of synchronized data and rights specifying who can
> advance the shared workflows. These workflows remain static until advanced
> by external components. Any action on the ledger must be initiated by
> external components."

https://docs.canton.network/appdev/deep-dives/app-architecture-design

Canton does have a cron scheduler on the admin API, but it drives pruning, not
command submission. Worth knowing before somebody points you at it.

**2. Daml Triggers: deprecated, and not in 3.x.** The 2.10 docs say:

> "Daml Triggers are deprecated and are not supported in the next major
> release of Daml Enterprise."

And they are gone from the tree. `sdk/triggers` is present at tag `v2.10.6`
and absent at `v3.4.11`, at the 3.5 snapshots and on `main`. The current docs
site has no triggers page anywhere. I could not find a release note announcing
the removal, so that part is an observation rather than a quote.

Either way they would not have helped here. Triggers reacted to ledger events.
There was never a time-based one.

**3. Recommended pattern: your own backend, polling PQS.** Same architecture
page:

> "PQS is the recommended path for automation and integration components to
> access ledger data."

> "it is recommended to modularize it into retriable tasks"

> "The entire code block that processes the task should be retried, not just
> the ledger command submission within the block."

So: scheduler fires, query PQS for what is due, submit through the Ledger API,
and retry the whole block so a retry sees current state. I could not find an
official sample, only that prose.

**4. External scheduler: yes, and the choice barely matters.** Cron, Quartz,
Temporal and Airflow all work. What matters is idempotency, because the job
will fire twice eventually.

**One gotcha that will cost you if you miss it.** Do not gate the choice with
`getTime`. In 3.x calling it pins the ledger time, which constrains
preparation and submission to within the tolerance, 1 minute by default. Use
the deadline helpers instead:

- `assertWithinDeadline` and `assertDeadlineExceeded` in `DA.Assert`
- `isLedgerTimeGE` with `isLedgerTimeLT` in `DA.Time` for a window

The docs say these "do not constrain the time bound between transaction
preparation and submission."

https://docs.canton.network/appdev/modules/m3-working-with-time

**And one thing worth deciding early rather than in an audit.** When the
scheduler fires outside the window, the assertion aborts the transaction and
nothing commits. So when someone asks next month whether the interest run
happened on the 1st, the ledger holds no record that it was attempted and
refused. For EOD and interest that is an audit question rather than a
scheduling one. Either keep a good off-ledger log or make the refusal commit
as its own contract. Both are defensible. Pick deliberately.

Vacuumlabs have a Dev Fund proposal for delegated automation with cron and
on-chain checks before execution, which may be worth watching:
https://forum.canton.network/t/9084. It is a proposal seeking a champion, not
shipped code.
