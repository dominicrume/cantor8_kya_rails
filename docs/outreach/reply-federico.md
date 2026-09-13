# Reply to Federico_Rodriguez

**Where:** https://forum.canton.network/t/9114/2 (our own topic)
**Status:** not sent. He posted 11 September; it is now 13 September.

He read the design, found the hole, and specified the fix, a day before we
built it. The reply owes him three things: say he was right, show the code, and
say what his own caveat still leaves open. No pitch, no question back.

Paste this:

---

Your understanding was correct, and you were right about the limitation.

The receipts were produced by the application, so a refused attempt existed
only because our own process chose to write it down. In Daml a failed
`assertMsg` aborts the transaction, so after a refusal the ledger looks exactly
as it would if the agent had never tried. The accepted payments were
corroborated by the ledger. The refusals, which are the half anybody actually
asks about, were our word.

I built what you described. `TryCharge` runs the same rules and, when one says
no, creates a `ChargeRefused` contract and leaves the mandate untouched. The
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

Your caveat survives, and it is now written into the contract rather than
left in a thread: an attempt that was never submitted still leaves nothing
behind. This makes a refusal that happened impossible to invent, backdate or
reorder. It does not make one that never reached the ledger appear.

Thank you. That was a better piece of review than most code gets.

---

## Why it is written this way

He gets the credit in the first line, not the last. The code link, because he
is the kind of reader who will open it. The two things I got wrong on the way,
because he will find them anyway and it is cheaper to say them. His caveat
restated as still-true, because agreeing with someone and then quietly dropping
their objection is worse than not replying. No ask.
