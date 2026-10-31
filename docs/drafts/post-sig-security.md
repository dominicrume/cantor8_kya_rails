Post-To: https://forum.canton.network/c/sigs/sig-security/79  (New Topic. Title: "Refusal evidence on the ledger: what a stolen single key does and does not leave behind")

The 26 October advisory sent me to test something rather than to read it.
It says: "Start monitoring the network for transactions signed with the
compromised key." That is an evidence instruction, and I had been building an
evidence package for months without ever asking what mine does when one key
is stolen. So I asked. The answer is half good and I would rather you heard
the bad half from me.

What is built. Two Daml packages, MIT, SDK 3.4.11, target LF 2.1, no
dependency beyond daml-prim and daml-stdlib. A refused action becomes an
ordinary ledger contract instead of an aborted transaction, with the auditor
on the signatory line rather than the observer line, so a second journal
cannot be created at all rather than merely noticed. 170 Daml scripts.
Published to ghcr and rebuilding byte for byte from committed source.

github.com/dominicrume/cantor8_kya_rails/tree/main/step-0-refusal

The good half. A guarded asset survives one stolen key. The control is a
conjunction, and three tests hold it: owner and actor together move nothing
without the guardian, the guardian alone moves nothing either, and submitting
as both defeats it, which is a question about who runs which participant.

The bad half, and it is new. The evidence does not survive. An attacker with
one party's authority gains nothing by opening an attempt, so they exercise
the asset directly, the ledger refuses during interpretation, no transaction
commits, and the counter never moves. Five thousand blocked attacks and zero
blocked attacks look identical to the auditor.
testAnAttackerWithOneStolenKeyLeavesNoCount makes five attempts and shows the
auditor seeing nothing. This counts refusals by a cooperating actor. It does
not count attacks.

What I am asking for. A SIG Security read on whether the signatory-line
mechanism is sound, and a reviewer for Dev Fund #860, which has had none in
34 days. The specification is also on cip-discuss as message #909, where
Simon Meier has already corrected the mechanism once and Georgi Radev and
Leonid have each cost it a claim on the forum.

What has not been done. None of it has run on DevNet. I have never held a
credential. Weigh it as a specification with a tested reference
implementation, not as deployed software. Happy to walk anyone through it in
twenty minutes.
