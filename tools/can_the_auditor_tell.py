#!/usr/bin/env python3
"""Try to hide a refusal from the auditor, on a real ledger, and measure it.

    python3 tools/can_the_auditor_tell.py

WHY THIS EXISTS, and why it is not another unit test.

On forum.canton.network topic 9114 four people have argued about whether a
refusal record is evidence or telemetry, all of them from first principles.
Federico Rodriguez (2026-09-11) said a hash chain cannot prove a receipt was
not omitted. Leonid (2026-10-30, 2026-11-09) said a refusal decided inside a
choice body reaches nobody, and that putting the proof on the ledger means
paying for a create. PREDGE (2026-10-21, 2026-11-13) said the auditor belongs
on the signatory line, and that a counter closes completeness. tonozzibeverley953
(2026-11-11) said retention control decides it.

Every one of those is a claim about what an adversary can get away with.
Nobody has run an adversary.

This does. It builds the journal, refuses things, and then plays the operator
trying to leave the auditor with a false picture. For each strategy it reports
whether the auditor can still tell, using nothing but what their own
participant holds.

THE AUDITOR HAS TWO INDEPENDENT SOURCES, which is the whole design:

  1. `Expect` on the journal, a non-consuming choice the AUDITOR controls,
     returning (attempts, refusals). The auditor is a signatory of the
     journal, so the owner cannot recreate it with a different count.
  2. The auditor's own contract store, holding every `RefusalRecord` on which
     they were named observer in advance.

A lie has to survive both. `missingRefusals` in Journal.daml compares them and
returns the positions in one and not the other, in both directions, because a
fabricated record is the other half of the same lie.

WHAT THIS MEASURES AND WHAT IT CANNOT. One participant hosts every party here,
so this measures what the ledger and the contract store say. It does NOT
measure pruning, which is the open question tonozzibeverley953 raised: a
second participant is needed to show whether the auditor's copy survives the
audited party's retention policy. That row is reported as NOT SETTLED rather
than guessed. tools/does_the_auditors_copy_survive.py goes further with two
participants started from the canton.jar in the Daml SDK, no LocalNet needed.

PREREQUISITE: none. It builds the three packages it needs, starts a real
Canton sandbox, runs, and stops it. If a ledger is already answering on port
7575 it uses that one instead and leaves it running.

Stdlib only, per THE-RULES.md.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

from canton_sandbox import REFUSAL_CHAIN, Sandbox, build_chain, have_daml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAR = os.path.join(ROOT, "step-0-refusal", "test", ".daml", "dist",
                   "canton-refusal-record-test-1.0.0.dar")

BASE = "http://localhost:7575"
PKG = "canton-refusal-record"
RUN = str(int(time.time()))
_SEQ = [0]


def call(path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:  # nosec B310
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        # A bare "HTTP 400" sent the first run of this tool looking in the
        # wrong place. The ledger says exactly what it disliked; print it.
        raise SystemExit("%s %s\n  on %s\n  sent: %s\n  ledger said: %s"
                         % (e.code, e.reason, path,
                            json.dumps(body)[:300],
                            e.read().decode()[:500]))


_PARTY = [0]


def party(hint):
    """Allocate a fresh party. Hints must be unique per ledger, and the two
    scenarios below each need their own set, so the counter is per call
    rather than per run: the second scenario collided on HTTP 400 without
    it."""
    _PARTY[0] += 1
    return call("/v2/parties", {"partyIdHint": "%s%s%d" % (
        hint, RUN, _PARTY[0])})["partyDetails"]["party"]


def submit(actors, commands):
    if isinstance(actors, str):
        actors = [actors]
    _SEQ[0] += 1
    return call("/v2/commands/submit-and-wait-for-transaction", {
        "commands": {"commands": commands, "commandId": "a-%d" % _SEQ[0],
                     "actAs": actors, "userId": "sandbox"}})


def tid(module, template):
    return "#%s:%s:%s" % (PKG, module, template)


def created(tx, module, template):
    """The contract id of the created contract of this module and template.

    Matching on the template name alone was not enough: a `Refuse` creates
    both a RefusalRecord and a replacement AttemptJournal in one transaction,
    and the template id carries the package hash, so the match has to be
    on ":Module:Template".
    """
    want = ":%s:%s" % (module, template)
    for ev in tx["transaction"]["events"]:
        c = ev.get("CreatedEvent")
        if c and c["templateId"].endswith(want):
            return c["contractId"]
    return None


def journal_of(who):
    """The AttemptJournal this party's own node holds, with its numbers.

    This replaced an attempt to read `Expect`'s return value out of the
    submit reply. The default transaction shape carries no ExercisedEvent at
    all, so there was nothing to read. Going to the party's contract store is
    also the better measurement: it is what the AUDITOR holds, not what the
    operator chose to hand back.
    """
    for c in acs(who, "Journal", "AttemptJournal"):
        arg = c["createArgument"]
        return c["contractId"], arg["attempts"], arg["refusals"]
    return None, None, None


def acs(who, module, template):
    """Every contract of this module and template the party's store holds."""
    end = call("/v2/state/ledger-end")["offset"]
    body = {"activeAtOffset": end, "filter": {"filtersByParty": {who: {
        "cumulative": [{"identifierFilter": {"WildcardFilter": {
            "value": {"includeCreatedEventBlob": False}}}}]}}},
        "verbose": False}
    out = []
    for item in call("/v2/state/active-contracts", body):
        c = (item.get("contractEntry", {}).get("JsActiveContract", {})
             .get("createdEvent", {}))
        if c and c.get("templateId", "").endswith(":%s:%s" % (module, template)):
            out.append(c)
    return out


def as_ints(xs):
    """The JSON Ledger API returns a Daml Int as a STRING. Comparing those to
    Python ints made an honest run look like three missing refusals, and the
    positive control caught it. Normalise once, here, where it is visible."""
    return [int(x) for x in xs]


def missing_refusals(expected, disclosed):
    """Journal.daml's own arithmetic, here so both sides compute it the same.

    Deliberately a second implementation rather than a call into the ledger:
    if these two ever disagree, one of them is wrong and that is worth
    knowing. The Daml version is the authority.
    """
    return ([p for p in expected if p not in disclosed]
            + [p for p in disclosed if p not in expected])


def say(m):
    print(m, flush=True)


def build(owner, actor, guardian, auditor):
    """A journal with the auditor named in advance, as the design requires."""
    # All four, including the auditor. The ledger refuses otherwise, and the
    # refusal is the design: DAML_AUTHORIZATION_ERROR naming the auditor as a
    # required authorizer is the prevention property stated by Canton rather
    # than by us. An operator cannot stand up a journal the auditor has not
    # signed, which is what stops a second one appearing later.
    tx = submit([owner, actor, guardian, auditor], [{"CreateCommand": {
        "templateId": tid("Journal", "AttemptJournal"),
        "createArguments": {
            "owner": owner, "actor": actor, "guardian": guardian,
            "auditor": auditor, "attempts": 0, "refusals": []}}}])
    return created(tx, "Journal", "AttemptJournal")


def refuse(owner, actor, cid, choice, n):
    """One refusal, by whichever mechanism. Returns the new journal cid."""
    tx = submit([owner, actor], [{"ExerciseCommand": {
        "templateId": tid("Journal", "AttemptJournal"),
        "contractId": cid, "choice": choice,
        "choiceArgument": {"action": "withdraw",
                           "detail": "attempt %d" % n,
                           "rule": "charge would exceed the cap"}}}])
    return created(tx, "Journal", "AttemptJournal")


def expect(auditor, cid):
    """What the LEDGER says, read by the auditor, who controls this choice."""
    submit(auditor, [{"ExerciseCommand": {
        "templateId": tid("Journal", "AttemptJournal"),
        "contractId": cid, "choice": "Expect", "choiceArgument": {}}}])
    return True


def archive(owner, actor, cid):
    """Owner and actor together archive a refusal record.

    A single operator cannot: RefusalRecord is `signatory owner, actor`, so
    one party acting alone gets DAML_AUTHORIZATION_ERROR. This is therefore
    the COLLUSION case, which is the strongest attack available inside the
    model, and it is the one worth measuring.
    """
    submit([owner, actor], [{"ExerciseCommand": {
        "templateId": tid("Refusal", "RefusalRecord"),
        "contractId": cid, "choice": "Archive", "choiceArgument": {}}}])


def fabricate(owner, actor, auditor, n):
    """Owner and actor together create a refusal that never happened.

    The other half of the same lie: if an auditor only checked that every
    record they hold is real, a padded set would pass. missingRefusals
    compares in both directions for exactly this reason.
    """
    submit([owner, actor], [{"CreateCommand": {
        "templateId": tid("Refusal", "RefusalRecord"),
        "createArguments": {
            "owner": owner, "actor": actor, "action": "withdraw",
            "detail": "invented %d" % n, "rule": "charge would exceed the cap",
            "refusedAt": "2026-11-13T00:00:00Z", "auditor": auditor}}}])


def scenario(label, choice, how_many, attack=None):
    """Run one mechanism end to end and report what the auditor can tell."""
    owner = party("Owner")
    actor = party("Actor")
    guardian = party("Guardian")
    auditor = party("Auditor")

    cid = build(owner, actor, guardian, auditor)
    for i in range(1, how_many + 1):
        cid = refuse(owner, actor, cid, choice, i)

    note = ""
    if attack == "archive":
        held_now = acs(auditor, "Refusal", "RefusalRecord")
        archive(owner, actor, held_now[0]["contractId"])
        note = "owner and actor colluded to archive one disclosed record"
    elif attack == "fabricate":
        fabricate(owner, actor, auditor, how_many + 1)
        note = "owner and actor colluded to invent a refusal that never was"

    # The auditor exercises Expect themselves. It returns nothing readable
    # through this API, but a successful submit proves the auditor controls
    # it: the operator cannot stop them asking.
    asked = expect(auditor, cid)
    _, attempts, refusals = journal_of(auditor)
    held = acs(auditor, "Refusal", "RefusalRecord")
    disclosed = list(range(1, len(held) + 1))
    gaps = missing_refusals(as_ints(refusals), disclosed)

    say("")
    say("  %s" % label)
    if note:
        say("    attack                             : %s" % note)
    say("    auditor could exercise Expect      : %s" % ("yes" if asked else "no"))
    say("    ledger says refused at positions   : %s" % refusals)
    say("    records the auditor's node holds   : %d" % len(held))
    say("    positions with nothing behind them : %s"
        % (gaps if gaps else "none"))
    return attempts, refusals, len(held), gaps


def control_passes():
    """An honest run must leave no gap. Separate from main() because a gate
    and the thing it gates are different jobs, and because this is the only
    part whose failure stops everything else being printed."""
    _, refusals, held, gaps = scenario(
        "CONTROL: Refuse, everything recorded honestly", "Refuse", 3)
    if gaps:
        say("")
        say("  CONTROL FAILED: an honest run already shows gaps %s." % gaps)
        say("  Nothing below would mean anything. Refusing to report it.")
        return False
    if held != len(refusals):
        say("")
        say("  CONTROL FAILED: %d records for %d refusals."
            % (held, len(refusals)))
        return False
    say("    CONTROL PASSES: honest disclosure leaves no gap.")
    return True


def ledger_running():
    """Is a JSON Ledger API already answering on the expected port?"""
    try:
        call("/v2/version")
        return True
    except Exception:
        return False


def main():
    """Use a ledger that is already running, otherwise build one and start it.

    The first version of this tool only did the first half. It printed
    "Start one, then re-run" with a daml sandbox command that needed a DAR
    built by hand, and a forum reply on topic 9114 told a reader to run it as
    a single command. It worked on the author's machine because the author's
    machine already held the DARs. From a clean clone it failed on the first
    line, which was found by running it from a clean clone, not by reading it.
    """
    if ledger_running():
        return play()
    if not have_daml() or not build_chain(REFUSAL_CHAIN):
        return 1
    if not os.path.exists(DAR):
        say("the build reported success but %s is missing" % DAR)
        return 1
    box = Sandbox(DAR, extra=["--json-api-port", BASE.rsplit(":", 1)[1]])
    try:
        return play() if box.start() else 1
    finally:
        box.stop()


def play():
    say("Playing the operator against the auditor, on a real Canton ledger.")

    if not control_passes():
        return 1

    # Attack 1: collusion to destroy a record that was properly disclosed.
    _, r3, h3, g3 = scenario(
        "ATTACK 1: archive a record (owner and actor colluding)",
        "Refuse", 3, attack="archive")
    say("    detected                           : %s"
        % ("YES" if g3 else "no, the lie survived"))

    # Attack 2: collusion to pad the set with a refusal that never happened.
    _, r4, h4, g4 = scenario(
        "ATTACK 2: invent a refusal (owner and actor colluding)",
        "Refuse", 3, attack="fabricate")
    say("    detected                           : %s"
        % ("YES" if g4 else "no, the lie survived"))

    # Attack 3: the cheap mechanism, which creates nothing to destroy.
    a2, r2, h2, g2 = scenario(
        "ATTACK 3: RefuseSignalled, no record created at all",
        "RefuseSignalled", 3)

    say("")
    say("=" * 66)
    if g2 and h2 == 0:
        say("THE AUDITOR CAN STILL TELL.")
        say("")
        say("Nothing was created, so the auditor's node holds no record and")
        say("has no reason for any refusal. But the count is on a contract")
        say("the auditor SIGNS, so the operator cannot move it alone. The")
        say("ledger says %s were refused and the auditor holds %d records,"
            % (r2, h2))
        say("so every position is a declared hole.")
        say("")
        say("That is the measured difference between the two mechanisms, and")
        say("it is narrower than either side of the forum argument assumed:")
        say("  the cheap path still proves THAT something was refused;")
        say("  it stops proving WHAT, and it cannot be silently reduced.")
    elif not g2:
        say("THE CHEAP PATH LEAVES NO DETECTABLE HOLE, which contradicts")
        say("Journal.daml's own comment. Report this as measured and work")
        say("out which is wrong before quoting either.")
    else:
        say("MIXED: gaps %s with %d records held. Read the run above before"
            % (g2, h2))
        say("drawing anything from it.")
    say("=" * 66)

    say("")
    say("NOT SETTLED, and it is the open question on the thread.")
    say("Pruning. One participant hosts every party here, so this tool says")
    say("nothing about whether the auditor's copy survives the audited")
    say("party's retention policy. tonozzibeverley953 asked that on")
    say("2026-11-11.")
    say("")
    say("tools/does_the_auditors_copy_survive.py takes it further, with two")
    say("participants started from the canton.jar inside the Daml SDK. No")
    say("Docker and no LocalNet were needed, which this text used to say they")
    say("were. It shows pruning is per participant. It does not settle the")
    say("question, because Canton refused to prune as far as the event inside")
    say("a 168h window, so the event itself was never pruned.")
    say("")
    say("Canton's pruning reference says pruning never removes an active")
    say("contract, so the COUNT should survive a prune. Whether the REASONS do")
    say("is the part nobody has shown.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
