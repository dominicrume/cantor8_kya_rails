# What a KYA chain proves, and what it does not

The value of this format is not that it produces a record. Anything produces a
record. It is that a reader can work out **how much of it to believe** without
trusting whoever handed it to them.

That only works if the limits are written down as plainly as the claims. This
page is the limits.

---

## The claim

**You can prove an agent did not do the thing it was not allowed to do.**

Two halves, and until 2026-09-10 only one of them was true.

**What it tried.** Every attempt is an entry — allowed and refused alike, with
the rule that decided it. Logs record what happened; this records what was
*stopped*, which is the half nobody else keeps.

**What it was allowed to do.** The policy is the first entry, carrying the cap,
the allow-list, the period and the expiry as readable text. Every later entry
hashes it through `prev`.

The second half is the one that makes the first mean anything. A receipt
reading `REFUSED — over the cap` proves the agent was stopped; on its own it
does not prove what the cap *was*. An operator who set it to a million produces
the same record as one who set it to five. Until the policy was sealed, this
format proved caution, not limits.

---

## What a verified chain does prove

**Nothing in it has been edited since it was written.** Change a verdict, a
rule, an amount, a payee or the policy and the chain stops verifying at that
entry. Anyone can check this on a static page with no install, no account and
no node.

**No entry has been removed from the middle.** Deleting one breaks every seal
after it.

**The rules were fixed before the attempts.** The policy is entry one; the
attempts hash it. It cannot be widened afterwards to make a refusal look
generous or an acceptance look prudent.

**Who decided.** Every entry carries `ledger` — the system that produced the
outcome. See below, because this is the field that decides how much the rest is
worth.

---

## What it does not prove

**That the record is complete.** A chain proves nothing was *changed*. It does
not prove nothing was *omitted*. An operator who runs an agent, discards the
chain and starts a fresh one has produced a perfectly valid record of a shorter
story. Tamper-evidence is not the same as completeness, and no amount of
hashing gets you the second one.

The counter to omission is an **anchor**: publish the head somewhere you do not
control, at a time you cannot backdate. `KyaAnchor` does this on Canton; a
transparency log or a counterparty's countersignature would do it elsewhere. An
unanchored chain is only as complete as its author is honest.

**That the agent could not act outside the record.** The guard covers what it
wraps. An agent with a second credential, a shell, or a code path nobody
decorated is outside it entirely. This measures a boundary; it does not create
one.

**That the policy was reasonable.** A sealed cap of ten million is sealed just
as firmly as a sealed cap of ten. The format makes the number *checkable*, not
*sensible*. That judgement stays with the reader, which is the point of
printing the policy in text rather than only hashing it.

**That the code did what the receipt says.** The receipt records the decision.
If the wrapped function is buggy, or the payment API failed after being
authorised, the chain will faithfully record an authorised payment that never
settled. This is why receipts are written *before* the side effect: the record
of an attempt is more useful than a silent gap.

**Anything about time beyond what a clock asserted.** `at` is the producer's
clock. It is not proof the event happened then. Only an anchor gives you that.

---

## The level is what a reader established, never what a receipt says

An earlier version of this page had a rung called **ledger-enforced**, reached
by writing `assertMsg` in the `ledger` field. That was wrong, and wrong in the
direction this whole page exists to guard against: it made the strongest claim
in the format something a producer could type. SPEC §6a now forbids it by name.

The rule is one sentence. **A verifier reports the level it substantiated, and
it cannot substantiate anything from the file it was handed.** Every chain
therefore reads `self-attested` by default, however emphatic its `ledger` field
is. A receipt saying *"Canton DevNet, an independent validator refused this"*
seals perfectly and still reports `self-attested`, and conformance vector 18
exists to keep it that way.

Two findings can raise it, and both are things **the reader** goes and does:

| level | what the reader did | what they may then conclude |
|---|---|---|
| `self-attested` | checked the seals | nothing was edited after it was written. The party being checked is the party doing the checking. |
| `anchored` | found the head seal and receipt count published somewhere the producer does not control | nothing has been swapped or truncated since that publication. |
| `ledger-recorded` | both of the above, **and** found every refusal on that ledger with the rule and time claimed | the refusals happened, and were not invented, backdated or reordered. |

There is still no level meaning *the rule was enforced*. Whether a fence would
have stopped a payment had the record not been written is a fact about code,
not about records, and nothing in a document reaches it.

**The honest ladder**, weakest to strongest:

1. A log. Proves nothing; editable, incomplete, unordered.
2. A self-attested chain. Proves no edits since writing.
3. A self-attested chain, anchored. Adds: nothing removed or swapped since the
   anchor.
4. The above, with every refusal carrying a `ledger_ref` the reader looked up
   and found. Adds: these refusals really happened, on a ledger, at the time
   and for the reason stated.

Rung 4 needs something at the enforcement layer, not in the format. A refusal
enforced by an aborting assertion leaves nothing to look up, which is why
`KyaMandate.TryCharge` commits a `ChargeRefused` contract instead of aborting.

Most real deployments will sit at 2 or 3. That is fine. It is only a problem if
they are described as 4.

What no rung reaches: an attempt that was never submitted leaves nothing behind
at any level.

---

## What we have actually run

Stated so the claims above are not the only thing on this page.

- **69 authorisation fences** mutation-tested across three OpenZeppelin Canton
  repositories; **52** can be made vacuous with every test still passing. Sealed
  as three records in [`docs/findings/`](findings/), each reproduced from a
  clean clone weeks after the run that produced it.
- **Real Amulet moved on Cantor8 DevNet**, and the account the agent was told to
  redirect to holds **0.0** on both sides. The arithmetic is in
  [`devnet-balances.json`](devnet-balances.json) and re-added on every build.
- **Three independent implementations** (Python, JavaScript, Go) agree on
  20/20 conformance vectors.

And what has not: nobody outside this project has yet produced a chain with it.
That is the honest state, and this page will say so until it changes.

---

*If you are reading this because someone handed you a chain: open
<https://dominicrume.github.io/cantor8_kya_rails/> and drop the file on it.
Read the assurance level the page reports, not the `ledger` field inside the
file. The field is written by whoever produced the chain; the level is what the
page was able to establish, and for a file handed to you that is always
`self-attested` until you go and check something yourself.*
