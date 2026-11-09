Post-To: https://forum.canton.network/t/9114  (Reply at the bottom)

That is the right objection, and it has a number rather than an answer.

There are two mechanisms now. Simon Meier made the same point on cip-discuss
on 30 October and pointed at the EventLog in CIP-0112, so the second one is a
non-consuming choice. Twenty refusals through both: recording leaves twenty
contracts, signalling leaves none, and the auditor reads back the same count
and the same positions from either. That is testTheCostOfBothMechanisms.

The cost of the cheap one, since you did not ask and should have it. Once the
events are pruned, a signalled refusal and a refusal whose reason was withheld
are the same thing on the ledger, and the party who can prune is the party
being audited. That is testASignalledRefusalLooksWithheldOnceEventsAreGone.

So your big if buys survival of pruning, and nothing else. Worth it for
evidence, not for telemetry.
