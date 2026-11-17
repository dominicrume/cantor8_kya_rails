#!/usr/bin/env python3
"""Does the auditor receive what an attempt is made of? Measured on a real ledger.

    python3 tools/who_sees_the_attempt_arguments.py

WHY THIS EXISTS. step-0-refusal says an auditor learns that an attempt
happened and, for a refusal, what it was. For an attempt that was ALLOWED it
says the auditor learns a count and nothing else. On 14 November 2026 a review
of the Daml pointed out that this was a claim about what the code does and
nobody had looked at what the auditor's participant is actually sent.

Daml Script cannot look. It has no primitive for reading the update stream, so
every test passed while the claim was false: `Open` took a salt, an action and
a detail as choice arguments, and the auditor and the guardian, who are
signatories of the journal, are informees of that exercise and were sent all
three in plain text. `Allow` took an action and discarded it, and that was
delivered too. `SettleAttempt` took them again. A scratch version of this
tool, run on a local sandbox against the code as committed that morning
(f49ac18), found the salt, the action and the detail all present in the
auditor's and the guardian's streams. This version measures the fixed API.

WHAT IT DOES. Starts a real Canton sandbox, then for a fresh set of parties:

  CONTROL 1  `RefuseSignalled` is DOCUMENTED to deliver its action, detail and
             rule to the auditor. It is sent with marker strings and the
             auditor MUST see them. If the tool cannot see a leak that is
             meant to happen, it cannot see one that is not, and it refuses to
             report.
  CONTROL 2  the owner submitted every command, so the owner MUST see the
             markers of the control above.
  CHECK      the allowed path (`Open`, `Allow`, `SettleAttempt`) is run with
             the real commitment of a secret salt, action and detail, and the
             auditor's and the guardian's streams are searched for them.
  CONFORMANCE  the commitment is computed HERE, in Python, and the ledger then
             verifies it when the attempt is refused. If the two disagree the
             refusal is rejected and the tool says so, which proves the
             off-ledger computation is the same as `attemptCommitment`.

WHAT IT CANNOT SHOW, said before the result so it is not oversold.
  * It checks the arguments the API takes TODAY. A future choice that takes a
    new free-text argument would have to be added here to be measured.
  * One participant hosts every party, so this is what the ledger delivers to
    each PARTY, not a statement about separate participants' storage.
  * The guardian is a signatory of every attempt and sees what the owner does
    through it. That is the guardian's job, and it is reported, not hidden.

Stdlib only, per THE-RULES.md.
"""
import hashlib
import json
import os
import sys

from canton_sandbox import (REFUSAL_CHAIN, Sandbox, build_chain, have_daml,
                            when_packages_ready)
import can_the_auditor_tell as T

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WALLET = "#canton-refusal-record-test:TestAssets:Wallet"
SHAPE = "TRANSACTION_SHAPE_LEDGER_EFFECTS"

SECRET = {"salt": "NEEDLE-SALT-0123456789-ABCDEFGHIJKLMNOP",
          "action": "NEEDLE-ACTION-pay-1000-to-mallory",
          "detail": "NEEDLE-DETAIL-xyz"}
SIGNALLED = {"action": "MARK-ACTION-signalled", "detail": "MARK-DETAIL-signalled",
             "rule": "MARK-RULE-signalled"}
OPENED = {"salt": "CONF-SALT-0123456789-ABCDEFGHIJKLMNOPQ",
          "action": "CONF-ACTION", "detail": "CONF-DETAIL"}


def commitment(salt, action, detail):
    """`attemptCommitment` in Attempt.daml, computed here.

    Length-prefixed salt and action, then the detail, sha256 over the UTF-8
    bytes. Daml counts Unicode code points and so does len() on a str.
    """
    text = "%d:%s%d:%s%s" % (len(salt), salt, len(action), action, detail)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stream(who):
    """Everything this party was sent, as one string. Ledger-effects shape,
    because the default shape omits exercise arguments, which is the point."""
    end = T.call("/v2/state/ledger-end")["offset"]
    cumulative = [{"identifierFilter": {"WildcardFilter": {
        "value": {"includeCreatedEventBlob": False}}}}]
    body = {"beginExclusive": 0, "endInclusive": end, "updateFormat": {
        "includeTransactions": {"eventFormat": {"filtersByParty": {
            who: {"cumulative": cumulative}}, "verbose": True},
            "transactionShape": SHAPE}}}
    return json.dumps(T.call("/v2/updates", body))


def found(text, markers):
    """Which of these named marker strings appear in the text."""
    return [name for name, value in markers.items() if value in text]


def exercise(actors, cid, choice, args):
    return T.submit(actors, [{"ExerciseCommand": {
        "templateId": T.tid("Journal", "AttemptJournal"), "contractId": cid,
        "choice": choice, "choiceArgument": args}}])


def on_attempt(actors, cid, choice, args):
    return T.submit(actors, [{"ExerciseCommand": {
        "templateId": T.tid("Attempt", "Attempt"), "contractId": cid,
        "choice": choice, "choiceArgument": args}}])


def wallet(owner, guardian):
    tx = T.submit([owner, guardian], [{"CreateCommand": {
        "templateId": WALLET, "createArguments": {
            "holder": owner, "guard": guardian, "balance": "1000.0"}}}])
    return T.created(tx, "TestAssets", "Wallet")


def play_controls(p, journal):
    """Send the documented-to-leak choice, then read each party's stream."""
    exercise([p["owner"], p["actor"]], journal, "RefuseSignalled", SIGNALLED)
    seen = {name: found(stream(p[name]), SIGNALLED)
            for name in ("owner", "auditor", "guardian")}
    ok = len(seen["auditor"]) == 3 and len(seen["owner"]) == 3
    return ok, seen


def play_allowed_path(p, journal):
    """Open, Allow and Settle with the secret, and Refuse a conformance one."""
    who = [p["owner"], p["actor"]]
    c = commitment(**SECRET)
    tx = exercise(who, journal, "Open", {"commitment": c})
    attempt, journal = (T.created(tx, "Attempt", "Attempt"),
                        T.created(tx, "Journal", "AttemptJournal"))
    target = wallet(p["owner"], p["guardian"])
    on_attempt(who, attempt, "SettleAttempt", {"target": target})
    tx = exercise(who, journal, "Allow", {})
    return T.created(tx, "Journal", "AttemptJournal")


def play_conformance(p, journal):
    """Open with a commitment computed here; the ledger must accept the
    preimage. A mismatch is refused by `RefuseAttempt`, so success is proof."""
    who = [p["owner"], p["actor"]]
    tx = exercise(who, journal, "Open",
                  {"commitment": commitment(**OPENED)})
    attempt = T.created(tx, "Attempt", "Attempt")
    on_attempt(who, attempt, "RefuseAttempt", dict(OPENED, rule="allow-list"))


def report(p):
    allowed = {n: found(stream(p[n]), SECRET) for n in ("auditor", "guardian")}
    for name, hits in allowed.items():
        T.say("  %-9s received on the allowed path: %s"
              % (name, ", ".join(hits) if hits else "none of the three"))
    return allowed


def play():
    names = ("owner", "actor", "guardian", "auditor")
    p = {n: T.party(n) for n in names}
    journal = when_packages_ready(
        lambda: T.build(p["owner"], p["actor"], p["guardian"], p["auditor"]))
    T.say("CONTROLS")
    ok, seen = play_controls(p, T.journal_of(p["owner"])[0] or journal)
    for who in ("owner", "auditor", "guardian"):
        T.say("  %-9s received from RefuseSignalled: %d of 3 markers"
              % (who, len(seen[who])))
    if not ok:
        T.say("CONTROL FAILED: a leak that is meant to happen was not seen.")
        T.say("The tool cannot see leaks. Refusing to report.")
        return 1
    T.say("  controls pass: this tool can see what the auditor is sent.")
    return judge(p)


def judge(p):
    journal = T.journal_of(p["owner"])[0]
    T.say("\nCONFORMANCE (Python commitment against the ledger's)")
    play_conformance(p, journal)
    T.say("  the ledger accepted the preimage of a commitment computed here.")
    T.say("\nTHE ALLOWED PATH (Open, SettleAttempt, Allow)")
    play_allowed_path(p, T.journal_of(p["owner"])[0])
    allowed = report(p)
    leaked = allowed["auditor"] or allowed["guardian"]
    T.say("\nRESULT: " + ("the secret reached the auditor or the guardian."
          if leaked else "the secret did not reach the auditor or the guardian."))
    return 1 if (leaked and "--require-hidden" in sys.argv) else 0


def main():
    if T.ledger_running():
        return play()
    if not have_daml() or not build_chain(REFUSAL_CHAIN):
        return 1
    box = Sandbox(T.DAR, extra=["--json-api-port", T.BASE.rsplit(":", 1)[1]])
    try:
        return play() if box.start() else 1
    finally:
        box.stop()


if __name__ == "__main__":
    sys.exit(main())
