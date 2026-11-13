Destination: https://www.openzeppelin.com/careers/opening?gh_jid=7742510003
Role: Senior Blockchain Security Developer (Canton), Secure Development, remote
Written: 2026-11-13. NOT SENT. Rume submits this himself; nobody applies for a
job as him without him reading it first.

Process, from their Logistics section, so there is no surprise: recruiter call
30-45 min, manager 60, team 45, leadership 30, then a PAID TECHNICAL WORK
TRIAL, targeting about 30 days end to end. They state that automated tools
including AI help review applications, with human review of all hiring
decisions, and that a human review can be requested at talent@openzeppelin.com.

---

## COVER LETTER (paste into the cover letter field)

I build adversarial evidence infrastructure in Daml on Canton, and I would
rather show you than tell you.

    git clone https://github.com/dominicrume/cantor8_kya_rails
    cd cantor8_kya_rails && python3 tools/prove_refusal_on_sandbox.py

That starts a real Canton participant, sequencer and mediator locally, runs a
script that does not exist and REQUIRES it to fail, and only then runs the
real one. Canton refuses a 90.0 charge against a mandate with 40.0 already
spent, writes a refusal record naming the rule, and leaves the spent total
untouched. If the control passes, the tool refuses to report the real result,
because a harness that can only say "pass" cannot tell you whether it ran.

The tool also prints what it does not prove: single-participant local Canton,
no Amulet, so nothing about a shared network or Canton Coin.

Three things in your posting I can evidence rather than assert.

Production Daml and multi-party authorization. 166 Daml files and 171 passing
scripts across two packages. The design decision I would defend is putting the
auditor on the signatory line rather than the observer line: a create needs
every signatory's authority, so a compromised node holding one party's key
cannot bring the contract into existence at all. One test shows the limit of
that too, which matters more: a consuming choice archives on the controller's
authority alone, so one ordinary owner-controlled choice still moves an asset
past the journal. That is a specification hole, and it is named in the file
rather than left for a reader to find.

A security-first mindset, which you call non-negotiable. 82 mutation rows:
each deletes a real fence, rebuilds, and requires a NAMED test to go red, so
no assertion is decoration. Two audits found 15 assertions that could never
fail. The harness exists to stop the sixteenth.

An AI-native workflow. I use Claude Code daily and hold its output to the
standard of a colleague's pull request, which in practice means gates rather
than trust: a tool that refuses to open anything in another repository unless
a test goes red, a tool that reads the destination back after posting instead
of recording a keystroke, and a lint that makes every stated count re-derive
from the file that produces it. That lint caught six wrong numbers in my own
repository this week, including two the previous version of the gate was
structurally unable to see.

One thing your posting asks for that I do not have, said here rather than
found later: production DeFi. I have shipped no AMM, no vault, no lending
protocol and no cross-chain settlement, and your year-one work is exactly
that. What I bring to it is Canton-specific authorization judgment and an
unusually literal habit about what evidence does and does not support.

My one merged contribution outside my own repositories is digital-asset/dpm
#330, approved and merged in six days by a maintainer of that repository. It
is small and it is real, and you can read the review on the pull request.

O'Rume Dominic Uririe, Birmingham, United Kingdom.

---

## LINKS FIELD

Repository: https://github.com/dominicrume/cantor8_kya_rails
Merged upstream: https://github.com/digital-asset/dpm/pull/330
Published package: https://pypi.org/project/knowyouragenticai-receipts/
Research: https://github.com/dominicrume/cantor8_kya_rails/blob/main/docs/dev-fund-vote-mechanism.md
X: https://x.com/dominicrume

---

## NOTES FOR RUME BEFORE YOU SEND

1. The repository link is the whole application. Make sure the command in the
   letter runs on a clean clone before you press submit. If it does not, the
   letter is a liability rather than an asset.
2. The DeFi paragraph stays. A limit you declare costs less than one a
   reviewer finds, and they will find this one in the first call.
3. Do not add the hackathon placing. It is not evidence to this audience and
   it dilutes the parts that are.
4. The work trial is paid and it is where you actually win. Everything above
   exists only to reach it.
