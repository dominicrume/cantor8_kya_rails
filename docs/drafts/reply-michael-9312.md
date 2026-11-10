Michael is right that locking holdings is not enough. A compromised node can
exercise any choice the party controls.

Which is why the second signature belongs on the contract, not on the
holding. Put the co-signatory on the signatory line and a create needs their
authority, so a node holding the party's key cannot bring the contract into
existence at all. No token standard involvement, because it is contract
authorisation rather than holdings.

Tested: `testASecondJournalIsPrevented` in step-0-refusal.

The limit, stated because it is real: if one submitter holds both
authorities it is defeated. `testSubmittingAsTheGuardianDefeatsIt`.

Colin's co-sign-per-spend cost applies here too.

https://github.com/dominicrume/cantor8_kya_rails/blob/main/step-0-refusal/test/daml/JournalTest.daml
