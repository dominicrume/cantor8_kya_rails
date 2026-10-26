#!/usr/bin/env python3
"""The refusal detector counts what a monitor cannot otherwise see.

Written for a consumer of a Canton ingestion adapter: given the records such
an adapter publishes, the detector must report the refusal count, the attempt
count and the rate, and must do it with contract payloads HASHED, because that
is the default an adapter ships with.

Every check below is an assertion that can fail. The last block is the control:
it breaks the detector on purpose and requires a named check to go red, because
a suite that cannot fail is not a suite. See docs/findings for why that
sentence is in this repository twice.
"""
import json
import os
import subprocess  # nosec B404 - fixed argv, no shell
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import refusal_detector as rd  # noqa: E402

PKG = rd.REFUSAL_PACKAGE
OWNER = "owner::1220aa"
ACTOR = "actor::1220bb"

FAILED = []


def check(ok, why):
    print("  %s %s" % ("PASS" if ok else "FAIL", why))
    if not ok:
        FAILED.append(why)


def event(entity, kind="created", parties=(OWNER, ACTOR)):
    """One event in the shape an adapter publishes, payload HASHED.

    There is deliberately no payload key. If the detector ever needs one, this
    fixture stops compiling the behaviour it is meant to prove.
    """
    return {"type": kind, "offset": 762, "node_id": 0,
            "contract_id": "00ea30ef", "template_id": "%s:%s" % (PKG, entity),
            "package_name": "canton-refusal-record",
            "witness_parties": list(parties),
            "payload_hash": "44136fa355b3678a1146ad16f7e8649e"}


def update(events, kind="transaction", offset=762):
    return {"kind": kind, "offset": offset, "update_id": "1220%d" % offset,
            "synchronizer_id": "sync1::1220", "record_time": 1788994186204,
            "events": events, "synchronizer_times": {}}


print("the qualified name survives a package upgrade")
check(rd.qualified_name("%s:Refusal:RefusalRecord" % PKG)
      == "Refusal:RefusalRecord",
      "a full template id reduces to Module:Entity")
check(rd.qualified_name("adifferentpackageid:Refusal:RefusalRecord")
      == "Refusal:RefusalRecord",
      "  and the same name is produced after an upgrade changes the hash")
check(rd.qualified_name("rubbish") == "",
      "a malformed id is empty rather than an exception")
check(rd.qualified_name(None) == "",
      "  and so is a missing one, so one bad record cannot stop the count")

print()
print("refusals and attempts are counted from updates alone")
seen = rd.tally([
    update([event("Journal:AttemptJournal")], offset=1),
    update([event("Refusal:RefusalRecord")], offset=2),
    update([event("Journal:AttemptJournal")], offset=3),
    update([event("Refusal:RefusalRecord")], offset=4),
])
check(seen["attempts"] == 4, "four events on the journal or a record are four attempts")
check(seen["refusals"] == 2, "  two of which are refusals")
check(rd.rate(seen["refusals"], seen["attempts"]) == 0.5, "  a rate of 0.5")

print()
print("archiving a refusal record does not invent a second refusal")
# Found by mutation: deleting the `type == "created"` condition left the suite
# green, because nothing here had ever exercised a refusal record. An auditor
# counting refusals would have double-counted every archived one.
seen = rd.tally([
    update([event("Refusal:RefusalRecord", kind="created")], offset=1),
    update([event("Refusal:RefusalRecord", kind="exercised")], offset=2),
])
check(seen["refusals"] == 1, "a created then exercised record is one refusal")
check(seen["attempts"] == 2, "  while both events still count as attempts")

print()
print("a template the package does not own is not counted")
seen = rd.tally([update([{"type": "created",
                          "template_id": "abc:Iou:Iou",
                          "witness_parties": [OWNER]}])])
check(seen["attempts"] == 0, "an unrelated template contributes nothing")
check(rd.rate(seen["refusals"], seen["attempts"]) is None,
      "  and the rate is unknown rather than zero")

print()
print("no attempts is reported as unknown, not as a clean zero")
check(rd.rate(0, 0) is None, "zero over zero is None")
check(rd.rate(0, 5) == 0.0, "  but zero refusals in five attempts really is 0.0")

print()
print("it works with payloads hashed, which is the adapter default")
ev = event("Refusal:RefusalRecord")
check("payload" not in ev, "the fixture carries no payload at all")
seen = rd.tally([update([ev])])
check(seen["refusals"] == 1,
      "  and the refusal is still counted from template_id alone")

print()
print("per-party counts come from the witness list")
seen = rd.tally([
    update([event("Refusal:RefusalRecord", parties=(OWNER,))], offset=1),
    update([event("Journal:AttemptJournal", parties=(OWNER, ACTOR))], offset=2),
])
check(seen["parties"][OWNER] == {"attempts": 2, "refusals": 1},
      "the owner saw two attempts and one refusal")
check(seen["parties"][ACTOR] == {"attempts": 1, "refusals": 0},
      "  and the actor saw one attempt and no refusal")

print()
print("a malformed record is skipped and reported, never fatal")
seen = rd.tally([None, "not a dict", update([event("Refusal:RefusalRecord")])])
check(seen["skipped"] == 2, "two unusable records are counted as skipped")
check(seen["refusals"] == 1, "  and the good one is still counted")

print()
print("it reads the wire format off disk")
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "updates.jsonl")
    with open(p, "w", encoding="utf-8") as f:
        f.write(json.dumps(update([event("Journal:AttemptJournal")], offset=1)) + "\n")
        f.write("\n")
        f.write("{ this is not json\n")
        f.write(json.dumps(update([event("Refusal:RefusalRecord")], offset=2)) + "\n")
    out = subprocess.run(  # nosec B603 B607 - literal argv
        [sys.executable, os.path.join(ROOT, "tools", "refusal_detector.py"),
         "--json", p], capture_output=True, text=True)
    check(out.returncode == 0, "the command exits zero on a file with a bad line")
    got = json.loads(out.stdout)
    check(got["refusals"] == 1 and got["attempts"] == 2,
          "  and reports one refusal in two attempts")
    check(got["rate"] == 0.5, "  with the rate in the JSON output")
    check(got["skipped"] == 1, "  and names the unparseable line rather than hiding it")

print()
print("the control: break the detector and a named check above must go red")
original = rd.REFUSAL_ENTITY
try:
    rd.REFUSAL_ENTITY = "Refusal:SomethingElse"
    broken = rd.tally([update([event("Refusal:RefusalRecord")])])
    check(broken["refusals"] == 0,
          "pointing the detector at the wrong entity stops it counting")
finally:
    rd.REFUSAL_ENTITY = original
healed = rd.tally([update([event("Refusal:RefusalRecord")])])
check(healed["refusals"] == 1, "  and restoring it starts again, so the check is live")

print()
if FAILED:
    print("FAILED: %d" % len(FAILED))
    for f in FAILED:
        print("  - %s" % f)
    sys.exit(1)
print("a monitor reading committed updates can count what was refused,")
print("without ever reading what it was.")
