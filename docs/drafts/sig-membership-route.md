# The documented route from here to a Champion

Everything below was read on 4 November 2026 from
github.com/canton-foundation/canton-dev-fund and is cited by file and line.

## The gate we had wrong

`sig-directory.md` line 39:

  "Under CIP-0100, an external Development Fund proposal requires a Champion
  from the Tech & Ops Committee. SIG membership alone does not give an
  individual or organization formal Champion status."

`Development Fund Proposal Review Process.md` line 28:

  "A proposal moves to 'In Review' once it has been assigned to a champion or
  reviewer."

Two different gates, and we had been treating them as one. A reviewer gets a
proposal into review. A Tech & Ops Committee Champion is what CIP-0100
requires for it to proceed. Asking a SIG member to "champion" it asks for
something the directory says they cannot give.

Yiannis Varelis is listed in Tokenomics (Modeling & Monitoring) only
(sig-directory.md line 214), so the champion half of the ask to him was
misdirected. The validator access half stands and is the stronger half.

## The mechanism we had not read

`sig-directory.md` line 36, under what SIG members may do:

  "Recommend proposals to appropriate members of the Tech & Ops Committee"

That is the route. Not a direct approach to a committee we have no contact
with, but a SIG member recommending the proposal upward.

## Step 1, today, free, no endorsement needed

`sig-directory.md` line 29:

  "Anyone interested in participating in a SIG discussion may request access
  using the SIG participation form. Access to a SIG discussion channel does
  not automatically make someone a listed SIG member."

Form: https://wkf.ms/4qzsS3f
Each SIG has its own Slack channel (line 27). This is the off-thread channel
we did not have.

## Step 2, the two replies already drafted

Georgi Radev and Leonid Rozenberg are both listed SIG members and both
corrected this specification in public. They are owed replies that have been
written and checked. Those replies are now step two of this route rather than
a courtesy.

## Step 3, membership, and the SIG to pick

The rule, lines 68 to 70: one current member of that SIG recommends, a second
member of the same SIG endorses, and at least one of the two must be from an
organisation other than the applicant's.

So the binding constraint is not which SIG fits best. It is which SIG holds
two members, from two different organisations, who have already read this
work.

  DAR Package Management & App Lifecycle (line 268)
    Georgi Radev        LimeChain        mejerr        corrected it 27 Oct
    Simon Meier         Digital Asset    meiersi-da    reviewed the CIP
    Niko Cherkezishvilli Cantor8         cnnickolay    the hackathon this
                                                       repository came from
    Three organisations, three prior contacts.
    Topically exact: digital-asset/dpm IS the Daml Package Manager, our one
    merged contribution to Digital Asset is in it, and both DARs are published
    with a verifiable sha256.

  Identity & Metadata (line 219)
    Leonid Rozenberg    C7               leonidr-c7    corrected it 30 Oct
    Simon Meier         Digital Asset    meiersi-da
    Two organisations, two prior contacts. Also viable.

  Security (line 376)
    Edward Newman       Digital Asset
    Richard Domikis     MPCH
    Stanislav German-Evtushenko  SBI Security Solutions
    Topically closest to refusal evidence. No prior contact with any of them,
    so the endorsements would have to be earned from zero.

  Regulatory Compliance (line 365), which is #860's own label
    Three of the four listed are Digital Asset, plus Nikos Andrikogiannopoulos
    at Metrika. Cross-organisation endorsement is possible but no prior
    contact exists.

First choice: DAR Package Management & App Lifecycle. Not because it is the
best thematic fit for refusal evidence, which is Security, but because it is
the only one where the people who must endorse have already chosen to engage
with the work, and because the package-reproducibility side of this repository
genuinely belongs there.

Nothing is applied for until the replies are posted and a contribution to that
SIG's area exists that is not our own proposal. Membership is "recognizes
individuals who have relevant expertise and are expected to contribute
productively" (line 52), and an application from someone whose only history is
asking for a grant answers that sentence badly.

## The constraint on all of it

`AI_POLICY.md`:

  "Do not open a PR you would not have opened without AI assistance. An AI
  making content cheap to produce is not a reason to produce more of it."

  "Issues and PRs that appear to be unreviewed AI output - overlong and
  padded, referencing things that do not exist, plausible-sounding but wrong
  ... may be closed without further discussion."

#860 carries four comments from one author, several of them long. Whether that
is why it has sat 38 days cannot be known from here and is not claimed. It is
enough that in this repository, volume is a liability rather than evidence of
effort.
