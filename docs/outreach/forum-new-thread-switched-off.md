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

The guardrail now in CLAUDE.md: nothing is posted that is not built. So this
opens with the thing that exists and how to use it, not with six weeks of
reflection about how it got there.

> An audit control that the audited party can switch off is not a control.

That sentence is the finding. The post states it, shows the code that fixes
it, states the one condition under which it still fails, and stops.

## Rules

- Result first. The reader should know what to do with it inside two lines.
- The limit goes near the top, not in a footnote. A reader who finds it
  themselves stops trusting the rest.
- No Dev Fund, no PR number, no champion.
- End with a real question that has a real answer.

---

## THE POST

**Title: An audit control the audited party can switch off is not a control**

Shipped a Daml module that makes an asset impossible to move without writing
a ledger record of the attempt. One word on your signatory line and an
interface instance. MIT, no dependencies past the standard library.

https://github.com/dominicrume/cantor8_kya_rails/tree/main/step-0-refusal

The problem it solves is one I had for six weeks without seeing it. I was
recording what an agent was refused: a hash chain, a counter, an attempt
record. Every one of them was written by the application, which is the party
the evidence is about. An auditor asking "can I trust this record" was being
answered with "if the application chose to write one".

The fix is not cryptography. It is authorization.

A consuming choice in Daml needs the authority of the contract's signatories.
So put a second party on the asset:

    template Wallet
      with holder : Party; guard : Party; balance : Decimal
      where
        signatory holder, guard

        interface instance Journalled for Wallet where
          view = JournalledView with owner = holder; guardian = guard
          perform = do ...          -- your work, untouched

The guard is also a signatory of the journal, so its authority is reachable
only from inside a journal entry. An application trying to move that wallet
any other way holds the owner's authority and nothing else, and the ledger
refuses it. Not discouraged. Refused.

**The limit, because you would find it in a minute.** Daml hands a submitter
the authority of every party it submits as. An operator who can submit as the
guard reaches the asset directly and no record is written. There is a test
that performs that bypass and shows the counter never moves.

So it is a control when the guard is operated by someone who is not the
actor, and a convention when one person submits as both. Segregation of
duties does the work. The code makes it enforceable.

156 Daml scripts. Deleting any authorisation check turns a named test red.
None of it has run on DevNet, because I have never had a credential, so weigh
it as a design until it does.

If you want the reasoning for why a self-written chain is not evidence,
Hearsay (arXiv:2609.32495) injected 28 omissions into deployed agent
harnesses. A log outside the harness caught all 28. A hash chain over the
harness's own record caught none.

**The question.** Without contract keys, is there a Daml 3 way to guarantee an
asset cannot be acted on except through a particular contract, that does not
depend on a second party being operated by somebody else?

If there is not, then segregation of duties is the floor for every on-ledger
control, and that is worth knowing before you design one.
