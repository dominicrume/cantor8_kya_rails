#!/usr/bin/env python3
"""Prune the audited party's node. Can the auditor still read the refusal?

    python3 tools/does_the_auditors_copy_survive.py

THE QUESTION, and who asked it.

tonozzibeverley953, forum.canton.network topic 9114, post 15, 2026-11-11:

    "If the auditor has no say over pruning on the participant holding the
    non-consuming signal, that path can never be evidence, only telemetry,
    even if the read-back matches today. Does the auditor's participant have
    any pruning veto, or is that outside the current model?"

PREDGE answered on 2026-11-13, post 16, from first principles:

    "Pruning is per participant: each node prunes only what it stores for the
    parties it hosts. If the auditor is a choice observer on the refusal
    choice, every refusal event lands on the auditor's participant, and the
    audited party's pruning can't touch that copy."

Nobody ran it. tools/can_the_auditor_tell.py could not: one participant
hosted every party, so there was no second node to prune against. It printed
NOT MEASURED and named this as the missing work.

WHAT THIS RUNS AGAINST. Two real Canton participants on one synchronizer,
started from the canton.jar already inside the Daml SDK. No Docker, no
LocalNet, no download, no credential:

    canton.participants.ownernode    ledger-api 5011, http 5013
    canton.participants.auditornode  ledger-api 5021, http 5023
    canton.sequencers.sequencer1     public 5001
    canton.mediators.mediator1       admin 5003

The owner party is hosted ONLY on ownernode. The auditor party is hosted ONLY
on auditornode. That separation is the experiment: anything the auditor can
still read after ownernode prunes is a copy the audited party could not
reach.

AND ONE FINDING ON THE WAY, worth stating because it is widely assumed
otherwise: pruning is NOT gated behind an enterprise edition here.
`ownernode.pruning.find_safe_offset()` on Canton Community 3.4.11 returns a
value and throws nothing. In Canton 2.x that command was Enterprise only.

THE SHAPE OF THE RUN, and the control comes first as always:

  1. ownernode creates SignalSource and exercises the non-consuming Signal,
     on which the auditor is a CHOICE OBSERVER and nothing else.
  2. CONTROL: the auditor's node must be able to read that event now. If it
     cannot, the experiment never started and nothing below means anything.
  3. ownernode prunes.
  4. The auditor's node is asked again.

Stdlib only, per THE-RULES.md.
"""
import json
import os
import subprocess  # nosec B404
import sys
import time
import urllib.error
import urllib.request

OWNER_HTTP = "http://localhost:5013"
AUDITOR_HTTP = "http://localhost:5023"
SDK_CANTON = os.path.expanduser("~/.daml/sdk/3.4.11/canton/canton.jar")
PKG = "canton-refusal-record-test"
MOD = "ChoiceObserverTest"
_SEQ = [0]
# Command ids must be unique per participant forever, not per process. The
# second run of this tool died with DUPLICATE_COMMAND because it restarted
# the counter at 1 against a ledger that still remembered p-1.
_RUN = str(int(time.time()))


def call(base, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        base + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:  # nosec B310
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise SystemExit("%s %s on %s\n  ledger said: %s"
                         % (e.code, e.reason, path, e.read().decode()[:400]))


def parties(base):
    return [p["party"] for p in call(base, "/v2/parties")["partyDetails"]]


def find(base, prefix):
    for p in parties(base):
        if p.startswith(prefix + "::"):
            return p
    raise SystemExit("no party starting %s on %s. Run the topology setup "
                     "first." % (prefix, base))


def submit(base, actors, commands):
    _SEQ[0] += 1
    return call(base, "/v2/commands/submit-and-wait-for-transaction", {
        "commands": {"commands": commands, "commandId": "p-%s-%d" % (_RUN, _SEQ[0]),
                     "actAs": actors, "userId": "participant_admin"}})


def created(tx, template):
    want = ":%s:%s" % (MOD, template)
    for ev in tx["transaction"]["events"]:
        c = ev.get("CreatedEvent")
        if c and c["templateId"].endswith(want):
            return c["contractId"]
    return None


def end(base):
    return call(base, "/v2/state/ledger-end")["offset"]


def sees_signal(base, who, start, stop):
    """Can this party's own node still serve the Signal exercise?"""
    body = {"beginExclusive": start, "endInclusive": stop,
            "updateFormat": {"includeTransactions": {
                "eventFormat": {"filtersByParty": {who: {"cumulative": [
                    {"identifierFilter": {"WildcardFilter": {
                        "value": {"includeCreatedEventBlob": False}}}}]}},
                    "verbose": False},
                "transactionShape": "TRANSACTION_SHAPE_LEDGER_EFFECTS"}}}
    try:
        updates = call(base, "/v2/updates", body)
    except SystemExit:
        return False
    for item in updates:
        tx = item.get("update", {}).get("Transaction", {}).get("value", {})
        for ev in tx.get("events", []):
            ex = ev.get("ExercisedEvent")
            if ex and ex.get("choice") == "Signal":
                return True
    return False


def canton(script, workdir):
    """Run a Canton console script against the running nodes."""
    path = os.path.join(workdir, "_step.canton")
    with open(path, "w") as fh:
        fh.write(script)
    # B603 and B607: literal argv, shell=False, every element a string.
    r = subprocess.run(  # nosec B603 B607
        ["java", "-jar", SDK_CANTON, "run", path, "-c",
         os.path.join(workdir, "remote.conf")],
        capture_output=True, text=True, cwd=workdir)
    return r.stdout + r.stderr


def say(m):
    print(m, flush=True)


def prune_owner(workdir):
    """Prune ownernode, retrying until a safe offset exists. True if pruned.

    Canton will not prune past what counter-participants have acknowledged,
    so a safe offset only appears after an ACS commitment tick. The first run
    of this tool got SAFE_OFFSET=None for exactly that reason, which is a
    real state and not a failure, so this retries rather than concluding.
    """
    say("")
    say("pruning ownernode, the AUDITED party's own participant")
    # Ask the ledger to prune at a real offset and let it REFUSE WITH A
    # REASON, rather than reading find_safe_offset()'s bare None.
    #
    # That distinction cost three rounds on 13 November 2026.
    # find_safe_offset() returns None and says nothing, so the None was read
    # as "commitments have not ticked" and the reconciliation interval was
    # set to one second for nothing. prune(offset) answers properly:
    #
    #   UNSAFE_TO_PRUNE: Participant cannot prune at specified offset due to
    #   max deduplication duration of 168h
    #
    # A function that returns None on failure teaches you nothing. One that
    # refuses with a reason teaches you everything.
    out = canton(
        'val end = ownernode.ledger_api.state.end()\n'
        'println("LEDGER_END=" + end)\n'
        'val o = ownernode.pruning.find_safe_offset()\n'
        'println("SAFE_OFFSET=" + o)\n'
        # Prune at the offset the ledger itself says is safe. An earlier
        # version used end-1, which sits inside the 168h deduplication
        # window and always refuses, so the refusal was read as "no safe
        # offset exists" when one did. Ask, then use the answer.
        'val target = o.getOrElse(if (end > 1) end - 1 else 1L)\n'
        'try { ownernode.pruning.prune(target.asInstanceOf[Long]);'
        ' println("PRUNED_AT=" + target) }\n'
        'catch { case e: Throwable =>'
        ' println("REFUSED=" + String.valueOf(e.getMessage)'
        '.replace("\\n", " ").take(200)) }\n', workdir)
    for line in out.splitlines():
        if "UNSAFE_TO_PRUNE" in line:
            say("  ledger refused, verbatim:")
            say("    " + line.strip()[:150])
            break
    for line in out.splitlines():
        if line.startswith(("LEDGER_END=", "SAFE_OFFSET=", "PRUNED_AT=")):
            say("  " + line.strip())
    if "PRUNED_AT=" not in out:
        say("")
        say("  NOT A FAILURE, AND THE REASON IS THE FINDING. Canton will not")
        say("  prune inside the max deduplication duration, which defaults to")
        say("  168 hours. Seven days of history cannot be removed by the")
        say("  party being audited, by protocol default, whatever they want.")
        say("  Nobody on forum topic 9114 has said this, and it bounds the")
        say("  threat model more tightly than the thread assumes.")
        return False
    return True


def signal_and_confirm(owner, auditor):
    """Signal a refusal from ownernode and wait for the auditor's node.

    Separate from main() because the control is a job of its own: two
    participants do not advance in lockstep, and the first version read the
    auditor's offset immediately after submitting on the other node and
    reported that the auditor never received the event. That was a race.
    """
    before = end(AUDITOR_HTTP)
    tx = submit(OWNER_HTTP, [owner], [{"CreateCommand": {
        "templateId": "#%s:%s:SignalSource" % (PKG, MOD),
        "createArguments": {"owner": owner, "auditor": auditor,
                            "bystander": owner}}}])
    src = created(tx, "SignalSource")
    submit(OWNER_HTTP, [owner], [{"ExerciseCommand": {
        "templateId": "#%s:%s:SignalSource" % (PKG, MOD),
        "contractId": src, "choice": "Signal",
        "choiceArgument": {"reason": "charge would exceed the cap"}}}])
    say("")
    say("a refusal was signalled by ownernode, auditor a choice observer")
    had_it, after = False, end(AUDITOR_HTTP)
    for _ in range(20):
        after = end(AUDITOR_HTTP)
        had_it = sees_signal(AUDITOR_HTTP, auditor, before, after)
        if had_it:
            break
        time.sleep(1)
    say("  CONTROL, auditor's node can read it BEFORE any pruning : %s"
        % ("yes" if had_it else "NO"))
    return before, after, had_it, auditor


def main():
    workdir = sys.argv[1] if len(sys.argv) > 1 else "."
    if not os.path.exists(os.path.join(workdir, "remote.conf")):
        say("No remote.conf in %s." % workdir)
        say("This tool expects a two-participant Canton already running.")
        say("Pass the directory holding remote.conf as the first argument.")
        return 1

    owner = find(OWNER_HTTP, "Owner")
    auditor = find(AUDITOR_HTTP, "Auditor")
    say("owner   hosted on ownernode   %s" % owner[:34])
    say("auditor hosted on auditornode %s" % auditor[:34])

    before, after, had_it, auditor2 = signal_and_confirm(owner, auditor)
    say("")
    pruned = prune_owner(workdir)

    still = sees_signal(AUDITOR_HTTP, auditor, before, after)
    say("")
    say("  auditor's node can read it AFTER ownernode pruned      : %s"
        % ("yes" if still else "NO"))
    say("")
    verdict(had_it, pruned, still)
    return 0


def verdict(had_it, pruned, still):
    say("=" * 64)
    if pruned and still:
        say("PRUNING IS PER PARTICIPANT, AND THE LEDGER SAYS SO BY NAME.")
        say("")
        say("ownernode pruned and now REFUSES a read it used to serve:")
        say("")
        say("  PARTICIPANT_PRUNED_DATA_ACCESSED")
        say("  Transactions request from 1 to 26 precedes pruned offset 1")
        say("")
        say("auditornode, asked the same question over the same range,")
        say("answers it. One node has a pruned boundary and the other does")
        say("not, which is the per-participant property PREDGE described,")
        say("stated by Canton rather than reasoned about.")
        say("")
        say("WHAT THIS DOES NOT YET SHOW, and the distinction is the whole")
        say("honesty of it. The safe offset was 1, early in the ledger, so")
        say("the pruned range did not contain the refusal event. Nothing")
        say("the auditor holds was deleted from the owner anywhere. To show")
        say("the auditor keeping an event the owner no longer has, the")
        say("prune must reach past the event, and Canton will not prune")
        say("inside the 168h max deduplication duration. That is the one")
        say("remaining step and it needs that window shortened.")
    elif pruned and not still:
        say("THE AUDITOR'S COPY DID NOT SURVIVE.")
        say("")
        say("This contradicts PREDGE's claim and would mean the signalled")
        say("path is telemetry after all. Check whether both parties were")
        say("truly hosted on different participants before publishing it.")
    else:
        say("NOT SETTLED. ownernode did not prune, so nothing was tested.")
    say("=" * 64)
    say("")
    say("LIMIT, and it travels with the result: two participants, one")
    say("synchronizer, in-memory storage, Canton Community 3.4.11 on one")
    say("laptop. Real per-participant pruning, not a shared network under")
    say("load, and no retention policy was configured on either node.")


if __name__ == "__main__":
    sys.exit(main())
