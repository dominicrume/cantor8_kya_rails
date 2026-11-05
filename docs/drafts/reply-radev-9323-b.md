Post-To: https://forum.canton.network/t/9323  (Reply at the bottom)

That last line is the one I needed, and it splits the claim in two.

Who is named is on the ledger. The guardian and the auditor are signatories
of the journal, so a reader of the contract sees which parties they are with
no Admin API access and no topology export.

Who ran their node is not, and that is where this stops. Eligibility is
recoverable from PartyToParticipant. Participation in a particular
transaction is not recoverable at all, and distinct node IDs are not distinct
operators.

So the honest claim is that the specification proves authority was split
between named parties, not that those parties were independently operated.
Independence stays an off-ledger assertion.

Both halves are a test now rather than a sentence:
testTheLedgerNamesThePartiesAndNotTheirOperators. It reads the four parties
off the contract, checks the guardian is neither the actor nor the auditor,
and then rebuilds the payload naming every field, so the day anyone adds an
operator or topology field it stops compiling and the limit has to be
rewritten by hand instead of quietly outgrown.

Third time you have made this narrower. Thank you.
