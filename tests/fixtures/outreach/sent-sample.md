# Fixture for tests/outreach_lint.py

The public text of two forum replies sent on 13 September 2026
(forum.canton.network t/9059/13 and t/9114/4). Nothing else from the original
file is here: the rest was private and now lives outside this repository.

It exists so the lint, and the two mutation rows that prove the lint can fail,
have something real to run against in every clone. The paste blocks below are
what the lint measures.

---

```
Fair. Plainly.

Your agentic registry says what an agent may do.
Deterministic settlement says what happens when it pays.
I do the third one. I keep the record of what it tried and was refused.

You said you are porting to Canton natively. The gap gets wider there.

In Daml a failed assertMsg aborts the transaction. So a blocked payment
leaves nothing at all. Your settled payments sit on the ledger. Your
blocked ones sit in your own logs, written by you, about you. An auditor
asks a stablecoin issuer for the second half.

So two changes. The refusal becomes a transaction that commits and moves
no money. And refusals can be handed over without the payments.

Here is one:
https://dominicrume.github.io/cantor8_kya_rails/examples/settlement-refusals.json

Drop it on https://dominicrume.github.io/cantor8_kya_rails/

It shows three refusals in full. Three payments stay shut. Delete a
refusal and the file stops verifying. Nothing to install.

The figures are invented. MIT, and about twenty lines if you would
rather not take the dependency.
```

---

```
Yes, that is right. And the omission gap was the real problem.

I built what you described.

A choice called TryCharge checks the policy. If it passes, it pays. If it
fails, it creates a ChargeRefused contract and pays nothing. Both paths
commit. That is your RejectedAttempt under another name.

https://github.com/dominicrume/cantor8_kya_rails/blob/main/step-1-mandate/daml/KyaMandate.daml

You called the trade-off right too. Rejection is modelled in Daml now.
That cost a second copy of the rules. They drifted once. I changed one
comparison. Every test stayed green. The two paths then disagreed about a
charge landing exactly on the cap. There is a test for that now.

Your caveat still stands. An attempt nobody submits still leaves
nothing. This only fixes refusals that reached the ledger.

Thank you. That was better review than most code gets.
```
