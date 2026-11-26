# KYA Receipt Chain — External Anchor

**Anchored at:** 2026-11-26T02:09:16Z (UTC)
**Chain head seal:** `b791627b001ffd1d38b44e08048dfeab42a896d0d250eb13dce386241f09b01c`
**Outcome digest:** `b7d5632f6d1951d5869c9740680a23c4d6c6db9660b60743a7564962bfff3de2`
**Disclosure spec:** `know-your-agenticai-disclosure` v1.3
**Receipts in chain:** 1
**Disclosed entries:** 1 (every entry whose outcome is not ACCEPTED)

---

## What this file is

This is an external anchor of a KYA Receipt Chain head. The chain is a tamper-evident log of actions and refusals produced by the `knowyouragenticai-receipts` package (https://pypi.org/project/knowyouragenticai-receipts/).

The verifier inside the package can prove no entry was edited. It cannot by itself prove no entry was deleted from the end. This anchor file closes that limit: by publishing the head seal with a timestamp in a public, append-only context (a Git commit), any later deletion from the tail becomes detectable as a divergence from this anchor.

## The disclosed entry

| Field | Value |
|---|---|
| n | 1 |
| at | 2026-11-26T02:09:16Z |
| what | code review support_tools.py |
| amount | 6 |
| currency | FINDINGS |
| payee | production |
| rule | no_critical_to_production |
| outcome | **REFUSED** |
| prev | GENESIS |
| seal | `b791627b001ffd1d38b44e08048dfeab42a896d0d250eb13dce386241f09b01c` |

Plain reading: an agent reviewed `support_tools.py`, found 6 security findings, and refused to pass the code to production under the rule `no_critical_to_production`. The refusal was sealed to the GENESIS state, and the seal is published here.

## How to verify independently

```
pip install knowyouragenticai-receipts
kya mcp   # or import the verifier library directly
```

Pass `ANCHOR.disclosure.json` from this directory to `kya_verify` and confirm the head returned matches the seal above.

## Honest limits

- Tamper-evident **for mutation**: any edit to a sealed entry breaks the chain and the verifier reports the break.
- Tamper-evident **for truncation** only if this anchor is reachable publicly before a hypothetical truncation. The commit that introduces this file into a public Git repository provides that reachability.
- The disclosure spec withholds entries whose outcome is `ACCEPTED`, because an accepted action may be confidential. All refusals are disclosed in full.
- The outcome digest is a cryptographic hash of the outcome column across the whole chain, including accepted entries that are withheld. It lets a third party confirm the shape of the chain without seeing the confidential contents.
