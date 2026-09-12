## Development Fund Proposal

**Organization:** Independent (Rume Dominic / O'Rume Dominic Uririe)
**Author / Primary Contact:** Rume Dominic — dominicrume@gmail.com — github.com/dominicrume
**Status:** Draft
**Created:** 2026-09-06
**Proposal Type:** RFP-aligned
**RFP / Roadmap Area:** Security, Assurance & Incident Readiness — **RFP 22, Daml
Security Standards and Secure Development**
**Champion:** `Needs Champion`
**Total Funding Request:** 200,000 CC
**Project Duration:** 12 weeks
**Label:** daml-tooling

---

## Abstract

Daml's existing security tooling answers three questions well: does this source
contain a known anti-pattern (`daml-lint`), does it hold an invariant under
generated inputs (`daml-props`), and can a property be proved for all inputs
(`daml-verify`). None of them answers a fourth: **is the test suite that guards
this contract capable of failing at all?**

A Daml package with a correct authorisation fence and a test suite that would
pass with that fence deleted is, to every tool above, indistinguishable from one
with real coverage. It compiles, it lints clean, its properties hold, and its
tests are green. It is also unguarded, and nobody finds out until the fence is
tested by a counterparty.

This proposal delivers **mutation testing for Daml authorisation logic** as a
standalone tool: delete each fence in turn, rebuild, and require a *named* test
to fail. A fence no test notices is reported as uncovered rather than counted as
protected.

A working implementation exists in the applicant's repository and is what
produced the finding that motivated this proposal.

---

## Specification

### 1. Objective

**One objective: a mutation-testing tool for Daml that reports which
authorisation fences are actually covered by a test, and which only appear to
be.**

The problem is narrow and checkable. "All tests pass" is a claim about agreement
between code and tests, not about protection. The two diverge silently and in one
direction: a test written after the fence, asserting the behaviour the fence
already produces, passes whether or not the fence is there.

This is not hypothetical in this codebase. Running the harness across a repository
that had a green suite found **fifteen assertions that could not fail** — checks
that passed with authentication deleted, with the audit trail never written, and
with a tamper detector stubbed to return success. Every one was found the same
way: break the subject and see whether anything notices. Nothing did.

**In scope:** a mutation harness for Daml that operates on `assertMsg`
assertions, `ensure` clauses and consuming-choice archival; a catalogue of the
authorisation-fence patterns worth mutating, derived from real contracts rather
than invented; CI integration that fails a build on an uncovered fence; and a
report format that names the fence and the test that should have caught it.

**Out of scope:** general-purpose Daml mutation of arbitrary expressions, which
produces mostly equivalent mutants and wastes reviewer attention; formal
verification, which `daml-verify` already does; and static pattern detection,
which `daml-lint` already does.

### 2. Implementation Mechanics

**The method.** For each fence in a package: remove it, rebuild the DAR, run the
test suite, and record whether a test failed and which one. A fence whose deletion
leaves the suite green is reported as **uncovered**. The output is a mapping from
fence to the named test that dies without it — which is also what a reviewer or an
auditor wants to be handed.

**Why this is more than "delete a line and run the tests".** Three problems make a
naive version worse than useless, and the existing implementation addresses each:

1. **Equivalent mutants.** Deleting a guard that a second guard already covers
   changes nothing observable, and reporting it as a coverage failure trains people
   to ignore the report. The catalogue in Milestone 2 exists to separate fences
   worth mutating from those that are structurally redundant.
2. **Stale mutations.** A mutation whose target text has moved silently applies to
   nothing and is counted as covered. The existing harness reports this as `STALE`
   and exits non-zero rather than passing.
3. **Restoration.** A harness that leaves a mutated source or a stale build artefact
   behind corrupts every run after it. The existing implementation takes backups
   before mutating, restores in a `finally`, and rebuilds the DAR from restored
   source. This was learned the hard way: a mutated fence was once committed
   because a mutation run was interrupted.

**What already exists**, all reproducible from a clean clone of
`https://github.com/dominicrume/cantor8_kya_rails` (MIT), re-verified 2026-09-06:

| | |
|---|---|
| Daml fence mutation | `tests/mutation.py` — **32 of 32** fences; deleting any one turns a *named* test red. Baseline 100 of 100 scripts green |
| Suite-level mutation | `tests/mutation_suite.py` — 23 real defects across pages, adapters, storage, routes and the model interface; every one makes its covering suite fail |
| Refusal coverage | `tests/mutation_py.py` — **30 of 30** refusals at the edges covered by a *named* test. It reported 24 of 30 for weeks because six failed as a stack trace rather than an assertion; the harness refused to count those, which is the behaviour being proposed here |
| Fence lint | `tests/fence_lint.py` and a `tools/pre-commit` hook that refuses a commit with a fence missing |
| CI integration | mutation runs as its own GitHub Actions job against a separate checkout |
| Published | the receipt format the harness was built alongside is on PyPI as `knowyouragenticai-receipts` 1.0.0 (MIT, zero dependencies). The harness in this proposal is **not** packaged yet; Milestone 1 is what makes it installable |

The last row matters operationally: mutation rewrites the working tree, so it
cannot share a checkout with anything else. Discovering this cost a confusing
false failure during development and it is the kind of thing a shipped tool must
handle rather than document.

**Deliverable shape.** A standalone command that takes a Daml project path,
requires no changes to the project under test, and emits both a human report and
machine-readable output for CI.

A first version already exists and has been run against a project the applicant
did not write — `tools/daml_mutate.py`, pointed at OpenZeppelin's
`canton-contracts`. Two defects in the harness were found by doing so, and both
are the reason Milestone 1 is written the way it is: deleting a fence's LINE
breaks the enclosing `do` block, so the operator must make the condition vacuous
instead; and a failed build leaves the previous DAR in place, so a suite then
passes against code the mutation never reached — which reads exactly like a
finding and is not one. Both are now checked, and the second is printed with
every result.

### 3. Architectural Alignment

**This complements the existing tooling and duplicates none of it.** Stated
precisely, because RFP 22 asks how work relates to what exists:

| Tool | Question it answers | Blind to |
|---|---|---|
| `daml-lint` (OpenZeppelin) | Does the source contain a known anti-pattern? | A correct fence with no test behind it |
| `daml-props` (OpenZeppelin) | Does an invariant hold under generated inputs? | Whether the invariant you wrote is the one that matters |
| `daml-verify` (OpenZeppelin) | Can a stated property be proved for all inputs? | Properties nobody stated |
| **This work** | **Would your suite notice if the fence were gone?** | Anything not guarded by a fence |

All three existing tools reason about the contract. This one reasons about the
*test suite*, which is why it finds a different class of problem. The default
should be to extend what exists, and Milestone 1 includes evaluating whether this
belongs as a mode inside `daml-props` rather than as a separate tool. The applicant
will raise that with OpenZeppelin directly, and the answer being "fold it in" is an
acceptable and cheaper outcome of that milestone than shipping a fourth binary.

The catalogue in Milestone 2 aligns with RFP 22's request for "common vulnerability
patterns" and "review checklists", and is intended as input to the Daml Language &
Developer Tooling SIG rather than as a parallel standard.

### 4. Backward Compatibility

No backward compatibility impact. The tool reads a Daml project and runs its
existing test suite; it requires no change to the project under test, adds no
dependency to any package, and produces no on-ledger artefact.

---

## Milestones and Deliverables

Twelve weeks, four milestones. Milestones 3 and 4 are accepted on the harness
running inside Daml projects the applicant does not own, delivered as merged pull
requests the committee can open and read.

### Milestone 1: Standalone harness, and whether it should exist separately
- **Estimated Delivery:** Week 3
- **Focus:** Extract the working harness from one repository into a tool any Daml project can run.
- **Deliverables / Value Metrics:**
  - Command-line tool taking a project path, requiring no modification to the project under test.
  - Correct handling of equivalent mutants, stale mutations, restoration and build-artefact invalidation, each with a regression test.
  - A written evaluation, agreed with the OpenZeppelin maintainers, of whether this belongs inside `daml-props` rather than as a separate tool — with folding it in an acceptable outcome.
  - **Value metric:** the tool runs unmodified against **two Daml projects the applicant did not write**, and its report is correct on both.

### Milestone 2: The pattern catalogue and CI integration
- **Estimated Delivery:** Week 6
- **Focus:** Make the output actionable rather than merely alarming.
- **Deliverables / Value Metrics:**
  - Catalogue of authorisation-fence patterns worth mutating, each entry derived from a real contract and stating what an uncovered instance permits.
  - CI integration that fails a build on a newly uncovered fence, with a documented separate-checkout requirement.
  - Review checklist for Daml authorisation logic, submitted to the Daml Language & Developer Tooling SIG for comment.
  - **Value metric:** catalogue reviewed by at least one SIG member who is not the applicant, with their comments published.

### Milestone 3: Adoption by Daml projects
- **Estimated Delivery:** Week 9
- **Focus:** Somebody else finds a real uncovered fence.
- **Deliverables / Value Metrics:**
  - Integration into **two Daml projects the applicant does not own**, delivered as a pull request to each, with the applicant writing the integration and the host team reviewing and merging it. A harness nobody has heard of does not get adopted; it gets merged when somebody else writes the patch.
  - **Value metric:** **three Daml projects outside the applicant's control running it in CI, and at least one previously-uncovered fence found in a codebase the applicant did not write** — reported publicly with that project's consent, or privately to them with only the count disclosed.

### Milestone 4: Handover
- **Estimated Delivery:** Week 12
- **Focus:** Survive the applicant losing interest.
- **Deliverables / Value Metrics:**
  - Maintainer documentation, and a named second maintainer accepting commit rights.
  - Listed in the Canton Developer Hub with a current SDK version.
  - **Value metric:** a maintainer other than the applicant merges a substantive change.

---

## Acceptance Criteria

The Tech & Ops Committee will evaluate completion based on:

- Deliverables completed as specified for each milestone
- Demonstrated functionality or operational readiness
- Documentation and knowledge transfer provided
- Alignment with stated value metrics

Project-specific acceptance conditions:

1. **Milestone 3 does not pass on the applicant's own repository.** Three external
   Daml projects must run it, and at least one real uncovered fence must be found
   in code the applicant did not write.
2. **The Milestone 1 evaluation must be published even if its conclusion is that
   this tool should not exist separately.** A negative result is a delivered result.
3. **Every quantitative claim in a milestone submission must be reproducible from a
   clean clone** by a reviewer, using a documented command.

Condition 2 is offered deliberately. If the correct answer is that this belongs
inside `daml-props`, the ecosystem is better served by that answer than by a fourth
tool, and the committee should not have to pay for the applicant's reluctance to
reach it.

---

## Funding

**Total Funding Request:** 200,000 CC

Total scope for the twelve weeks is estimated at **$24,000 USDT**, fixed at the
date of submission. The Foundation grant covers the portion below; the applicant
covers the balance as in-kind co-investment, consisting of the existing
MIT-licensed harness — built, public and in CI before this proposal — and continued
maintenance.

### Payment Breakdown by Milestone

- Milestone 1 *(Standalone harness)*: 50,000 CC upon committee acceptance
- Milestone 2 *(Catalogue and CI integration)*: 50,000 CC upon committee acceptance
- Milestone 3 *(Adoption by Daml projects)*: 50,000 CC upon committee acceptance
- Milestone 4 *(Handover)*: 50,000 CC upon final release and acceptance

Milestones 3 and 4 are accepted on integration rather than adoption: merged pull
requests in Daml repositories the applicant does not own, each running the harness
in that project's own CI, named in the submission and openable by anyone. Nothing
is paid for a milestone that is not delivered, which is what the structure above
already means. Waiting to be adopted is waiting to be chosen. Writing the pull
request is work that can start on Monday.

### Volatility Stipulation

Project duration is **under 6 months**. Should the timeline extend beyond six months
due to Committee-requested scope changes, any remaining milestones must be
renegotiated to account for significant USD/CC price volatility.

---

## Co-Marketing

Upon release, the applicant will collaborate with the Foundation on:

- Announcement coordination
- A technical write-up on what a green Daml test suite does and does not prove,
  including the fifteen assertions in the applicant's own code that could not fail
- Developer promotion through the Canton Developer Hub and the Daml Language &
  Developer Tooling SIG

Specific commitment: the write-up will lead with the applicant's own failures
rather than with the tool, because the finding is more useful than the binary.

---

## Motivation

**Who benefits.** Every Daml package whose security depends on an authorisation
check — which is most of them, since authorisation is what Daml is for.

The Foundation's own DevRel survey of 41 active developers (January–February 2026)
found **75% rate Security & Auditing Tools "Important" (51%) or "Critical" (24%)**,
and separately notes that Canton lacks unified tooling "comparable to Hardhat or
Anchor" — a gap that is explicitly about *testing*. This proposal answers the
second finding in service of the first.

The honest estimate is still that the tool is *relevant* to nearly all Daml
projects and *adopted* by far fewer, because mutation testing is slow and its
value is invisible until it finds something. Milestone 3 is written so the
committee pays for the second number and not the first.

The Foundation's roadmap states it "anticipates approving multiple grants" in the
Security, Assurance & Incident Readiness area, and RFP 22 specifically names
"testing methodologies", "common vulnerability patterns", "review checklists" and
"CI/CD integration" — four of the five deliverables here.

**Why this matters more on Canton than elsewhere.** A Daml authorisation fence is
often the *only* thing between a party and an action, because Canton's model puts
authorisation in the contract rather than in an application. That is the right
design and it concentrates risk in exactly the place this tool inspects. A fence
that is present but untested is the specific failure mode that model creates.

**Evidence the problem is real, from this codebase.** Fifteen assertions that could
not fail. A committed contract with a spending fence deleted, which every test
still passed. A tamper detector stubbed to return success while its own test suite
reported the tampered chain as detected. None of these were found by review; all
were found by mutation.

---

## Rationale

**Why mutation and not more static analysis.** Static analysis finds patterns
someone anticipated. The failures above were not anti-patterns — the code looked
correct, and in the fence's case *was* correct. What was wrong was the test, and no
tool that reads only the contract can see that.

**Why restrict to authorisation fences.** General mutation testing of Daml would
generate mostly equivalent mutants and a report nobody reads. Restricting to
authorisation constructs keeps the signal high and the runtime affordable, which is
the difference between a tool that runs in CI and one that runs once.

**Why this applicant.** The harness exists, is public, is MIT-licensed, runs in CI
today, and produced the findings quoted above on the applicant's own code. The
applicant has also shipped a package to PyPI from this repository
(`knowyouragenticai-receipts` 1.0.0, MIT, zero dependencies, 6 September 2026),
which is evidence of the release discipline this proposal asks to be funded for —
not evidence that anyone has adopted anything. The
applicant is an individual, which is a real risk to the committee; Milestone 4
retires it with a named second maintainer inside the grant.

**Relationship to the applicant's other proposal.** A separate proposal addresses
RFP 27 (audit trails and compliance evidence). These are deliberately filed
separately, per the template's guidance that a proposal should have a single
objective: one is development-time assurance tooling, the other is a runtime
evidence format. They share an author and a repository and nothing else. Either can
be funded without the other, and neither depends on the other's acceptance.

---

**Verification.** Every quantitative claim in this proposal was re-run on
2026-09-06 and can be reproduced from a clean clone of
`https://github.com/dominicrume/cantor8_kya_rails` (MIT). The applicant will
provide the exact command for any figure on request, and undertakes to correct any
figure shown to be wrong.
