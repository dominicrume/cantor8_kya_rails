# Drafts waiting to go out

Run the queue. It checks each draft, copies it, opens the page, and then goes
and looks to see whether it actually arrived:

    python3 tools/post_queue.py

`posted.log` is written only when a post is **verified on the destination**, or
when you type `yes` to a destination that cannot be checked, and those lines
are marked unverified.

## The destinations, written down so a check can be constructed

Added 12 November 2026. An X post sat UNVERIFIED for two days partly because
nothing in this repository recorded which profile to look at, so there was no
URL to build a check from. A destination nobody has written down cannot be
read back.

| Channel | Handle or URL |
|---|---|
| X, personal | `https://x.com/dominicrume` |
| X, company | `https://x.com/vorem_co` |
| Canton forum | `https://forum.canton.network/u/orumedominic` |
| GitHub | `https://github.com/dominicrume` |
| cip-discuss | `https://lists.sync.global/g/cip-discuss` (needs a login; read-back from here returns a bot gate, so it is a CANNOT CHECK destination) |

## What this log does not cover

`posted.log` begins on 2026-11-04. Everything sent before that date is absent:
eleven forum posts, four #860 comments, two #866 comments, dpm#330 and
dpm#331. `docs/outreach/` holds 29 further files, several named as though they
were sent, and none of them is referenced here.

So this is a ledger of what `post_queue.py` handled, not of what left this
machine. On 12 November an audit also found four posts that had landed and
were never logged at all, which is the opposite of the over-recording failure
the tool was rebuilt to stop. The failure changed direction and nobody was
watching the new direction. Both are recorded in the log itself.

## Why the log is not written on a keystroke

The first version asked "Enter once it is posted" and wrote the date on that
keystroke alone. On 31 October 2026 it recorded two forum replies as posted.
Neither was on the forum.

That is the argument of `step-0-refusal` happening to its own tooling: a
record written by the party it is about, attesting to its own compliance, with
nothing independent checking it. The counter said one, the ledger said zero.
The fix is the same fix: do not take the actor's word, go and read the state.

Discourse topics and GitHub pull requests are checked directly. Groups.io
returns 402 to automated fetches and a brand new topic has no id yet, so those
two are logged on your word and say so in the log.
