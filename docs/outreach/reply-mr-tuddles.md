# Reply to Mr_Tuddles

**Where:** https://forum.canton.network/t/9059 (reply to his post)
**Status:** not sent

He asked "what do you have in mind?" after saying Pearl supports deterministic
settlement by agents. He is a stablecoin issuer porting to Canton. The thing
worth saying to him is the one thing he cannot get anywhere else, and the file
has to come with it, because a description of evidence is not evidence.

Paste this:

---

@Mr_Tuddles thanks, that helps. One thing I have been stuck on, and I think you
will have hit it too.

In Daml a failed `assertMsg` aborts the transaction. So when a spending rule
stops an agent, nothing is written: the ledger afterwards looks exactly as it
would if the agent had never tried. The payments that went through are on the
ledger. The ones that were stopped are only in whatever your own process wrote
about itself, which is the half a regulator actually asks about.

Two things came out of that.

The refusal becomes a transaction that succeeds. Same rules, but instead of
aborting it writes a `ChargeRefused` contract and moves no money, so the
contract id and the record time come from the ledger rather than from me.

And the refusals can be handed over on their own. Here is one:

https://dominicrume.github.io/cantor8_kya_rails/examples/settlement-refusals.json

Open https://dominicrume.github.io/cantor8_kya_rails/ and drop the file on it.
Nothing to install, no account, no node. It should say the disclosure holds,
show you three refusals in full, and show three payments as sealed gaps it is
not being shown. Delete one of the refusals and it stops verifying.

The figures are invented. It is there so you can check the shape before
producing one.

Two things it does not do, since they matter more than what it does: an attempt
that was never submitted still leaves nothing behind, and a seal says the
contents have not changed, not who wrote them.

What happens to a refused settlement attempt in your system today?

---

## Why it is written this way

One question at the end, about his week, not about my idea. The link before the
explanation. The limits stated by me rather than found by him. No ask.
