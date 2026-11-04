Post-To: https://forum.canton.network/c/developer-support/57  (New Topic.)
Why here and not a SIG category: the twenty SIG categories hold eleven topics
between them. App Development holds 3,417, and it is where Georgi Radev,
Leonid, PREDGE and Simon Meier have each already corrected this work.
Title: Should a refused action leave a record on the ledger? Privacy, cost
and semantics

Amanda Martin asked me on 5 November to bring this to the forum rather than
keep it on a funding proposal, and she named the three things worth arguing
about: privacy, cost, and whether it is semantically right at all. She is
correct that those are the questions, so here they are with what is built
against each.

Declared interest: I wrote #860. The assessment below compares it with two
proposals competing for the same RFP.

**The three RFP 27 proposals sit in different places.** #788 LedgerShield
refuses an API request in front of the Ledger API. #860 refuses an action
inside Daml. #866 OS Ledger reports committed activity afterwards. A request
LedgerShield rejects never reaches Daml; an action Daml refuses never reaches
the books. Full version, with the numbers as commands you can run:
github.com/dominicrume/cantor8_kya_rails/blob/main/docs/rfp-27-overlap.md

**Semantics first, because the others depend on it.** You cannot record a
failed transaction. Leonid established why on 30 October: a failed assertion
aborts during the submitter's own interpretation, nothing is sent, no
mediator verdict exists, and Scan has nothing. So the design does not record
a failure. It makes the refusal a successful transaction whose content is
the fact that an action was attempted and stopped, and then constrains it so the record cannot
flatter its author: testTheResolutionCannotLieAboutTheAttempt,
testRefusalsCannotExceedAttempts, testArchivingAnAttemptLeavesANumberedHole.

**Privacy.** An attempt is a salted commitment, not plaintext, and disclosure
is one-sided by construction: an allowed action reveals nothing, a refused
one opens. testSettlingRevealsNothing, testRefusingDisclosesTheRefusal,
testAStrangerSeesNoAttempt, testOnlyTheNamedAuditorSeesIt. The auditor is
optional, and with none there is no disclosure at all:
testNoAuditorMeansNoDisclosure.

**Cost.** Simon Meier's objection, and it has an answer. There are two
mechanisms and they give the auditor an identical answer at different
storage: recording is one contract per refusal, signalling is none.
testTheCostOfBothMechanisms runs twenty refusals through both and asserts
the auditor's reading is the same while the contract count is twenty against
zero. That is a contract count in Daml Script, not a fee measured on DevNet.

**The half that does not work, so you hear it from me.** This counts refusals
by a cooperating actor. It does not count attacks. An attacker holding one
stolen key skips the attempt and exercises directly, the ledger refuses during
interpretation, and nothing is counted.
testAnAttackerWithOneStolenKeyLeavesNoCount makes five attempts and shows the
auditor seeing nothing. Five thousand blocked attacks and zero look identical.

None of it has run on DevNet. I have never held a credential.

Two questions. Which of the three objections do you think is fatal rather
than merely a cost? And a Champion has to come from a Tech & Ops Committee
organisation, which Amanda confirmed on 5 November she cannot assign, so if
yours is one and this is worth sponsoring, say so here.
