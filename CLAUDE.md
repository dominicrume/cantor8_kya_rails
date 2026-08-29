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
