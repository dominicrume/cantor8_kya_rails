# Two replies, both owed since 11 September

Run `python3 tools/waiting.py` and it will name both of these. Neither can be
sent from here: the forum needs a login and returns 403 to anonymous posts.

Copy each block between the lines. Nothing else needs writing.

---

## 1. Mr_Tuddles

**Go to:** https://forum.canton.network/t/9059
Click **Reply** at the bottom.

He asked twice for a plain answer and we led with the mechanism both times.
He is a stablecoin issuer with agents paying on testnets and a Canton port
under way, which is the one place this matters most.

Paste this:

```
Fair enough. Plainly:

I am not building a platform. I build the evidence layer that sits under one.
A platform decides what your agent may do. I record what it tried and was
refused, sealed so the other side can check it without trusting whoever ran
the agent.

That matters most exactly where you are going. You said you are looking at
porting to Canton natively. In Daml a failed assertMsg aborts the whole
transaction, so a refused action leaves nothing behind at all: afterwards the
ledger looks exactly as it would if the agent had never tried. Your settled
payments are on the ledger. Your blocked ones exist only in your own logs,
written by you, about you. For a stablecoin issuer that is the wrong half to
be vouching for.

Two parts to it.

The refusal becomes a transaction that succeeds. Same rules, but when one says
no it writes a small contract and moves no money, so the contract id and the
time come from the ledger instead of from the operator.

And the refusals can be handed over without the payments. Here is one:

https://dominicrume.github.io/cantor8_kya_rails/examples/settlement-refusals.json

Drop it on https://dominicrume.github.io/cantor8_kya_rails/ and it shows three
refusals in full and three payments as sealed gaps it is not being shown.
Delete a refusal and it stops verifying. Nothing to install, no account.

The figures are invented, so you can see the shape without reading anything
into the numbers. MIT, and about twenty lines to implement if you would rather
not take the dependency.
```

---

## 2. Federico_Rodriguez

**Go to:** https://forum.canton.network/t/9114
Click **Reply** at the bottom.

He found the hole and specified the fix on 11 September. It was built on the
12th. He gets the credit in the first line.

Paste this:

```
Your understanding was correct, and you were right about the limitation.

The receipts were produced by the application, so a refused attempt existed
only because our own process chose to write it down. In Daml a failed
assertMsg aborts the transaction, so after a refusal the ledger looks exactly
as it would if the agent had never tried. The accepted payments were
corroborated by the ledger. The refusals, which are the half anyone actually
asks about, were our word.

I built what you described. TryCharge runs the same rules and, when one says
no, creates a ChargeRefused contract and leaves the mandate untouched. The
transaction commits either way and money only moves on the allowed path, which
is the shape you set out.

https://github.com/dominicrume/cantor8_kya_rails/blob/main/step-1-mandate/daml/KyaMandate.daml

Two things I would not have got right without the nudge. The rules are now
written once and read by both paths, because the aborting fence and the
recording fence saying the same words is not the same as them agreeing: I
flipped one comparison and every test stayed green while a charge landing
exactly on the cap was refused by one path and accepted by the other. And the
refusal record is archivable by its signatories, so the honest claim is that
removing one is itself a ledger event, not that it cannot be removed.

Your caveat survives, and it is in the contract now rather than in a thread:
an attempt that was never submitted still leaves nothing behind. This makes a
refusal that happened impossible to invent, backdate or reorder. It does not
make one that never reached the ledger appear.

Thank you. That was a better piece of review than most code gets.
```

---

## After sending

Add a row to `docs/conversations.md` for anything either of them says back, in
their words. Do not chase either thread. The OpenZeppelin issues have had no
reply in seven days and get no second message.
