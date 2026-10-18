# Reply to Federico, forum 9114

**Thread:** https://forum.canton.network/t/how-do-you-prove-your-app-didnt-do-something/9114
**Our own thread.** Last post ours, 13 Sept. 112 views.

He asked for nothing. So this is a short update, not an essay. He gave the
review for free and the only right response is to report what it produced.

**Not in it:** no champion, no Dev Fund, no proposal, no ask of any kind.

---

## THE POST

Federico, an update, since your point was the one that mattered.

You said a chain of receipts written by my app cannot prove I left one out.
Right, and no hash fixes it, because I choose what to hash.

So I stopped hashing and started counting.

One contract per owner and actor. Every attempt consumes it and puts it back
with the count up by one. The auditor observes that contract, so they read the
count off the ledger instead of off what I hand them.

Fifty attempts, refusals at 3, 7 and 19. I show them two records. They know one
is missing and which position it was.

The work and the count commit in the same transaction, so skipping the count
means skipping the work. That is the part you described, reached from the other
side.

Two things I could not do. Daml 3 removed contract keys, so I cannot stop
someone opening a second journal. The auditor sees both, which is detection and
not prevention. And nothing forces an app to use the journal at all.

Still no credential, so all of it is Daml Script until it runs on DevNet.

Thank you for the review.
