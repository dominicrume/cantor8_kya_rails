# How the Canton Dev Fund actually works

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
