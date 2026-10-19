# Second reply to Vacuumlabs, forum 9084

Arpit raised the revert case on 18 October. Solved on 19 October, then broken
and fixed twice more the same day by reviewing it as an attacker.

## Why the post names its own flaws

The first version of this post claimed a clean win. Then a review found that
the commitment bound but did not hide, and that signatories could archive the
evidence. Both would have failed an institutional security review.

**A post that names its own two flaws and shows the fix is worth more to this
audience than one that claims a clean win.** Everyone reading it has shipped
something broken. Nobody believes the clean win.

## What must be credited, because a reviewer will know

- **Write-ahead logging.** Mohan et al., ARIES, ACM TODS 1992.
- **Daml propose-accept.** The two-transaction shape, documented and standard.
- **Hyperledger Fabric**, which has retained failed transactions with a
  validation code for years.
- **Not** Sagas. Different problem, and citing it would be wrong.

---

## THE POST

Solved, and then broken twice by reviewing it properly. All three are worth
writing down.

**The fix.** Nothing written inside a transaction survives that transaction
aborting. That is atomicity, not a gap. So the record has to commit before
the work.

Open the attempt in its own transaction. It holds nothing else, so nothing can
revert it. The work happens next and consumes it. If that reverts, the attempt
stays open, and an attempt left open is the evidence. The absence of a
resolution is the record.

**First thing I got wrong.** The attempt carried a sha256 commitment over the
action and detail, and I claimed it revealed nothing. It did not hide at all.
A commitment needs binding and hiding; I had binding. sha256 over "withdraw"
and a round amount is brute-forced in seconds by anyone who guesses the
format, and payments are exactly the low-entropy case where that works. It now
takes a random salt held off the ledger and revealed at resolution.

**Second thing I got wrong, and I had not tested it.** Daml's implicit
`Archive` is controlled by the signatories. Both parties on the attempt are
signatories, and in the ordinary case one firm controls both. So the subject
of the evidence could delete it, and an auditor querying active contracts
would see a clean ledger.

That cannot be prevented. So every legitimate ending now mints a small
resolution marker carrying the position and the outcome kind, nothing else.
Deleting an attempt then leaves a numbered hole:

    attempts      50   monotonic counter, cannot be rewound
    resolutions   47
    still open     2
    ------------------
    unaccounted    1   archived with no resolution

That last line is the finding. The marker leaks nothing new, because anyone
who can count already knew settled equals attempts minus refusals minus open.

**Three I could not fix, so they are documented.** Nothing forces an attempt
to be opened before the work; a second path to the asset bypasses all of it.
The open time is ledger time, so the submitting participant has latitude
inside the skew window. And opening attempts is free, so noise can bury a real
unresolved one.

**Credit.** This is write-ahead logging, Mohan et al. 1992, with the durable
intention read by an auditor rather than by a recovery manager. The
two-transaction shape is Daml's own propose-accept used for a different
reason. Fabric has retained failed transactions with a validation code for
years, though that covers consensus-layer failures and not application policy.
What is left that is arguably mine is treating the unresolved record as the
artefact and binding it with a salted commitment.

Fifteen scripts on it, 37 on the package. Dropping the salt, removing the
minimum salt length, or minting a marker at the wrong position each turn named
tests red.

step-0-refusal/daml/Attempt.daml. MIT, no dependencies past the standard
library.

Thanks for the objection. It was the right one, and the two things it led me
to find were worse than the one you raised.
