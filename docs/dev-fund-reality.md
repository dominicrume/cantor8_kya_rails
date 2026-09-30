# How the Canton Dev Fund actually works

> ## THIS DOCUMENT WAS OVERTAKEN. Re-measured 27 September 2026.
>
> **The champion gate described below no longer exists.**
> `.github/workflows/champion-check.yml` has been deleted from
> `canton-foundation/canton-dev-fund`. No workflow now closes a proposal for
> naming the wrong champion, and the pull request template explicitly accepts
> **`Needs Champion`** as a valid value.
>
> The fund moved to **Dev Fund 2.0** on 22 September. The gate is now
> `rfp-category-check.yml`: a proposal is closed only if it references **no RFP
> category at all**, and on 24 September they merged a fix to leave proposals
> open when that check cannot run.
>
> **CORRECTION TO THIS CORRECTION, 29 September.** "Removed" was too strong and
> wrong in the other direction. The champion requirement is alive and is
> **CIP-0100**: "If no champion can be found... funding from the development
> fund will not be available." Proposals #851 and #811 were auto-closed for it
> on 21 and 18 September, citing that CIP by name.
>
> What changed is ENFORCEMENT, not the rule. Every proposal filed since Dev
> Fund 2.0 merged on 22 September is still open and none carries a champion
> label. The robot stopped closing them.
>
> So filing was right and #860 is safe, AND it will not be funded without a
> champion. Both are true. The route to one is the SIG directory: our proposal
> is labelled `regulatory-compliance`, that SIG has four named members, two with
> public GitHub handles, and the review process says SIG members may self-assign
> proposals and that SIG participation is not limited to Foundation members.
>
> **WHAT A CHAMPION ACTUALLY IS, 30 September.** Not a supporter. A seat.
> CIP-0100: "The Tech & Ops committee should request **one of its members** to
> become the champion of the external contributor and **represent them in the
> committee**." Any Canton Foundation member organisation may attend that
> committee; it elects five voting members and two alternates, quarterly, and
> those five decide.
>
> So a champion must hold a seat. An ecosystem service provider, however
> friendly, is not automatically one. What a friendly non-member CAN do is
> introduce you to someone who is, which is the shortest real path and is worth
> more than the label.
>
> **What this changes.** Everything in this project that waited on finding a
> champion was waiting for the wrong thing: not a name on a list, but a Tech &
> Ops member willing to represent it, reachable through the SIG the proposal is
> already labelled into. `docs/dev-fund-proposal.md`
> already says `Needs Champion`, already names RFP 27, and already contains the
> phrases "audit trails" and "compliance evidence", which are three of the
> keywords the live checker matches. It would be labelled
> `rfp-27:security-monitoring` today.
>
> **RFP 27 is "Security Monitoring, Auditability and Evidence"**, and asks for
> "audit trails, compliance evidence... while preserving Canton's privacy
> model... how privacy, access controls, and selective disclosure will be
> handled". It also says the Foundation anticipates approving *multiple* grants
> there.
>
> Not RFP 11. "Public verifiability" sounds like this project and is not: it
> asks for public aggregates of price and volume, which is the opposite of
> selective disclosure to a named auditor.
>
> The measurement below was true on 11 September. It is kept because the lesson
> is not that the fund changed; it is that a measured fact has a shelf life, and
> a strategy built on one needs re-measuring before it is used to say no.


Measured on 2026-09-11 from the public repository, not from the documentation.
Everything here is reproducible with `gh`; the numbers are counts, not
impressions.

**This is an internal note.** Publishing it would read as criticism of the
people whose sponsorship the work needs. The facts are useful; the tone of a
public version would have to be different, and the value of knowing them does
not depend on saying them out loud.

---

## The gate is a regex, not a committee

`.github/workflows/champion-check.yml` runs on every proposal PR at open. It
scans for a line containing `champion`, `endorser` or `sponsor`, and closes
the pull request unless the value matches this list:

> intellecteu · canton foundation · digital asset · zenith · temple ·
> t-rize/trize · cumberland · obsidian · fdf technologies/fdftech ·
> sygnumbank/sygnum · broadridge · xdao · paideia · mouro capital · sv group

Eighteen names. **Cantor8 is not one of them.** A proposal naming Cantor8 as
its champion is closed automatically, in seconds, with no human involved.

## Almost nothing is rejected. Things are filtered

Of the last 70 closed proposals:

| closed by | count |
|---|---:|
| `github-actions[bot]` | **63** |
| a person | 7 |

"The Dev Fund rejected it" is almost always "a regex closed it before anyone
read it". Two examples, nine seconds apart in behaviour and seventeen days
apart in outcome:

| | #665 Woof — Canton Risk Engine | #784 Predge — Agent Reputation |
|---|---|---|
| opened | 25 Aug 10:55:53 | 10 Sep 19:43:32 |
| auto-closed | 10:56:03 — **10s** | 19:43:41 — **9s** |
| champion field | `Needs Champion` | `Cantor8 (Reni Achkar)` |
| reopened | **by `Jatinp26`, 9½ hours later** | never |
| today | open, labelled `rfp-13:payments-defi` | closed |

Both were auto-closed for the same reason. One had a human reopen it. That
human intervention is the entire difference, and it is the only part of this
process worth optimising for.

## Two thirds of the open queue is stuck at the same gate

Of 45 open proposals sampled:

| | count |
|---|---:|
| champion the bot accepts | **13** |
| placeholder or unrecognised organisation | **30** |
| no champion field at all | 2 |

**121 proposals are open. 48 have ever been accepted.** Of the 42 merged since
the bot went live, most are maintenance by insiders — a dozen alone from one
Foundation account ("Names updated", "Link fix", "Approval date fix") — plus
amendments to work already funded. Genuinely new external proposals accepted
in the last three months: roughly six.

So a stalled proposal is not evidence of a weak proposal. It is the median
state of the queue.

## Who actually champions

From the same 45:

| champion | proposals |
|---|---:|
| **Digital Asset** | **5** — Wayne Collier (×2), Itai Segall, Curtis Hrischuk |
| Canton Foundation | 4 — incl. `hythloda` (Amanda Martin) |
| IntellectEU | 3 |
| Zenith | 1 — Heslin Kim |

**Digital Asset champions more than anyone.** They are also the owner of
`daml-finance` — 71 authorisation fences, which this repository is mutation
testing now. The organisation most likely to champion is the organisation
whose flagship library we are about to hand a findings record to. That is not
a coincidence to exploit; it is a reason the order of operations matters.

## What follows

**Drafting is not the bottleneck.** Two proposals sit finished in this
repository. Neither can pass a gate that reads one field.

**IntellectEU is out as a route.** Twelve Daml repositories, zero `assertMsg`
between them — measured with `tools/ecosystem_scan.py`. Nothing to offer them.

**Digital Asset is the route.** Most active champion, most fences, named and
reachable people, and work already underway that is useful to them before
anything is asked for.

**Being auto-closed is not fatal.** Woof was closed in ten seconds and
reopened the same evening. File when there is a name, and know that the bot
closing it is the beginning rather than the end.

---

*Reproduce: `gh pr list -R canton-foundation/canton-dev-fund --state all`,
then read `.github/workflows/champion-check.yml`.*
