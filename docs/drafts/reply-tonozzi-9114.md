Destination: forum.canton.network topic 9114, reply to tonozzibeverley953 post #15
Written: 2026-11-12

You are right, and it kills the non-consuming version.

A non-consuming choice leaves an exercise event and no contract. Events are
prunable by whoever holds the participant, so the auditor's view of them is
telemetry, exactly as you say. A read-back that matches today says nothing
about next year.

That is why the count lives in an active contract. Pruning never removes an
active contract, so the journal survives a prune that erases every event
around it.

The cost is one create per refusal, which Leonid flagged on 9 November.
