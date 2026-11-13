#!/usr/bin/env python3
"""Who actually receives a non-consuming exercise: a measurement, not an argument.

    python3 tools/who_witnesses_a_nonconsuming_exercise.py

WHAT IS BEING TESTED. On forum.canton.network topic 9114, post 16, on
2026-11-13, PREDGE answered tonozzibeverley953's pruning question of
2026-11-11 with a precise claim:

    "A non-consuming exercise goes to signatories, actors and choice
    observers, not to plain contract observers. If the auditor is a choice
    observer on the refusal choice, every refusal event lands on the
    auditor's participant, and the audited party's pruning can't touch that
    copy."

That matters to this repository because `step-0-refusal/daml/Journal.daml`
solves the same problem the expensive way: it puts the auditor on the
SIGNATORY line, which needs the auditor's authority at creation time. If
PREDGE is right, a choice observer gets the same delivery for free.

WHY DAML SCRIPT CANNOT ANSWER IT, which was tried first and is recorded in
`step-0-refusal/test/daml/ChoiceObserverTest.daml`. Daml Script has no
primitive for reading an event stream or asking who was an informee. The
closest proxy is whether a party can later read a contract created by the
exercise. Run against this ledger, NEITHER the choice observer NOR the plain
observer could read it, so the proxy answers nothing and the script aborts
saying so rather than reporting a pass.

So this tool asks the ledger directly. It reads the update stream through the
JSON Ledger API once as each party and reports which of them was sent the
exercise event. That is the question, asked of the only thing that knows.

HOW TO READ THE RESULT. The claim is confirmed only if the choice observer
receives the exercise and the plain contract observer does not. Any other
combination is reported as what it is. A tool that can only print
"confirmed" cannot tell you whether it ran, so the signatory case is measured
alongside as a positive control: a signatory MUST witness an exercise on its
own contract, and if that comes back negative this tool refuses to report the
interesting result at all.

PREREQUISITE. A sandbox with the test DAR and the JSON API, started by hand
because this tool deliberately does not manage a ledger it is measuring:

    daml sandbox --dar step-0-refusal/test/.daml/dist/canton-refusal-record-test-1.0.0.dar \\
      --json-api-port 7575

Stdlib only, per THE-RULES.md.
"""
import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://localhost:7575"
PKG = "canton-refusal-record-test"
MOD = "ChoiceObserverTest"


def call(path, body=None):
    """POST json, or GET when body is None. Returns the decoded reply."""
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path, data=data,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:  # nosec B310
        return json.loads(r.read().decode())


# Party hints must be unique per ledger. The first run of this tool failed on
# its second invocation with HTTP 400, because "Owner" already existed.
RUN = str(int(time.time()))


def party(hint):
    return call("/v2/parties",
                {"partyIdHint": hint + RUN})["partyDetails"]["party"]


_SEQ = [0]


def submit(actors, commands):
    """actors may be one party or several, because a two-signatory create
    needs both on actAs. The first version passed a single party and the
    co-signed control failed with a missing-authority error."""
    if isinstance(actors, str):
        actors = [actors]
    _SEQ[0] += 1
    return call("/v2/commands/submit-and-wait-for-transaction", {
        "commands": {
            "commands": commands,
            "commandId": "m-%d" % _SEQ[0],
            "actAs": actors,
            "userId": "sandbox",
        }})


def create(actor, template, payload):
    return submit(actor, [{"CreateCommand": {
        "templateId": "#%s:%s:%s" % (PKG, MOD, template),
        "createArguments": payload}}])


def exercise(actor, template, cid, choice, payload):
    return submit(actor, [{"ExerciseCommand": {
        "templateId": "#%s:%s:%s" % (PKG, MOD, template),
        "contractId": cid,
        "choice": choice,
        "choiceArgument": payload}}])


def contract_id(tx):
    """The contract id of the single create in a transaction reply."""
    for ev in tx["transaction"]["events"]:
        if "CreatedEvent" in ev:
            return ev["CreatedEvent"]["contractId"]
    raise SystemExit("no CreatedEvent in the reply; the API shape changed")


def ledger_end():
    return call("/v2/state/ledger-end")["offset"]


def saw_exercise(who, start, end, choice):
    """Did this party's stream carry an ExercisedEvent for this choice?

    Read as the party, which is the whole point: the Ledger API serves each
    party only what its participant received.

    The first version of this matched on the text '"choice":"X"'. json.dumps
    writes '"choice": "X"' with a space, so it matched nothing and the
    positive control came back negative. The control did its job and the tool
    refused to report. It walks the structure now rather than the text.
    """
    body = {
        "beginExclusive": start,
        "endInclusive": end,
        "updateFormat": {"includeTransactions": {
            "eventFormat": {
                "filtersByParty": {who: {"cumulative": [
                    {"identifierFilter": {"WildcardFilter": {
                        "value": {"includeCreatedEventBlob": False}}}}]}},
                "verbose": False},
            "transactionShape": "TRANSACTION_SHAPE_LEDGER_EFFECTS"}}}
    try:
        updates = call("/v2/updates", body)
    except urllib.error.HTTPError as e:
        raise SystemExit("the updates endpoint refused the read: %s" % e)
    for item in updates:
        tx = item.get("update", {}).get("Transaction", {}).get("value", {})
        for ev in tx.get("events", []):
            ex = ev.get("ExercisedEvent")
            if ex and ex.get("choice") == choice:
                return True
    return False


def verdict(by_choice_observer, by_plain_observer):
    """Every outcome the measurement can produce, each said in full.

    These branches are the output of this tool, so they live together where a
    reader can check that no case is missing. That is also why they are not
    inside main(): the measurement and the reporting of it are different jobs.
    """
    if by_choice_observer and not by_plain_observer:
        say("PREDGE's claim HOLDS on this ledger. A choice observer is sent")
        say("the exercise; a plain contract observer is not. So an auditor")
        say("named on the choice gets the event on its own participant, and")
        say("the audited party cannot prune that copy, without needing the")
        say("auditor's authority at creation time.")
    elif by_choice_observer and by_plain_observer:
        say("PARTLY. Both received it, so a plain contract observer DOES see")
        say("a non-consuming exercise here. The delivery claim holds; the")
        say("exclusion half of the claim does not.")
    elif not by_choice_observer:
        say("PREDGE's claim DOES NOT HOLD as stated on this ledger: the")
        say("choice observer did not receive the exercise. Report this as")
        say("measured, and say which SDK and which ledger.")


def main():
    try:
        call("/v2/version")
    except Exception:
        say("No JSON Ledger API on %s." % BASE)
        say("Start one first, then re-run:")
        say("  daml sandbox --dar step-0-refusal/test/.daml/dist/"
            "canton-refusal-record-test-1.0.0.dar --json-api-port 7575")
        return 1

    owner = party("Owner")
    auditor = party("Auditor")
    bystander = party("Bystander")
    say("parties allocated on the ledger")

    # ---- the positive control, measured FIRST --------------------------
    # A signatory must witness a non-consuming exercise on its own contract.
    # If this is negative the tool has not measured what it thinks it has,
    # and Journal.daml's central argument would be in trouble too.
    before = ledger_end()
    co = contract_id(create([owner, auditor], "CoSignedSource", {
        "owner": owner, "auditor": auditor, "bystander": bystander}))
    exercise(owner, "CoSignedSource", co, "CoSignedSignal",
             {"reason": "control"})
    after = ledger_end()
    control = saw_exercise(auditor, before, after, "CoSignedSignal")
    say("control: does a SIGNATORY witness a non-consuming exercise? %s"
        % ("yes" if control else "NO"))
    if not control:
        say("  The control failed, so nothing below would mean anything.")
        say("  Refusing to report the real result.")
        return 1

    # ---- the question --------------------------------------------------
    before = ledger_end()
    src = contract_id(create(owner, "SignalSource", {
        "owner": owner, "auditor": auditor, "bystander": bystander}))
    exercise(owner, "SignalSource", src, "Signal", {"reason": "cap exceeded"})
    after = ledger_end()

    by_choice_observer = saw_exercise(auditor, before, after, "Signal")
    by_plain_observer = saw_exercise(bystander, before, after, "Signal")

    say("")
    say("choice observer received the exercise : %s"
        % ("YES" if by_choice_observer else "no"))
    say("plain contract observer received it   : %s"
        % ("YES" if by_plain_observer else "no"))
    say("")

    verdict(by_choice_observer, by_plain_observer)

    say("")
    say("LIMIT, and it travels with the result: single-participant local")
    say("Canton sandbox, SDK 3.4.11. One participant hosts every party here,")
    say("so this shows what the Ledger API SERVES each party, which is the")
    say("informee question. It does not show cross-participant delivery on a")
    say("shared network, and pruning was not exercised at all.")
    return 0


def say(m):
    print(m, flush=True)


if __name__ == "__main__":
    sys.exit(main())
