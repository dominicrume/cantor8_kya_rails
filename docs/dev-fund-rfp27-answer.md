# RFP 27, answered clause by clause

**Why this file exists.** RFP 27 asks four specific things and `PR #860` does
not answer any of them in those words. Every proposal that has been merged in
this repository answered the RFP's own questions using the RFP's own language.
This is the text to paste into the proposal.

**RFP 27 in full**, from `2026-2028-strategic-roadmap.md`, lines 260 to 262.
It is two sentences and this is all of it:

> 27. Security Monitoring, Auditability and Evidence
>     1. RFP
>        1. Develop reusable tools and standards for security logging,
>           monitoring, alerting, audit trails, compliance evidence, and
>           security metrics while preserving Canton's privacy model.
>           Proposals should identify the threats being monitored, whether the
>           scope is at the entity or network level, required data sources and
>           how privacy, access controls, and selective disclosure will be
>           handled.
>        2. We anticipate approving multiple grants in this area as work
>           progresses over the coming year.

Note the last line. **This is explicitly not winner-takes-all.**

---

## PASTE THIS INTO THE PROPOSAL

### Answering RFP 27 directly

RFP 27 asks proposals to identify four things. Here they are in its own order.

**The threats being monitored.** Three, named rather than implied.

1. **A control that fired leaves no evidence it fired.** In Daml a failed
   `assertMsg` aborts the whole transaction, so after a refused action the
   ledger is byte-identical to one where nothing was attempted. The operator's
   own log is the only artefact, written by the operator, about the operator.
2. **An operator omits an inconvenient refusal from a disclosure.** The
   records that are handed over are genuine; the set is not complete.
3. **An operator relabels a refusal as an allowed action**, or resolves an
   attempt as something other than what was attempted.

The threat actor in all three is **the entity being audited**, not an external
attacker. That is the distinguishing feature of this work and the reason
cryptography alone does not reach it: a producer who writes their own log can
compute a correct hash over an incomplete one.

**Entity or network level.** **Entity level, explicitly.** This is a package
an application takes as a data-dependency to produce evidence about its own
conduct, disclosed to a counterparty or auditor it names. It introduces no
network-wide component, no shared service, no new synchronizer traffic, and
nothing any other participant must run or trust. A network-level deployment of
the same idea is possible and is not proposed here.

**Required data sources.** **None beyond the ledger the application already
writes to.** There is no external feed, no oracle, no off-ledger database and
no indexer dependency. Specifically:

| Datum | Source | Who assigns it |
|---|---|---|
| Record identity | contract id | the ledger |
| Time of a refusal | `getTime`, ledger effective time | the ledger |
| Position of an attempt | monotonic counter on a consumed-and-recreated contract | the ledger |
| Which rule refused | application text | the application |
| What was attempted | salted sha256 commitment | the application |

Four of the five come from the ledger. The two that come from the application
are bound: the commitment fixes what was attempted before the outcome is
known, so the application cannot describe a different action afterwards.

**Privacy, access controls and selective disclosure.** This is the clause the
work is built around rather than an afterthought.

- **Named in advance.** The auditor party is fixed when the journal is opened,
  before any attempt exists. They never ask the operator for anything.
- **Refusals are disclosed. Allowed actions are not.** The auditor observes
  refusal records in full. An allowed action produces no record of what it
  was, only that the count moved. That asymmetry is the whole design and is
  held by a named test, so adding an acceptance record would turn the suite
  red.
- **An open attempt discloses a position, a time and a digest.** Not the
  action, not the amount, not the counterparty. The commitment is salted, with
  the salt held off-ledger until resolution, because an unsalted hash over a
  payment action is brute-forced in seconds.
- **Nothing is public.** No transparent log, no network-visible artefact. The
  privacy model is Canton's own: the parties on the contract, and nobody else.
- **The auditor is a signatory of the journal, not merely an observer**, so a
  second journal cannot be opened behind their back. A create requires every
  signatory.
- **Access control is the enforcement mechanism, not a feature alongside it.**
  An asset carrying a guard party on its signatory line cannot move at all
  unless a record is written, because the guard's authority exists only inside
  a journal entry.

**The limit, stated here rather than found later.** Daml grants a submitter the
authority of every party it submits as. An operator who can submit as both the
actor and the guard reaches the asset directly, and a test in the suite
performs exactly that bypass and shows it working. **This is a control under
segregation of duties and a convention without it.** No on-ledger mechanism can
do better, and a proposal claiming otherwise is claiming something false.

---

## ALSO PASTE: the interface, in types rather than prose

`moritzkiefer-da` made the same criticism of PR #627 twice on 16 October:

> "you say that you add an interface but then you don't mention at all what
> choices that interface actually supports."

> "this is a lot of prose but it's hard to see how that actually looks like, I
> suggest to at least add the type signatures of your interface here."

That is the single most repeated reviewer criticism in the repository. The
answer is to put the signatures in the document.

### What ships, and what an integrator writes

**Ships, built and tested today:** two packages, SDK 3.4.11, Daml-LF 2.1, no
dependencies beyond `daml-prim` and `daml-stdlib`.

```daml
-- canton-journal-interface
data JournalledView = JournalledView with
    owner    : Party
    guardian : Party

interface Journalled where
  viewtype JournalledView
  perform : Update ()
  choice Perform : ()
    controller (view this).owner, (view this).guardian

-- canton-refusal-record
template RefusalRecord with
    owner, actor : Party
    action, detail, rule : Text
    refusedAt : Time
    auditor : Optional Party

template AttemptJournal with
    owner, actor, guardian : Party
    auditor : Optional Party
    attempts : Int
    refusals : [Int]
  where
    signatory [owner, actor, guardian] <> optional [] (\a -> [a]) auditor
    choice Open   : (ContractId Attempt, ContractId AttemptJournal)
      with salt, action, detail : Text
    choice Refuse : (ContractId RefusalRecord, ContractId AttemptJournal)
      with action, detail, rule : Text
    choice Allow  : ContractId AttemptJournal   with action : Text
    nonconsuming choice Expect : (Int, [Int])

template Attempt with
    owner, actor, guardian : Party
    auditor : Optional Party
    n : Int
    commitment : Text
    openedAt : Time
  where
    choice RefuseAttempt  : (ContractId RefusalRecord, ContractId Resolution)
      with salt, action, detail, rule : Text
    choice SettleAttempt  : ContractId Resolution
      with salt, action, detail : Text
           target : ContractId Journalled
    choice AbandonAttempt : ContractId Resolution   with reason : Text
    nonconsuming choice Opened : (Int, Time)

attemptCommitment : Text -> Text -> Text -> Text   -- salt, action, detail
missingRefusals   : (Int, [Int]) -> [Int] -> [Int]
```

**An integrator writes exactly two things:**

```daml
template Wallet with
    holder : Party
    guard  : Party          -- 1. the guard on the signatory line
    balance : Decimal
  where
    signatory holder, guard

    interface instance Journalled for Wallet where
      view = JournalledView with owner = holder; guardian = guard
      perform = do ...      -- 2. their own work, which we never inspect
```

That is the whole integration surface. No runner, no adapter, no service, no
configuration file.

### Where to be exact about readiness

Not a roadmap. Built, pushed and mutation-tested today:

| Property | The test that fails if it stops being true |
|---|---|
| A refusal commits and moves nothing | `testRefusalIsOnLedgerAndNothingMoved` |
| A withheld refusal can be named from the ledger | `testAWithheldRefusalIsDetectable` |
| A record survives the work reverting | `testTheRecordSurvivesARevert` |
| An open attempt discloses nothing | `testTheCommitmentHidesAndNotJustBinds` |
| A resolution cannot lie about the attempt | `testTheResolutionCannotLieAboutTheAttempt` |
| Evidence cannot be destroyed by the operator alone | `testArchivingAnAttemptLeavesANumberedHole` |
| A second journal cannot be opened secretly | `testASecondJournalIsPrevented` |
| **The asset cannot move outside the journal** | `testTheAssetCannotMoveOutsideTheJournal` |
| The bypass that defeats it, performed | `testSubmittingAsTheGuardianDefeatsIt` |

165 Daml scripts across two packages. Every authorisation check is
mutation-tested: deleting it turns a named test red.

**What has never happened:** none of it has run on DevNet, because no
credential has been issued. Every claim above is proven in Daml Script and is a
design until that changes.
