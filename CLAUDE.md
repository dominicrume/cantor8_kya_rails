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
- Before any release, verify rather than assume: build from committed code and
  never the working tree, list every file that would go public, scan the built
  artefacts for secrets WITH A POSITIVE CONTROL proving the scan reads them,
  and install the artefact into a clean environment and run it. A PyPI version
  number cannot be reused once taken.
