# HackCanton Season 4, registration form answers

**Run by NODERS LLC.** Note it says **Season 4**, not 3. My earlier figures
(up to $50,000, Grand Final 14 October) were **Season 3's**. Read S4's own
prize pool and dates off the form or the announcement. Do not assume they
carried over.

---

## Page 3, the four questions

### Primary role

**Smart contracts / Daml**

Not "Full-stack", even though you are. This is the rarest skill in the room
and the one the organisers are shortest of. It gets you onto a team as the
person who can actually write the contract rather than the person who can do
a bit of everything.

You have two Daml packages on SDK 3.4.11, 111 test scripts, 32 spending
fences each proven load-bearing, and an on-ledger design a Canton Community
Tech Partner reviewed. That answer is not a stretch.

### Skills / Stack

Paste this:

```
Daml (SDK 3.4.11), Canton, Python (stdlib only, zero dependencies),
JavaScript, Go, SQLite, Git, GitHub Actions, Bash. Mutation testing and
conformance vectors across three languages.
```

Every item is in the repository. The three languages are the Python,
JavaScript and Go implementations of the same specification, which all agree
on 20 conformance vectors. "Stdlib only, zero dependencies" is worth saying
out loud because almost nobody does it and it signals a particular kind of
discipline.

### Experience level

**Advanced.**

I know the instinct is Intermediate because Daml is a month old for you. Do
not. The question is what you can do. Not how long you have been doing it.
The evidence is public:

- two Daml packages, one reusable with no dependencies beyond the standard
  library
- 111 Daml test scripts, 42 test suites, 82 mutations where each one breaks
  something real and requires a *named* test to go red
- a written specification implemented three times independently and agreeing
- three pull requests merged into the official Canton Developer Hub
- eight fixes contributed to the Cantor8 hackathon toolkit
- a Development Fund proposal open under RFP 27
- an upgrade-safe Daml design, with the Canton upgrade rules understood well
  enough to keep three modules in a vetted package deliberately

Beginner and Intermediate both put you on a team being taught. Advanced puts
you on a team building. If anyone questions it, the repository answers in
thirty seconds.

### Have you participated in HackCanton before?

**No, this is my first season.**

The Cantor8 "Build on Canton" hackathon on 29 to 31 August was a different
event by a different organiser. HackCanton is run by NODERS. Say no.

---

## For the pages you have not reached yet

Likely fields, and the answer that is already written.

| field | use |
|---|---|
| project name | **Know Your AgenticAI** |
| one line | "On Canton a blocked action leaves nothing behind. I built the record that survives it, and a regulator can check it without trusting the operator." |
| description | the long version in `hackcanton-s3-entry.md`, unchanged |
| links | repo, verifier, the example file, PyPI, PR #860, SPEC.md |
| team or solo | **solo**, unless they pair you |
| GitHub | `github.com/dominicrume` |

## If it asks why you are joining

```
I have a working Canton project and no users. I am joining to put it in
front of people who build on Canton, and to be told what is wrong with it.
The last time someone did that, on the forum in September, they found a
real hole in the design and I shipped the fix the next day.
```

That is true, it is checkable, and it is the opposite of what everyone else
will write.

## One thing not to do

Do not describe this as a hackathon project. It is a month old, it has been
rebuilt twice, and one of the rebuilds came from outside review. Say that.
The organisers see a hundred five-week prototypes and almost nothing that
arrived already tested.
