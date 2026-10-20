# Context for AI assistants working on this repo
Project: KYA Rails. Hackathon build, Cantor8 Build on Canton, challenge D1 (spend-limited agent wallet).
Method: read THE-RULES.md first, then the THE-JOB.md of the stage you are working in, and nothing else.
Owner: Rume Dominic (O'Rume Dominic Uririe), Aston University. Creator of the KYA Framework.

Hard rules for any AI touching this code:
- The AI suggests, the human decides. Propose diffs; do not restructure without being asked.
- Spending rules are enforced in Daml (step-1-mandate/KyaMandate.daml). Do not "helpfully" move them to Python.
- Python is stdlib only. No pip installs. This matches the organisers' toolkit constraint.
- The receipt chain canonicalisation MUST stay identical in Python (kya_chain.py) and JS (verifier.html):
  JSON with sorted keys, separators ",", ":", sha256 over canonical(receipt_without_seal) + prev_seal.
- Anything mocked must be labelled MOCKED in code and in the demo. Honesty is scored.
- NEVER run a command whose output is a credential: `git credential-* get`,
  `gh auth token`, `cat ~/.netrc`, `env | grep -i secret`. To check whether one
  exists, print its length or a boolean. This is here because an assistant
  debugging a push printed a live GitHub token into the transcript on
  2026-09-13. Every secret scanner in this repository reads FILES, so none of
  them could have caught it.
- The organisers' toolkit lives at ~/hackathon-toolkit. Read it, call it, never edit it.
- NOTHING IS PUBLISHED to PyPI, npm, GitHub Pages or any public index unless the
  exact package name and version has been stated and approved in that message.
  "Publish it" is not approval; "publish knowyouragenticai-receipts 1.0.0" is. This was
  written after an AI read "we publish the auditor" as authority to cut a release
  of a different project, and did.
- The OTC desk moved OUT on 2026-09-12, to its own repository. The operator
  and customer screens, the WhatsApp bot, the Breet and Meta webhooks and the
  desk settings are no longer here. What stayed is the evidence layer: the
  mandate, the agent, the verifier, the MCP wallet, the receipt package and the
  sealed journal the wallet writes through to. Do not add a payment screen, a
  webhook or a wallet address back into this repository; if the work needs one,
  it belongs in the desk repo. The desk's Daml modules (KyaCycle, KyaInbound,
  KyaQuote) DID stay in step-1-mandate, and must: kya-rails-mandate 1.1.0 is
  vetted on DevNet, and Canton's upgrade check refuses a version that drops a
  data type its predecessor had.
- No wallet address that a wallet would accept may exist anywhere in this tree,
  including in a doc, a comment, a test fixture or a commit you are about to
  make. tests/no_real_addresses.py decodes Base58Check, EIP-55 and bech32 and
  fails on anything spendable. This rule exists because the customer screen
  served the USDT TRC20 contract address for two weeks.
- kya-rails and the AI code auditor are SEPARATE PROJECTS. kya-rails is the
  Canton work. The auditor (~/Downloads/NEW-enterprise-ai-code-quality-auditor,
  PyPI: ai-code-quality-auditor) is the owner's MSc dissertation tool and has no
  Canton content. Work on one is never a reason to release the other, and a
  version number belonging to one is never bumped for work done in the other.
- DECIDE FROM THE DATA, NOT FROM THE STORY. Before recommending a direction,
  go and measure it, and say which numbers you actually read. This rule was
  written after a comparison against the hackathon winners produced the
  opposite of the expected answer: 1st place last committed 29 August with 34
  commits, 2nd place 29 August with 21, and this repository 16 October with
  over 100. The assumption was "they built more". The data said they stopped
  on the day and won on presentation. Every plan built on the assumption would
  have been wrong.
  The same rule caught three live overclaims in one week: "nobody else keeps
  the refusal half" (sentry does), "the EU AI Act requires this" (Annex III
  does not cover payments), and "241 downloads a month" (84 once mirrors are
  excluded, and that figure was already printed on a CV). A number nobody has
  plotted is a rumour. If a claim cannot be checked by a stranger in one
  command, it does not go in a document, a proposal, or a sentence said out
  loud.
- NEVER A BETTER YESTERDAY. The direction is forward. A measurement that was
  true last month is not evidence today, a claim that was defensible before a
  competitor shipped is not defensible after, and a plan built on either is a
  plan built on a memory. When something is found to be wrong, it gets
  corrected in the open with the reason written down, and the correction is
  the work, not an interruption to it. Nothing in this repository is ever
  quietly tidied to look better than it was.
- MEASURE AGAINST WHOEVER IS AHEAD, FROM THEIR ARTEFACTS, NOT FROM THEIR
  REPUTATION. docs/measured-against-the-winners.md is that table and it is
  kept current. It is why this repository has STATUS.md at all.
- STATUS.md and ASK-THE-ORGANISERS.md are kept current, not written once.
  The first separates proven from mocked from pending so a reader with four
  minutes can see the shape of the project. The second holds the questions to
  ask the people who run this ecosystem, written down BEFORE the conversation.
  Both exist because the team that won the hackathon had them and this did not.
- NOTHING IS POSTED THAT IS NOT BUILT. Every reply, forum post, proposal
  comment and outreach message reports something finished, tested and
  pushed. Not a plan, not a design, not a half-fix with the remainder
  described. If it is not built, the post waits until it is.
  This was written after a reply to a named engineer went through three
  drafts in a day because the design kept changing underneath it, and after
  a developer asked in her own words for "sample implementations" and was
  sent four paragraphs of documentation quotes with no code in them. She
  asked for code. The answer was to go and write the module, test it,
  mutation-test it, and then reply with something she could paste.
  The order is: build, test, break it on purpose to prove the tests are
  real, run the full sweep, push, and only then write the message. A post
  about work in progress invites a conversation. A post about finished work
  invites a user.
  The limit of what was built is still stated, because a limit discovered by
  the reader costs more than one declared by the author. But it is stated as
  a property of a finished thing, not as an excuse for an unfinished one.

- Before any release, verify rather than assume: build from committed code and
  never the working tree, list every file that would go public, scan the built
  artefacts for secrets WITH A POSITIVE CONTROL proving the scan reads them,
  and install the artefact into a clean environment and run it. A PyPI version
  number cannot be reused once taken.
