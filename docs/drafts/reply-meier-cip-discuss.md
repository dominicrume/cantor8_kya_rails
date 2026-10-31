Post-To: https://lists.sync.global/g/cip-discuss/message/910  (log in, press Reply, keep the subject)

Simon, you are right on both counts about the mechanism, and I had built only
the expensive one.

RefuseSignalled is in now. No contract, and the arguments reach the exercise's
informees, the auditor included, because a signatory is an informee of every
exercise on a contract. It follows EventLog from CIP-0112.

What I added is the measurement of what it costs. Pruning never removes an
active contract, and a pruned node cannot serve events preceding the prune. So
a signalled refusal and a deliberately withheld one leave an identical active
contract set, and the participant that can prune belongs to the party the
record is about. Twenty refusals each way: twenty contracts against one, with
both auditors returning the same count and the same positions. One test per
half, and the cheap one was checked by making it create a record.

So the draft now says: signal when somebody is watching now, record when
somebody will ask later.

On whether it needs a CIP. Vacuumlabs, Dev Fund #627, wrote on 18 October:
"since there's no standard pattern out there to commit them on-chain, it
didn't make sense to implement it within this proposal." Their refusal logs
sit off-ledger, held by the party they describe, because no standard existed.
That is the coordination I think is missing, and EventLog is the precedent: a
holdings change is application-level too, and was standardised so one client
can read any issuer.
