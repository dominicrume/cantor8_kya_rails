# Paid work, and the twelve-month clock

Two goals that turn out to point at the same people.

**Income.** Daml and Canton contract work, now.

**Global Talent.** Three letters are required, each from somebody who has
known the work for **at least twelve months**. Every Canton relationship is
too young: Federico since September, Arpit and PREDGE since October. None
qualifies before late 2027.

**So every senior relationship started this month is a letter in October
2027.** That is not a reason to write to people. It is a reason not to wait
until the application to start.

---

## The model that worked for somebody else

PR #858 was merged because `waynecollier-da` wrote this:

> "BitDynamics has demonstrated a high level of effectiveness on the small
> Splice projects they completed to date **on their own initiative**, and the
> Splice maintainers believe they can be effective in delivering this
> proposal."

Free work first, paid work after. That is the only route anyone in this
repository's research has been observed to take.

The OpenZeppelin finding is that work, already done, and not yet sent to
anybody who sells it.

---

## 1. Hacken. The closest thing to a warm lead.

**Why them.** They sell Daml security audits. They ran an "AI Daml Auditor"
workshop on the forum in September that got no community engagement. Łukasz
and Andrew are in `#sig-security` and `#sig-regulatory-compliance` with you.

**The hook.** You have a real finding about real Canton code, produced by a
method they do not appear to use. 49 of 62 authorisation conditions in two
OpenZeppelin Canton packages could be deleted with the suite still green.

**Slack DM to Łukasz:**

```
Łukasz, we are both in sig-security.

I mutation-test Daml authorisation fences: delete each condition, re-run the
project's own suite, see what stays green. On two OpenZeppelin Canton
packages, 49 of 62 could be made vacuous. Their newer one is clean.

The sealed report is yours if useful. No ask attached.

I also saw the AI Daml Auditor workshop. If Hacken ever needs this run as
part of an engagement, I do it, and I am available.
```

---

## 2. Moonsong Labs. Federico has already read your code.

**Why them.** Two Community Tech Partners on the roster, Federico and Tomi
Moreno. Federico read your design in September and wrote the objection that
reshaped it. He knows the work.

**The hook.** Not a job ask. A report on what his objection produced, with
one line at the end.

**Forum DM to Federico:**

```
Federico, you found the omission gap in September and it took three goes.

Record is written before the work now, so a revert cannot destroy it. The
auditor is a signatory rather than an observer, so a second journal cannot be
opened. And an asset carrying a guard party cannot move unless a record is
written.

165 scripts, every authorisation check mutation-tested.

Separately: I am looking for Daml contract work in London. If Moonsong ever
needs hands, I would like to be on the list.
```

---

## 3. Vacuumlabs. They are hiring shape, not just proposing.

**Why them.** A grant-funded protocol engineering shop across Cardano,
Midnight, Arbitrum and now Canton. Arpit is already in conversation with you
and already cited your proposal.

**When.** After he answers the authority question. Not before. A technical
exchange first, then this, in the same thread.

```
Separate from the above. Vacuumlabs takes on protocol engineering work and
I am looking for Daml contract work. If you ever need a second pair of hands
on the Canton side, I am available and already building in it.
```

---

## 4. Jørgen Ouaknine. The long one.

**Who he actually is.** Board Member of the Canton Foundation and **Global
Head of Innovation and Digital Assets at Euroclear**. Not the Founding
Chairman, which this repository wrongly said on 17 October. The Chair is
Dr Johnna Powell of DTCC.

**Why him specifically.** Euroclear settles securities. A control that fires
and leaves no evidence it fired is a settlement problem before it is a
blockchain one. That is his subject, not a courtesy.

**What this note can and cannot do.** It cannot produce a letter now, because
of the twelve-month rule. It can start the clock, and it can open a door at a
firm that pays people.

**The discipline.** No ask. Not for a champion, not for a job, not for a
meeting. One artefact, one sentence about why it might matter to him, and
stop. If he replies, that is a relationship. If he does not, nothing is lost
and nothing is owed.

**LinkedIn, or whatever channel exists:**

```
Jørgen, this is relevant to Euroclear rather than to me, so no ask attached.

On Canton, a failed check aborts the whole transaction. So when a control
blocks a settlement instruction, the ledger afterwards is identical to one
where nothing was tried. The control fired and there is no evidence it fired.
The only record is the operator's own log, about the operator.

I have built the other half: refused actions commit as contracts, disclosed
to an auditor named in advance, without disclosing what was allowed. MIT,
165 tests.

github.com/dominicrume/cantor8_kya_rails

Third place at Cantor8's Build on Canton in August.
```

---

## The order, and the honest odds

1. **Hacken.** Same Slack, same subject, real finding. Highest chance of a
   reply this week.
2. **Federico.** Warm, owed an update anyway, and the work ask is one line at
   the end of something he will want to read.
3. **Ouaknine.** Slow. Start the clock.
4. **Vacuumlabs.** Only after the technical exchange.

**What not to do.** Do not send all four today. Do not attach a CV to any of
them. Nobody opens a CV from a stranger, and all four already have the only
thing that matters, which is a public repository with the work in it.
