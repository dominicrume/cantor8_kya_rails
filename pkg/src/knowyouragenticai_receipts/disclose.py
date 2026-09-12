"""Hand over the refusals without handing over the book.

Prevention says the door was locked. This is the other question: show me
everything the agent tried and was stopped from doing, and let me check it
without trusting you.

Until now a chain was all or nothing. Slice out the refusals and the file no
longer verifies, because every seal covers the one before it. Hand over the
whole chain and you have disclosed every accepted payment as well, which for a
regulated issuer is the reason they cannot use it.

A disclosure keeps every entry's **position, outcome, prev and seal**, and the
full body of only the entries you chose to show:

    from knowyouragenticai_receipts import disclose, check_disclosure

    doc = disclose(chain.receipts, refusals_only)
    ok, why = check_disclosure(doc)

The reason `outcome` is never withheld is the whole design. If a producer could
hide an entry entirely, "here are my three refusals" would be indistinguishable
from a chain that had thirty. Leaving the outcome in the clear means a
withheld entry still announces itself as a refusal, and the reader can ask for
that one specifically. **You can decline to show a refusal. You cannot conceal
that it happened.**

WHAT A DISCLOSURE PROVES

  * Nothing was removed. Positions run 1..n with no gaps and every `prev`
    matches the previous seal, so a deleted entry breaks the document.
  * Every shown entry is genuine. Its body re-seals to the seal published
    beside it, computed by the reader.
  * The outcome of every entry, shown or withheld, is on the record.

WHAT IT DOES NOT PROVE, said here because a format that oversells itself is
worse than none:

  * A withheld body is what it claims. The reader has its seal and nothing
    else. A withheld entry could have carried anything, which is exactly why
    the outcome stays visible.
  * A withheld entry's outcome, on its own. The seal is published but the
    body is not, so the label cannot be recomputed. The `disclosing` field is
    what makes it checkable in the normal case: a document promising to show
    every refusal cannot also withhold one. A producer who instead relabels a
    withheld refusal as accepted has made a positive false statement about a
    numbered entry, which the full chain or its anchor will contradict.
  * That the chain itself is complete. A producer who ran an agent and threw
    the whole chain away has nothing to disclose from. That is what anchoring
    the head is for, and it is a separate question.
  * That anyone was refused for a good reason. This carries decisions, it does
    not make them.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from . import GENESIS, canonical, seal

__all__ = ["disclose", "check_disclosure", "refusals_only", "WITHHELD",
           "EVERY_REFUSAL", "what_this_reveals"]

WITHHELD = "withheld"

# The default promise a disclosure makes about itself.
EVERY_REFUSAL = "every entry whose outcome is not ACCEPTED"

# Never withheld, whatever the chooser says. Position and links are what prove
# nothing was removed; the outcome is what stops a refusal being concealed.
ALWAYS_SHOWN = ("n", "outcome", "prev", "seal")


def refusals_only(receipt: Mapping[str, Any]) -> bool:
    """The common case: show what was stopped, withhold what went through.

    POLICY is shown. A refusal reading "would exceed the cap" is half a
    sentence without the cap beside it, and the policy entry is where the cap
    lives. This function withheld it at first, which contradicted the
    docstring above it and produced disclosures a reader could not act on.
    """
    return str(receipt.get("outcome", "")).upper() != "ACCEPTED"


def _entry(r: Mapping[str, Any], shown: bool) -> dict[str, Any]:
    """One entry: always its position, outcome, link and seal; the body only
    if it is being shown."""
    entry = {k: r.get(k) for k in ALWAYS_SHOWN}
    if shown:
        entry["body"] = {k: v for k, v in r.items() if k != "seal"}
    else:
        entry[WITHHELD] = True
    return entry


def disclose(receipts: Sequence[Mapping[str, Any]],
             show: Callable[[Mapping[str, Any]], bool] = refusals_only
             ) -> dict[str, Any]:
    """A document carrying the chosen entries in full and the rest as seals.

    `show` decides, per receipt, whether the body travels. The default shows
    everything that is not an accepted payment, which is refusals plus the
    policy that was in force, because a refusal without the rule it broke is
    half a sentence.
    """
    entries = [_entry(r, show(r)) for r in receipts]
    return {
        "kind": "know-your-agenticai-disclosure",
        "spec": "1.2",
        "count": len(receipts),
        "head": receipts[-1].get("seal", "") if receipts else GENESIS,
        "shown": sum(1 for e in entries if "body" in e),
        # The rule the producer says they applied. Declaring it is what makes
        # a withheld entry's outcome checkable at all: with the default rule
        # in force, a withheld entry claiming REFUSED contradicts the document
        # that carries it, and check_disclosure refuses the whole thing.
        # Without this, a producer could withhold a refusal and relabel it
        # accepted, because a withheld entry has no body to contradict it.
        "disclosing": (EVERY_REFUSAL if show is refusals_only else "a chosen subset"),
        "entries": entries,
    }


def _check_envelope(doc: Any) -> str:
    """The document about itself: is this even a disclosure, and does its own
    count match what it carries."""
    if not isinstance(doc, Mapping):
        return "not a disclosure document"
    entries = doc.get("entries")
    if not isinstance(entries, list) or not entries:
        return "no entries"
    if doc.get("count") != len(entries):
        return "count says %s, there are %d entries" % (doc.get("count"), len(entries))
    return ""


def _check_promise(doc: Mapping[str, Any], entries: list) -> str:
    """The promise the document makes about itself, checked against it.

    A withheld body cannot be recomputed, so a withheld entry's outcome is
    otherwise unfalsifiable. Declaring the rule is what makes it checkable: a
    document promising to show every refusal cannot also withhold one.
    """
    if doc.get("disclosing") != EVERY_REFUSAL:
        return ""
    for e in entries:
        if e.get(WITHHELD) and refusals_only(e):
            return ("entry %s is withheld and says it is %s, but this document "
                    "claims to show %s" % (e.get("n"), e.get("outcome"), EVERY_REFUSAL))
    return ""


def _check_totals(doc: Mapping[str, Any], entries: list, prev: str) -> str:
    """The two counts the document states about itself."""
    if doc.get("head") and doc["head"] != prev:
        return "the head does not match the last entry"
    shown = sum(1 for e in entries if "body" in e)
    if doc.get("shown") is not None and doc["shown"] != shown:
        return "says %s shown, %d are shown" % (doc.get("shown"), shown)
    return ""


def _check_entry(e: Any, index: int, prev: str) -> str:
    """What is wrong with one entry, or empty when nothing is.

    Split out of check_disclosure so each rule reads on its own. A single
    function holding every rule is one nobody can read a refusal out of, and
    the refusal text is the part the reader of a disclosure actually needs.
    """
    if not isinstance(e, Mapping):
        return "entry %d is not an object" % index
    if e.get("n") != index:
        return ("entry at position %d is numbered %s, so one was removed or "
                "reordered" % (index, e.get("n")))
    if e.get("prev") != prev:
        return "entry %d does not follow the one before it" % index
    if not e.get("outcome"):
        return ("entry %d withholds its outcome, which a disclosure may never "
                "do" % index)
    return _check_body(e, index, prev)


def _check_body(e: Mapping[str, Any], index: int, prev: str) -> str:
    """A shown body must re-seal to the seal printed beside it, and must agree
    with the outcome the entry declares. A missing one must say it is
    withheld, so that absence is a statement rather than a gap."""
    body = e.get("body")
    if body is None:
        return ("" if e.get(WITHHELD)
                else "entry %d has no body and does not say it is withheld" % index)
    try:
        recomputed = seal(body, prev)
    except (TypeError, ValueError):
        return "entry %d has a body that cannot be sealed" % index
    if recomputed != e.get("seal"):
        return "entry %d was edited after it was sealed" % index
    if body.get("outcome") != e.get("outcome"):
        return "entry %d states one outcome and its body says another" % index
    return ""


def check_disclosure(doc: Any) -> tuple[bool, str]:
    """(ok, what is wrong). Never raises: this reads a file a stranger sent.

    Three things are checked, in the order a reader cares about. Nothing was
    removed. Everything shown is genuine. The document describes itself
    honestly.
    """
    why = _check_envelope(doc)
    if why:
        return False, why
    entries = doc["entries"]

    prev = GENESIS
    for index, e in enumerate(entries, start=1):
        why = _check_entry(e, index, prev)
        if why:
            return False, why
        prev = e.get("seal")
        if not isinstance(prev, str) or not prev:
            return False, "entry %d has no seal" % index

    why = _check_promise(doc, entries) or _check_totals(doc, entries, prev)
    return (False, why) if why else (True, "")


def summary(doc: Mapping[str, Any]) -> str:
    """One line a person can read, including what was kept back."""
    entries = doc.get("entries") or []
    shown = sum(1 for e in entries if "body" in e)
    held = [e for e in entries if WITHHELD in e]
    line = "%d entries, %d shown in full, %d withheld" % (len(entries), shown, len(held))
    return line + _held_refusal_note(held) + "."


def _held_refusal_note(held: list) -> str:
    """A refusal kept back is the sentence a reader must not miss."""
    n = sum(1 for e in held if refusals_only(e))
    if not n:
        return ""
    return (". %d withheld entr%s a refusal, and can be asked for by number"
            % (n, "y is" if n == 1 else "ies are"))


def what_this_reveals(receipts: Sequence[Mapping[str, Any]],
                      doc: Mapping[str, Any]) -> list[str]:
    """Read this before sending. What a withheld entry gives away anyway.

    Withholding a body is not the same as withholding its contents. A refusal
    reads "would exceed the cap: 10.00 + 999.00 > 100.00", and the 10.00 is
    the accepted payment sitting two entries above it, withheld and quoted
    verbatim inside a refusal that is shown. A running total is a statement
    about everything that came before it.

    This cannot be fixed by redacting, because changing a shown body breaks
    its seal and the disclosure stops verifying. It can only be pointed at, so
    the producer decides knowingly rather than discovering it afterwards.

    Returns one plain line per leak, empty when there is nothing to say.
    """
    entries = [e for e in doc.get("entries", []) if isinstance(e, Mapping)]
    shown_text, policy_text = _shown_and_policy_text(entries)
    withheld_ns = {e.get("n") for e in entries if e.get(WITHHELD)}
    out = []
    for r in receipts:
        if r.get("n") in withheld_ns:
            out += _leaks_from(r, shown_text, policy_text)
    return out


def _shown_and_policy_text(entries: list) -> tuple[str, str]:
    """(everything shown, just the policy).

    The policy lists the allow-list and the cap on purpose. A withheld payee
    that is simply named there is not a leak from that entry, it is the policy
    doing its job, and flagging it buries the one line that matters.
    """
    shown = [e.get("body") for e in entries if "body" in e]
    policy = [b for b in shown
              if isinstance(b, Mapping)
              and str(b.get("outcome", "")).upper() == "POLICY"]
    return canonical(shown), canonical(policy)


def _leaks_from(r: Mapping[str, Any], shown_text: str, policy_text: str) -> list[str]:
    """Which of one withheld receipt's own values appear in what is shown."""
    out = []
    for field in ("amount", "payee"):
        value = str(r.get(field, ""))
        if len(value) < 4 or value not in shown_text:
            continue
        if value in policy_text:
            continue                      # the policy lists it on purpose
        out.append("entry %s is withheld, but its %s (%s) appears inside an "
                   "entry you are showing" % (r.get("n"), field, value))
    return out
