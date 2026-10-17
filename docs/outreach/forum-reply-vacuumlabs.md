# Reply to Vacuumlabs, forum 9084

**Thread:** https://forum.canton.network/t/were-building-delegated-automation-on-canton-seeking-feedback-champion/9084
**Posted:** 27 August 2026 by `arpitkarnatak_vl`. **58 views, one post, no replies, 51 days.**
**Their PR:** canton-dev-fund #627, open since 9 August, still `needs-champion`.

They asked: *"Looking to hear if there are teams who have a need for this."*
Nobody answered. That is the whole reason to post.

**Goal of this reply:** answer their question honestly, name the gap their own
design has, and offer the piece that fills it. Not a pitch. They are seeking a
champion too, and so are we.

**Do not** mention our Dev Fund proposal in the first post. Help first.

---

## THE POST

Yes. Here is a team with that need, and here is where.

Your checks run before execution: number of runs, cooldown, expiration, and a
revokable Authorization. Good. Now think about the moment a check says no.

In Daml a failed assertion aborts the transaction. Nothing commits. So the run
your authorization correctly stopped leaves no trace on the ledger at all.

Your control worked. There is no evidence it worked.

The only record is a line in the operator's own log, written by the operator,
about the operator. That is the artefact a regulated client hands an auditor
when asked to show the automation was actually bounded.

I build the other half of that. Refusals become contracts.

One choice checks the policy. If it passes, it acts. If it fails, it creates a
refusal record and moves nothing. Both paths commit. The contract id and the
record time come from the ledger, not from the runner.

It is a separate Daml package with no dependencies beyond the standard library,
so it drops into yours without taking your design hostage:

https://github.com/dominicrume/cantor8_kya_rails/tree/main/step-0-refusal

One thing in it you may want and will not find elsewhere. The refusal names an
auditor party, chosen once when the authorization is written. They observe
refusals. They do not observe the actions that were allowed. A client can hand
over what was stopped without handing over what went through.

There is a second piece you will want if a client ever audits a sample of your
runs. One contract per owner and actor counts every attempt that passes
through, allowed or refused, and holds the positions that were refused. The
auditor observes it, so they read the count off the ledger. Fifty runs,
refusals at 3, 7 and 19: if they are shown two refusal records they know one is
missing and which position it was, without the operator telling them.

They still cannot see the 47 runs that went through. Not what they were, not to
whom. The count is disclosed and the content is not, which is the only shape I
have found that a regulated client can actually hand over.

Your runner exercises it in the same transaction as the work, so the work and
the count cannot come apart.

Two honest limits, so nobody is surprised later.

It records what reached the ledger. A run with a second path that does not go
through the journal is still invisible, and nothing a module can do fixes that.
What it changes is that the hole has to be a code path somebody can look for.

And it is proven in Daml Script, 20 scripts on this module, and has never run
on DevNet because I do not have a credential. Everything above is a design
until it does.

If it is useful, take it. MIT, and about twenty lines if you would rather not
take the dependency.

One question back. When a cooldown or run-count check fails today, what does
your runner write down, and who can read it?
