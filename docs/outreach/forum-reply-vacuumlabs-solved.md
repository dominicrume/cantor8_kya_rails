# Second reply to Vacuumlabs, forum 9084

**What changed:** Arpit Karnatak raised the revert case on 18 October. On
19 October it is solved, in code, with tests, and the limitation is gone
rather than conceded.

## What "solved" means precisely, so the post does not overclaim

- A record now survives the work reverting. **Yes.** `testTheRecordSurvivesARevert`.
- The count is now complete. **Yes.** The number is taken in transaction one.
- The resolution cannot lie about the attempt. **Yes.** sha256 commitment.
- An attempt that never touches the journal is still invisible. **Unchanged**,
  and still stated in the code.
- Distinguishing "reverted" from "still in flight" needs an application-chosen
  timeout. **Still true.**

## Prior art the post must credit, because a reviewer will know it

- **Write-ahead logging.** Mohan et al., ARIES, ACM TODS 1992. The mechanism
  is theirs. The only difference is who reads the durable intention: WAL
  recovers a system, this informs an auditor.
- **Daml propose-accept.** The two-transaction shape is documented and
  standard. It exists there for authority, reused here for evidence.
- **Hyperledger Fabric** has retained failed transactions with a validation
  code for years. Own it in the post rather than have it raised.
- **Not** Sagas. Different problem.

---

## THE POST

Solved. It needed two transactions instead of one.

You were right that nothing written inside a transaction survives that
transaction aborting. That is atomicity, not a gap in the design. So the
record has to commit before the work, not alongside it.

Open the attempt in its own transaction. It holds nothing else, so nothing can
revert it. The work happens in the next transaction and consumes the attempt.
If that reverts, the attempt simply stays open.

An attempt left open is the evidence. The absence of a resolution is the
record.

The attempt carries a sha256 commitment over the action and detail, length
prefixed so the boundary cannot be moved afterwards. The resolution has to
match it, so you cannot open an attempt to move 900,000 and resolve it as a
refused request for 10. And an open attempt shows the auditor a position, a
time and a digest, nothing else, so an allowed action stays private.

What an auditor reconciles, all of it off the ledger:

    50  attempts, from the counter
    12  refusals, disclosed to them
     3  still open: tried, never resolved
    35  settled, and they learn nothing else about those

None of those numbers is mine.

Credit where it is due. This is write-ahead logging, which is Mohan et al.
1992, and the two-transaction shape is Daml's own propose-accept pattern used
for a different reason. Fabric has retained failed transactions with a
validation code for years, though that covers consensus-layer failures rather
than application policy. What is new here, if anything, is treating the
unresolved record as the artefact and binding it with a commitment.

Eleven scripts on it. Removing the commitment check or the counter both turn
named tests red.

step-0-refusal/daml/Attempt.daml. MIT, no dependencies past the standard
library.

Two things still open, so nobody is surprised later. An attempt that never
opens is still invisible, and nothing fixes that. And an open attempt cannot
tell you by itself whether the work reverted or is still in flight; that needs
a timeout you choose.

Thanks for the objection. It was the right one and it changed the design.
