<pre>
  CIP:  (unassigned)
  Layer: Daml
  Title: A ledger record for refused actions
  Author:
    O'Rume Dominic Uririe
  License: CC0-1.0
  Status: Draft
  Type: Standards Track
  Created: 2026-09-26
  Post-History:
</pre>

**NOT SUBMITTED.** `cip-0000` says to float an idea on `cip-discuss` before
writing a full CIP, and that has not been done. This exists so the float has
something behind it if anyone asks, and so the shape can be argued with early
rather than after a month of writing. See `docs/outreach/float-on-cip-discuss.md`.

# 1. Abstract

A supervisor asks a firm to show what its system blocked last quarter. The firm
can show every action that went through. It cannot show one that was stopped.

That gap is structural, not sloppy. In Daml a failed `assertMsg` aborts the
transaction, so a refused action leaves nothing on the ledger at all.

This CIP proposes a standard template for recording a refused action as a
committed transaction, with the party entitled to read it named in advance.

# 2. Motivation

**Who this is for, and what it saves them.**

| | what they get |
|---|---|
| a firm under supervision | an answer to "show me what you stopped" that does not begin with "trust our logs" |
| its auditor | the refusals, readable without asking the firm for them |
| an application builder | one module instead of a design problem, and a name other applications already use |
| a Super Validator | a standard that costs nothing to adopt and nothing to ignore |

The asymmetry today runs the wrong way. What settled is corroborated by the
ledger. What was refused exists only in the application's own logs, written by
the operator, about the operator. The half a supervisor asks about is the half
with no ledger artefact behind it.

EU AI Act Article 12 requires high-risk systems to log events automatically
across their lifecycle. DORA requires integrity-protected audit trails. Both
move the burden from HAVING a control to EVIDENCING that it operated, and a
control that operates produces refusals.

This is specific to ledgers that do not commit failed transactions. On Ethereum
a reverted transaction is still included in a block and still costs gas, so the
attempt is visible. On Canton it is not, which makes the gap larger here and
the fix more valuable here.

A survey of the 118 existing CIPs found no prior art: none covers refusals,
rejected attempts, or a record of a blocked action. The eight that mention
"audit" mean security audits, auditors as institutional actors, or audited
uptime.

# 3. Specification

A template with no opinions about money.

A payments application, a lending protocol and a collateral engine all fit.
None of them carries a field that means nothing to it.

```daml
template RefusalRecord
  with
    owner     : Party            -- accountable for the system that refused
    actor     : Party            -- who tried
    action    : Text             -- the application's own word: "withdraw"
    detail    : Text             -- the particulars, application's encoding
    rule      : Text             -- WHICH rule refused it
    refusedAt : Time             -- ledger effective time
    auditor   : Optional Party   -- named in advance; None discloses to nobody
  where
    signatory owner, actor
    observer optional [] (\a -> [a]) auditor
    ensure action /= "" && rule /= ""

    nonconsuming choice Acknowledge : Text
      controller optional owner identity auditor
      do pure rule
```

The calling pattern is to stop aborting and commit either way:

```daml
case refusalReason ... of
  Some rule -> do
    _ <- create RefusalRecord with ...
    pure ()
  None -> -- the real work, only on this branch
```

# 4. Rationale

**Why both parties sign.** A refusal one side can mint alone is a log line with
extra steps. Signing it jointly means neither can later say the other invented
it.

**Why an empty rule is refused.** "Refused" on its own evidences no control.
The name of the control that fired is the evidence.

**Why the auditor is named in advance.** An auditor who has to ask the operator
for the refusals is handed what the operator chose to hand over. One named in
the contract before the attempts happened is not. This is the part a
transparent chain cannot do: the record is ON a ledger and is NOT public.

**Why `Acknowledge` is non-consuming.** Asking must not destroy the thing being
asked about, and it lets "we disclosed it" be checkable rather than asserted.

**Why `action` and `detail` are Text.** A typed union of every domain's
operations would need extending for every new application. Text costs a
convention and buys universality.

# 5. Backwards compatibility

None. This is a new template in a new package with no upgrade history. Existing
applications are unaffected until they choose to use it.

# 6. Security considerations

Stated as limits rather than discovered as surprises.

- **An attempt never submitted leaves nothing behind.** This makes a refusal
  that HAPPENED impossible to invent, delete, backdate or reorder. It does not
  make one that never reached the ledger appear, and no ledger artefact can.
- **A record is archivable by its signatories.** The honest claim is that
  removing one is itself a ledger event, not that it cannot be removed.
- **It proves a rule fired, not that a rule is correct.**
- **`detail` is free text and is disclosed to the auditor.** An application that
  puts a customer identifier in it has made a data protection decision, and
  should be told so by its own review rather than by this template.

# 7. Reference implementation

`canton-refusal-record` 1.0.0. One module, dependencies limited to `daml-prim`
and `daml-stdlib`, MIT.

https://github.com/dominicrume/cantor8_kya_rails/tree/main/step-0-refusal

Eight scripts. The two that matter prove it is reusable: a lending protocol and
a collateral engine, both using it with no concept of a payee. The rest are the
guards. An auditor reads every record. A stranger reads none, and cannot
manufacture an acknowledgement.

# 8. Credit

The pattern was named `RejectedAttempt` by **Federico_Rodriguez**, a Canton
Community Tech Partner, on forum.canton.network/t/9114 in September 2026. He
identified that application-written receipts cannot prove completeness,
specified the fix, and named the limit it does not close. All three are above.

# 9. Copyright

CC0-1.0.
