Post-To: https://forum.canton.network/c/developer-support/57  (New Topic.)
Title: RFP 27 has three open proposals. Are they three things or one thing
three times?

Three proposals are open under RFP 27 and nobody outside the committee has
assessed whether they overlap. I wrote one of them, so I am the worst
possible person to answer that and the best placed to put the question. The
Foundation's COO asked me on 5 November to bring it here rather than argue
it on a funding thread, and she is right that it is a technical question.

Declared interest: #860 is mine.

Where each one sits:

| | #788 LedgerShield | #860 Refused actions | #866 OS Ledger |
|---|---|---|---|
| Layer | in front of the Ledger API | inside Daml | after the ledger |
| Refuses | an API request, by OPA policy | an action, by a Daml check | nothing; it reports |
| Record goes to | DuckDB, in the proxy | a contract, on the ledger | journal entries plus an attestation |

The claim is that a request LedgerShield rejects never reaches Daml, an
action Daml refuses never reaches the books, and a period OS Ledger closes
contains neither. Full assessment, with every number as a command you can
run yourself:
github.com/dominicrume/cantor8_kya_rails/blob/main/docs/rfp-27-overlap.md

One fact decides most of it, and it is not mine. Leonid set it out on 30
October: a failed assertion aborts inside the submitter's own
interpretation, so nothing is sent, no mediator verdict exists and Scan has
nothing to publish. OS Ledger ingests UpdateService and StateService, which
carry committed activity. So a refused action produces no update and cannot
appear in a close built from those streams. That is not a defect in #866. It
is a property of the data, and it is why "what did your controls block" has
to come from somewhere other than a finance close.

Which leaves the real question, and it is the one I would like attacked:
should a refusal be on the ledger at all?

Three honest answers to the three objections. On semantics, you cannot
record a failed transaction, so the design makes the refusal a successful
one whose content is that an action was attempted and stopped, constrained
so the record cannot flatter its author
(testTheResolutionCannotLieAboutTheAttempt, testRefusalsCannotExceedAttempts).
On privacy, an attempt is a salted commitment and disclosure is one-sided:
an allowed action reveals nothing, a refused one opens
(testSettlingRevealsNothing, testAStrangerSeesNoAttempt), and with no
auditor named there is no disclosure at all. On cost, there are two
mechanisms giving an identical reading at different storage, one contract
per refusal against none: testTheCostOfBothMechanisms runs twenty through
both. That is a contract count in Daml Script, not a fee measured on DevNet.

What does not work, so you hear it here first. This counts refusals by a
cooperating actor and does not count attacks. An attacker with one stolen
key skips the attempt, the ledger refuses during interpretation, and nothing
is counted. testAnAttackerWithOneStolenKeyLeavesNoCount shows the auditor
seeing nothing after five attempts. Five thousand blocked attacks and zero
look identical.

Georgi Radev narrowed it again on 4 November: the ledger shows authority was
split between named parties, and nothing at the protocol level will show
those parties were independently operated.

None of it has run on DevNet. I have never held a credential.

So: three things or one thing three times? And if your organisation sits on
the Tech and Ops Committee and thinks the middle layer is worth owning, say
so here.
