Post-To: https://forum.canton.network/t/9323  (Reply at the bottom)

You were right on both counts, and I went and tested the rest of your list.

Implicit Archive is gated by the signatory line, so the owner alone fails. The
bypass is submitting as both, which succeeds with the counter at zero:
testSubmittingAsTheGuardianDefeatsIt.

Owner-controlled choices: you were right, and my suite had missed it because
the test wallet carried no choices at all. There is one that does now, and it
moves outside the journal with the guardian correctly on the signatory line:
testAnOwnerControlledChoiceStillBypassesTheJournal. It is a requirement on
implementers in the draft now, credited to you.

Keys I cannot test. The build targets LF 2.1.

Your last two points I cannot test either, with no participant and no
credential, and they are the ones I wanted to ask you about. Point five
especially. Is the confirming set visible to a reader anywhere after the fact,
so independence can be checked, or is it only ever an operational claim about
who runs which node?
