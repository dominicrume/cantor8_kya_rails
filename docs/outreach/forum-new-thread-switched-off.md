# New thread: a control the audited party can switch off

**Where:** forum.canton.network, **App Development**. Tags `daml`, `canton`.
**Why a thread and not a reply:** the only topic this account has started is
9114, on 8 September. Six weeks of replying to other people. Replies make you
useful. Threads make you visible, and a Tech and Ops member does not read
replies.

**Two earlier drafts were deleted rather than posted.** The denominator one
and the "solved" one both described designs that changed within a day. A post
about audit evidence that has to be corrected twice is worse than no post.

## The frame

Not "I built a thing". The honest sentence, and the one nobody else in this
ecosystem is saying:

> An audit control that the audited party can switch off is not a control.

That was true of everything in this repository until yesterday, including the
hash chain, and saying so is the part that earns the read.

## Rules

- The limit goes near the top, not in a footnote. A reader who finds it
  themselves stops trusting the rest.
- No Dev Fund, no PR number, no champion.
- End with a real question that has a real answer.

---

## THE POST

**Title: An audit control the audited party can switch off is not a control**

I spent six weeks building evidence that an agent was refused, and last week
somebody made me notice that none of it was enforceable.

The chain of receipts, the counter, the two-phase attempt record: every one of
them was written by the application, which means every one of them was written
by the party the evidence is about. An auditor asking "can I trust this
record" was being answered with "if the application chose to write one". That
is not an answer.

Worth saying that a paper three weeks old makes the same point harder than I
can. Hearsay, arXiv:2609.32495, injected 28 omissions into deployed agent
harnesses. A log kept outside the harness caught all 28. **A hash chain over
the harness's own record caught none of them.** If you are relying on a seal
you compute yourself, that is the paper to read.

So the fix was not cryptography. It was authorization.

In Daml a consuming choice needs the authority of the contract's signatories.
So put a second party on the asset:

```daml
template Wallet
  with holder : Party; guard : Party; balance : Decimal
  where
    signatory holder, guard
```

The guard is also a signatory of the journal, which means its authority is
reachable only from inside a journal entry. An application trying to move that
wallet any other way holds the owner's authority and nothing else, and the
ledger refuses it. Not discouraged. Refused.

The integration is one word on the signatory line and an interface instance.
The work itself stays entirely the application's; the module never looks
inside it.

**Now the limit, because you would find it in a minute and it is better from
me.**

Daml hands a submitter the authority of every party it submits as. So an
operator who can submit as the guard reaches the asset directly and no journal
entry is written. There is a test that performs exactly that bypass and shows
the counter never moves.

Which means this is a control when the guard is operated by someone who is not
the actor, and a convention when one person submits as both. Segregation of
duties is doing the work. The code only makes it enforceable.

I think that is the honest ceiling for any on-ledger control, and I would
rather state it than have a compliance officer discover it.

Three smaller things learned on the way, in case they save somebody a day:

Daml-LF 2.1 removed contract keys, so there is no way to enforce one journal
per pair. I settled for making a second one visible to the auditor.

The build refuses a package containing both interfaces and templates, saying
it may not be upgradeable. It is right, and given Canton's upgrade check that
matters more here than usual. The interface now lives in its own package.

`DA.Crypto.Text` is still marked alpha. The commitment depends on `sha256`,
so if that module changes, every commitment already written becomes
unverifiable, with no migration path for a contract already on a ledger. I
accepted that and wrote it down rather than suppressing the warning quietly.

147 Daml scripts, none of them on DevNet, because I have never had a
credential. All of it is a design until it runs on a real ledger and I would
weigh it accordingly.

https://github.com/dominicrume/cantor8_kya_rails/tree/main/step-0-refusal

**The question.** Has anyone enforced this differently? Specifically: without
contract keys, is there a Daml 3 way to guarantee an asset cannot be acted on
except through a particular contract, that does not depend on a second party
being operated by somebody else?

If the answer is no, then segregation of duties is the floor for every
on-ledger control, and that seems worth knowing.
