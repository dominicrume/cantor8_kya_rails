#!/usr/bin/env python3
"""Count refused actions in a stream of Canton updates.

WHY THIS EXISTS. A monitor that reads a Canton participant through the Update
and State services sees committed activity only. A Daml check that refuses an
action aborts the transaction, so it produces no update at all and never
reaches the stream. The rejection goes to the command completion service,
which only the submitting application can read, so it is not independent
evidence either.

That leaves a monitor able to score what happened and not what a control
stopped. The denominator is missing.

The fix needs nothing from the monitor. If a refusal is written as a CONTRACT
rather than thrown as an error, it is an ordinary created event and any
adapter already carries it. This module is the consumer side of that: give it
the records an adapter publishes and it reports the refusal count, the attempt
count and the rate, per party.

THE PRIVACY PROPERTY, which is the part worth noticing. Adapters commonly hash
contract payloads rather than retaining them. With payloads hashed, a refusal
record still arrives with its template_id and its witness parties, so the
COUNT is visible while the reason stays unreadable. An auditor gets the
denominator without the monitor learning what was refused, which is the whole
shape this package is for. Nothing here needs payloads, and `payload_hash` is
never inspected.

    python3 tools/refusal_detector.py updates.jsonl
    python3 tools/refusal_detector.py --json updates.jsonl

Input is one JSON object per line, in the envelope shape an adapter publishes:

    {"kind": "transaction", "offset": 762, "update_id": "...",
     "events": [{"type": "created", "template_id": "<pkg>:Refusal:RefusalRecord",
                 "witness_parties": [...], "payload_hash": "..."}]}

Stdlib only, per CLAUDE.md. No adapter, no broker and no ledger is contacted.
"""
import json
import sys

# The published package. `daml build` prints this id, and it is the prefix of
# every template_id the package produces:
#   ghcr.io/dominicrume/canton-refusal-record:1.0.0
REFUSAL_PACKAGE = "90b2d50c8171bc89e5194c1bd4a12a6d5a1d0100ba58ac463b7c4802dce3a5d2"

# Matched on the module and entity, not the package id, so a consumer still
# counts refusals after the package is upgraded and the id changes. Canton's
# upgrade rules keep the qualified name stable across versions; the hash does
# not survive one.
REFUSAL_ENTITY = "Refusal:RefusalRecord"
JOURNAL_ENTITY = "Journal:AttemptJournal"


def qualified_name(template_id):
    """The `Module:Entity` half of `<package>:Module:Entity`.

    Returns "" for a malformed id rather than raising. A monitor that dies on
    one bad record stops counting, and a counter that stops is worse than a
    counter that skips: the gap looks like an absence of refusals.
    """
    parts = (template_id or "").split(":")
    return ":".join(parts[-2:]) if len(parts) >= 3 else ""


def events_of(record):
    """Every event in one update, for any envelope that carries a list."""
    events = record.get("events")
    return events if isinstance(events, list) else []


def count_event(event, seen):
    """Add one event to the tally, if the package owns its template.

    An ATTEMPT is any event on the journal or a refusal record. A REFUSAL is a
    CREATED refusal record: archiving one is not a second refusal, and a
    mutation that dropped that condition left the suite green until
    tests/refusal_detector_smoke.py grew a case for it.
    """
    name = qualified_name(event.get("template_id"))
    if name not in (REFUSAL_ENTITY, JOURNAL_ENTITY):
        return
    refused = name == REFUSAL_ENTITY and event.get("type") == "created"
    seen["attempts"] += 1
    seen["refusals"] += 1 if refused else 0
    for party in event.get("witness_parties") or []:
        row = seen["parties"].setdefault(party, {"attempts": 0, "refusals": 0})
        row["attempts"] += 1
        row["refusals"] += 1 if refused else 0


def tally(records):
    """Refusals, attempts and parties, from updates alone.

    The rate is refusals over attempts, which is the number an auditor divides
    by and the one a monitor reading committed activity cannot otherwise get.
    """
    seen = {"refusals": 0, "attempts": 0, "parties": {}, "updates": 0,
            "skipped": 0}
    for record in records:
        if not isinstance(record, dict):
            seen["skipped"] += 1
            continue
        seen["updates"] += 1
        for event in events_of(record):
            count_event(event, seen)
    return seen


def rate(refusals, attempts):
    """Refusals over attempts. Zero attempts is reported as None, not as 0.0.

    A rate of zero and no data are different findings, and the second one is
    the one that needs a human. `all([])` is True for the same reason this
    returns None: measuring nothing is not a passing measurement.
    """
    return None if not attempts else round(refusals / attempts, 4)


def read_jsonl(path):
    """Each line as an object, skipping blanks and unparseable lines."""
    out = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                out.append(None)
    return out


def report(seen):
    """One screen a human reads, with the rate stated as unknown when it is."""
    ratio = rate(seen["refusals"], seen["attempts"])
    lines = ["  updates read   %d" % seen["updates"],
             "  attempts       %d" % seen["attempts"],
             "  refusals       %d" % seen["refusals"],
             "  refusal rate   %s" % ("unknown, no attempts seen"
                                      if ratio is None else ratio)]
    if seen["skipped"]:
        lines.append("  unparseable    %d" % seen["skipped"])
    for party, row in sorted(seen["parties"].items()):
        lines.append("    %-28s %d of %d" % (party[:28], row["refusals"],
                                             row["attempts"]))
    return "\n".join(lines)


def main(argv):
    if not argv:
        sys.exit(__doc__)
    paths = [a for a in argv if not a.startswith("--")]
    records = []
    for path in paths:
        records.extend(read_jsonl(path))
    seen = tally(records)
    if "--json" in argv:
        seen["rate"] = rate(seen["refusals"], seen["attempts"])
        print(json.dumps(seen, indent=2, sort_keys=True))
    else:
        print("refusals in %d file(s)" % len(paths))
        print(report(seen))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
