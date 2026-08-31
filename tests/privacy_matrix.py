#!/usr/bin/env python3
"""Generate the privacy matrix from the Daml, so it cannot drift from it.

Who signs a contract, who observes it, and -- the column that is the actual
design -- who is excluded. A matrix typed by hand is a claim; one read out of
the source is a fact, and it goes stale the moment someone adds an observer
without updating it.

    python3 tests/privacy_matrix.py            print it
    python3 tests/privacy_matrix.py --check    fail if docs/privacy-matrix.md is stale
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAML = os.path.join(ROOT, "step-1-mandate", "daml")
OUT = os.path.join(ROOT, "docs", "privacy-matrix.md")

# Everyone who appears anywhere, so "excluded" can be computed rather than guessed.
def parties_in(text):
    found = set()
    for m in re.finditer(r"^\s+(\w+)\s*:\s*Party\s*$", text, re.M):
        found.add(m.group(1))
    for m in re.finditer(r"^\s+(\w+)\s*:\s*Optional Party\s*$", text, re.M):
        found.add(m.group(1))
    return found


def templates():
    out = []
    for fn in sorted(os.listdir(DAML)):
        if not fn.endswith(".daml"):
            continue
        src = open(os.path.join(DAML, fn)).read()
        # split on template boundaries, keeping the name
        blocks = re.split(r"^template\s+(\w+)", src, flags=re.M)
        for i in range(1, len(blocks), 2):
            name, body = blocks[i], blocks[i + 1]
            sig = re.search(r"^\s+signatory\s+(.+)$", body, re.M)
            obs = re.search(r"^\s+observer\s+(.+)$", body, re.M)
            fields = parties_in(body.split("where")[0])
            out.append({
                "module": fn.replace(".daml", ""),
                "name": name,
                "signatory": clean(sig.group(1)) if sig else [],
                "observer": clean(obs.group(1)) if obs else [],
                "fields": sorted(fields),
            })
    return out


def clean(s):
    s = re.sub(r"--.*", "", s)
    s = re.sub(r"optional \[\] \(\\p -> \[p\]\)\s*", "", s)
    return [p.strip() for p in s.split(",") if p.strip()]


def render(ts):
    rows = []
    for t in ts:
        can_see = set(t["signatory"]) | set(t["observer"])
        excluded = [f for f in t["fields"] if f not in can_see]
        rows.append("| `%s` | %s | %s | %s |" % (
            t["name"],
            ", ".join("`%s`" % p for p in t["signatory"]) or "—",
            ", ".join("`%s`" % p for p in t["observer"]) or "—",
            ", ".join("`%s`" % p for p in excluded) + (", **everyone else**"
                                                      if excluded else "**everyone else**")))
    return rows


def build():
    ts = templates()
    lines = [
        "# Privacy matrix",
        "",
        "Who signs each contract, who observes it, and who is **excluded**. The",
        "exclusions are the design: on Canton a non-observer receives nothing —",
        "not an encrypted payload, not a hash, zero bytes — so a party absent",
        "from a row cannot see that the contract exists.",
        "",
        "*Generated from the Daml by `tests/privacy_matrix.py`. CI fails if this",
        "file drifts from the source, because a privacy claim written by hand is",
        "a claim and one read out of the contracts is a fact.*",
        "",
        "| Contract | Signatories | Observers | Excluded |",
        "| --- | --- | --- | --- |",
    ]
    lines += render(ts)
    lines += [
        "",
        "## What the exclusions buy",
        "",
        "**The operator never sees the desk's margin.** `KyaMandate` and the books",
        "are signed by the principal; an operator observes only what it must act on.",
        "",
        "**A payee sees their own payment and nothing else.** `ChargeRecord` has",
        "`observer payee`, so a counterparty can verify what they were paid without",
        "gaining sight of the cap, the float, or any other payee.",
        "",
        "**A watcher cannot see a quote.** This is the structural difference from a",
        "public chain, where a deposit address is monitorable by anyone and that is",
        "what makes a false claim cheap to fabricate. On Canton the counterpart to a",
        "deal is visible only to its parties.",
        "",
        "**A feed sees one deal and can confirm one fact.** The bank feed and the",
        "deposit feed observe only the deals they must confirm, and neither can pay",
        "anyone. Narrow sight and narrow authority, deliberately matched.",
        "",
        "**The customer sees their own deal.** `DepositInstruction` and `Release`",
        "carry `observer customer`, so \"you sent me the wrong address\" and \"I was",
        "never paid\" are questions with answers on the ledger rather than arguments",
        "in a chat log.",
        "",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    text = build()
    if "--check" in sys.argv:
        cur = open(OUT).read() if os.path.exists(OUT) else ""
        if cur != text:
            print("docs/privacy-matrix.md is stale. Regenerate:")
            print("  python3 tests/privacy_matrix.py > docs/privacy-matrix.md")
            sys.exit(1)
        print("privacy matrix matches the Daml")
    else:
        sys.stdout.write(text)
