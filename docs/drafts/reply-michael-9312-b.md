Destination: forum.canton.network topic 9312, reply to Michael post #9
Written: 2026-11-12

Agreed, and that is a boundary I should state more plainly.

The guardian never goes on a holding. It goes on the journal and the attempt
record, which are contracts I author, and the asset is wrapped so it moves
only through a choice that writes a journal entry first.

The wrapping is the weak point, not the signatory line.
testAnOwnerControlledChoiceStillBypassesTheJournal shows why: a consuming
choice archives on the controller's authority alone, so one ordinary
owner-controlled choice moves the asset and the journal stays at zero.

That is a specification hole, not a code bug, so the fix belongs in the CIP as
a requirement on implementers.
