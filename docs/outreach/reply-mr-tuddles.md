# Reply to Mr_Tuddles

**Where:** https://forum.canton.network/t/9059 (reply to his post #12)
**Status:** not sent. He posted 11 September; it is now 13 September.

## What he actually said

> "Might be easier for you to just tell us what you are building. We are a
> stablecoin issuer; our stables are deployed on testnets with agentic
> payments."

Plus: they are investigating porting to Canton natively.

## What was wrong with the first draft of this

It opened with "thanks, that helps", explained `assertMsg` semantics, and
ended with a question. He has now declined our question twice and asked, in
plain words, for us to say what we are building. Both of our messages led with
the mechanism. A third that did the same would read as evasive, because it
would be.

He is also the closest thing to a real user in that thread: agents making
payments on testnets, today, and a port to Canton under way.

So: answer the question, in his register, short. Give him the thing. Ask
nothing. Two unanswered questions from us is already one too many.

Paste this:

---

Fair enough.

I build the record of what an agent was **refused**.

Your agents pay. When a policy stops one, most systems keep nothing useful. In
Daml a failed `assertMsg` aborts the transaction, so afterwards the ledger
looks exactly as it would if the agent had never tried. What went through is on
the ledger. What was stopped exists only in your own logs, written by you,
about you. That second half is what an auditor asks for.

Two parts.

The refusal becomes a transaction that succeeds: same rules, but when one says
no it writes a small contract and moves no money. The id and the time come from
the ledger instead of from the operator.

And the refusals can be handed over without the payments. Here is one:

https://dominicrume.github.io/cantor8_kya_rails/examples/settlement-refusals.json

Drop it on https://dominicrume.github.io/cantor8_kya_rails/ and it will show
three refusals in full and three payments as sealed gaps it is not being shown.
Delete a refusal and it stops verifying. Nothing to install, no account.

The figures are invented. It is there so you can see the shape.

MIT, and about twenty lines to implement if you would rather not take the
dependency.

---

## If he replies

The thing worth learning is still what happens to a blocked settlement attempt
in his system today. Do not ask it again. If he engages, it will come out.
