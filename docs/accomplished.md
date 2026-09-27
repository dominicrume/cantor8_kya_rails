# What has actually been achieved

*29 days, 29 August to 27 September 2026. Every number below came from the
GitHub, PyPI and Canton forum APIs today, not from memory. Where a number is
zero it says zero.*

---

## Shipped, and other people can use it

| | what | evidence |
|---|---|---|
| **A published format** | `knowyouragenticai-receipts`, live on PyPI since 6 September | 2 releases, 189 downloads a month |
| **A published tool** | `ai-code-quality-auditor`, live since 31 May, now at 0.5.1 | 6 releases, 311 downloads a month |
| **A reusable Daml package** | `canton-refusal-record` 1.0.0: one module, no dependencies beyond the standard library | 8 scripts, incl. a lending protocol and a collateral engine that have no concept of a payee |
| **A written specification** | `SPEC.md` with 20 conformance vectors | three independent implementations, Python, JavaScript and Go, agree on all 20 |
| **A verifier that needs nothing** | drop a file on a web page, no wallet, no install, no network | works offline |

## Accepted by people who are not us

| | what | when |
|---|---|---|
| **3 pull requests merged** into the Canton Developer Hub | #156 added the listing, #160 fixed link rendering for **nineteen** entries of which one was ours, #168 rewrote the entry | 8 and 21 September |
| **A public catalogue listing** | "Know Your AgenticAI" in the official Canton Developer Hub | live now |
| **2 more merged** into `veritaport/VFS-Core` | a Polygon audit stamp, and an enterprise API layer | private repo, so unverifiable by outsiders |

## Given away, no reply asked for

| | what |
|---|---|
| **8 contributions to the organisers' own toolkit** | `Cantor8/hackathon-toolkit`: issues #3, #4, #5, #6 and pull requests #7, #8, #9, #10. Token caching past expiry, `find_party` walking every party, `C8_USER` silently ignored, a stale README |
| **3 findings filed at OpenZeppelin** | 69 authorisation fences examined across three Canton repositories; **52 could be made vacuous with every test still passing** |

## The engineering, which is the unusual part

| | |
|---|---|
| **42 test suites**, all green | one command rebuilds and runs everything |
| **82 mutations** | each breaks something real and requires a *named* test to go red. None blind, none stale |
| **111 Daml scripts** | across two packages |
| **32 spending fences**, each proven load-bearing | delete any one and a named test fails |
| **142 commits** in 29 days | |

Two independent audits found **15 assertions that could not fail** and **35
false statements**. The mutation harness exists because of them. It has since
caught its own blind spots more than once.

## Found by asking, not by building

| | |
|---|---|
| **A design review from a stranger** | Federico_Rodriguez, a Canton **Community Tech Partner** at Moonsong Labs, read the architecture unprompted, identified that application-written receipts cannot prove completeness, and specified the fix. It shipped the next day with his name on it |
| **A real prospect identified** | Mr_Tuddles, Pearl Digital Treasury: stablecoins on testnets with agentic payments, porting to Canton |
| **Their own marketing confirms the gap** | Pearl's page: *"If any check fails, the transfer is rejected and logged. Nothing rule-breaking reaches the chain."* Logged where? Their own system |
| **Two forum threads, 519 views** | 6 of the 17 posts are ours |

## Honest numbers

| | |
|---|---|
| **Revenue** | **£0.** Nothing has ever been invoiced or received |
| **GitHub stars** | **0.** Forks 0. Watchers 0 |
| **Real conversations** | **3 rows**, two people |
| **Outside chains produced** | **none.** Nobody outside this project has yet made one |
| **`TryCharge` on a real ledger** | never run. No DevNet secret |
| **Dev Fund** | proposal written, never filed. Naming Cantor8 as champion gets it auto-closed in 9 seconds |

---

## The one sentence

Twenty-nine days. From nothing to this:

- a published format, implemented three times
- a reusable Daml package
- three merged pull requests into a repository that is not ours
- a listing in the official Canton catalogue
- eleven unpaid contributions to two other teams
- a design review from a Canton Community Tech Partner, who was right, and
  who was credited for it in public

**It has earned nothing. Nobody outside has used it yet.**

Both halves are true. The first half is why the second half is a distribution
problem rather than a quality problem.
