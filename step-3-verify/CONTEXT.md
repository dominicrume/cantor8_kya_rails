# CONTEXT.md (Layer 2, stage 3: what do I do?)

## Job

Let a judge verify the receipt chain themselves, offline, in one tap, and let them break it with the tamper button so they feel why the seals matter.

## Inputs

| File | Why |
| --- | --- |
| receipts.js | the sealed chain produced by stage 2, never handwritten |
| ../THE-RULES.md | honesty banner text, nothing overclaimed |

## Process

verifier.html is fully self-contained: no network, no build step. It replays the story in a phone frame, recomputes every seal in the browser with a stableStringify that matches Python's canonical form byte for byte, and shows the Moniepoint-style transaction overlay. The tamper button edits receipt 2 in memory and every later seal must turn red.

## Output

A green chain a judge verified with their own hands, or a red cascade that proves tampering cannot hide. This file is the judged surface; do not change it, only amplify around it. THE-JOB.md holds the fuller narrative.
