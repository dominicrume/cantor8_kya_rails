# Drafts waiting to go out

Run the queue. It checks each draft, copies it, opens the page, and then goes
and looks to see whether it actually arrived:

    python3 tools/post_queue.py

`posted.log` is written only when a post is **verified on the destination**, or
when you type `yes` to a destination that cannot be checked, and those lines
are marked unverified.

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
