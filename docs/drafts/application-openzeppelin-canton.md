Destination: https://www.openzeppelin.com/careers/opening?gh_jid=7742510003
Role: Senior Blockchain Security Developer (Canton), Secure Development, remote
Written: 2026-11-14, replacing the 2026-11-13 draft. NOT SENT.

Nobody applies for a job as you without you reading it first. This file holds
every word that goes in the form, and a list of the fields only you can answer.

Their process, from the posting: recruiter call, manager interview, team
interview, leadership interview, then a PAID TECHNICAL WORK TRIAL, about 30
days end to end. They say AI tools help screen applications, with human review
of every decision, and a human review can be asked for at
talent@openzeppelin.com.

---

## BEFORE YOU SUBMIT, in this order

1. `git push origin main`. The command in the cover letter only works from a
   clean clone once the fix for it is on GitHub. On 14 November it was not.
2. Fill the placeholders in docs/drafts/cv/cv.html, then rebuild cv.pdf.
3. Submit.

---

## COVER LETTER

I build adversarial evidence tools in Daml on Canton, and I would rather show
you than describe it.

    git clone https://github.com/dominicrume/cantor8_kya_rails
    cd cantor8_kya_rails && python3 tools/prove_refusal_on_sandbox.py

That builds the Daml, starts a real Canton participant, sequencer and mediator
on your machine, and runs a script that does not exist, which must fail. Only
then does it run the real one: Canton refuses a charge of 90.0 against a
mandate with 40.0 already spent, writes a refusal record naming the rule, and
leaves the spent total untouched. If the control passes, the tool refuses to
report. It also prints what it does not prove: this is one local participant,
not a shared network, and there is no Canton Coin.

Three things in your posting, with evidence.

Security first. Every one of my 32 Daml fences is deleted in turn, and a named
test must go red. A wider suite breaks 82 real things the same way. In
September I ran that harness on two of your Canton packages, after your forum
thread invited people to clone the repos and open an issue. 49 of 62 fences
had no test that failed when the fence was made vacuous, at pinned commits
c96456f and fbc6392. That is a coverage finding and not a vulnerability. I
opened public issues.

Being wrong in public. Georgi Radev showed on the Canton forum that a guard
signatory alone does not gate owner-controlled choices. My test wallet had no
owner-controlled choices, so my suite could not see it. I wrote the test that
proves the hole, named it for what it shows, and put it in the draft
specification as a requirement, credited to him.

An AI workflow with checks. I use Claude Code every day. This week my own tool
printed that an auditor's copy of a refusal survives pruning. It was true and
meaningless, because the prune never reached the event. Asking whether the
owner's node still held it too exposed that. I then found a stronger claim
that I had written and not tested, and corrected it before it was published.

What I do not have: production DeFi. I have shipped no AMM, vault, lending
protocol or cross-chain settlement, and your first-year work is exactly that.

One merged contribution outside my own repositories: digital-asset/dpm #330.

Dominic O'Rume, Birmingham, United Kingdom.

---

## FORM ANSWER 1
"Our mission is to accelerate the world’s transition to an open financial system. How do you identify with that mission?"

An open financial system is one a stranger can check. That is what I care
about, and it is what I build.

My work is about refusals. When a system stops something, the stop should sit
on a record that the stopped party cannot quietly delete. The claim I find
hardest to trust is the one nobody outside can test. So I try to make mine
testable with one command, and I print what they do not prove.

OpenZeppelin has done this for years by publishing libraries and reviews in
the open. Canton is where it matters next. Its privacy means fewer people can
look, so the few who do carry more weight.

---

## FORM ANSWER 2
"What has been your experience working with Canton to this point?"

About eleven weeks, since the Cantor8 hackathon in London on 29 August 2026,
where I placed third.

I wrote two main Daml packages. One is a spending mandate that Canton itself
enforces. The other is a refusal journal with the auditor as a signatory, so a
second journal cannot be created. 173 Daml scripts pass. Version 1.1.0 of the
mandate package was vetted on DevNet under Canton's upgrade check. I run real
Canton locally, including two participants to test pruning. That work is not
finished.

I have one merged pull request in digital-asset/dpm and three in the Canton
Developer Hub. Engineers have reviewed my design in public on the forum.

What I have not done: run on a shared network under load, or ship production
DeFi.

---

## FORM ANSWER 3
"Describe an instance where you built tools that other people have leveraged for their benefit."

The honest answer first: less than I would like. My own repository has no
outside contributors and no outside issues. My package has 488 installs, which
I count as installs and not users.

What others have used are two changes that someone else reviewed and merged.

In dpm, a bad path given to --auth was silently ignored, so the tool carried
on without logging in. I made it stop with an error. It was merged in six
days.

In the Canton Developer Hub, 19 of 56 catalogue entries declared several
links, but each card showed only the first. I fixed that, and it was merged.

Both are small. I chose them because they are the ones another person
checked.

---

## FORM ANSWER 4
"How do you leverage AI in your daily workflow?"

Claude Code is open all day. I treat its output like a colleague's pull
request, which means it does not count until something checks it. So I build
the checks.

A gate refuses to let me post a quote that is not in a source file, or a claim
about someone's employer with no link. This week it refused a made-up first
name with a company attached. Every test harness I write runs a control that
must fail first.

An audit of my own repository found six wrong numbers, including a README that
said 30 fences when the file had 32. My gates had passed all of them, so I
fixed the gates.

I also use agents for research, and I check them. One told me a pull request
of mine duplicated another. I read both diffs. They touch different files, so
I did not close it.

---

## FIELDS ONLY YOU CAN ANSWER

I do not know these and I will not guess them. Answer each truthfully.

- Email, phone, and your LinkedIn profile URL.
- What time zone do you legally reside in? You live in Birmingham, so this is
  probably the UK option, but read the list.
- What is your country of residency? Probably the United Kingdom.
- Do you have the right to work in your country of residency? Yours to answer.
- Do you require visa sponsorship from OpenZeppelin, now or in the future?
  Yours to answer. A wrong answer here costs you more than a slow one.
