#!/usr/bin/env python3
"""Open the four things in DO-THIS.md that a person has to do by hand.

Nothing here touches the repository or the network. It opens browser tabs and
prints which block of text belongs in each one, because the failure mode on a
Friday night is not forgetting the task, it is pasting the wrong body into the
right box.

    python3 tools/open_tabs.py          # open them
    python3 tools/open_tabs.py --dry    # just print, open nothing

Stdlib only, per CLAUDE.md.
"""

import sys
import webbrowser

# Order matters. Vacuumlabs first: answering somebody else before posting your
# own thread is the difference between helping and broadcasting.
TABS = [
    (
        "Canton Foundation Slack Request",
        "https://forms.monday.com/forms/1d6ba9aa5f15edece06d93a2a6645634?r=use1",
        "Company: Vorem. General channels: none. SIGs: regulatory-compliance, "
        "security, daml-tooling, dapp-integration. Full sheet: DO-THIS.md section 1.",
    ),
    (
        "Reply to Vacuumlabs (51 days, zero replies)",
        "https://forum.canton.network/t/9084",
        "Paste: the '## THE POST' section of docs/outreach/forum-reply-vacuumlabs.md",
    ),
    (
        "Reply to Federico (your own thread, 34 days silent)",
        "https://forum.canton.network/t/how-do-you-prove-your-app-didnt-do-something/9114",
        "Paste: the '## THE POST' section of docs/outreach/forum-reply-federico.md",
    ),
    (
        "New thread, App Development",
        "https://forum.canton.network/c/app-development",
        "Title and body: docs/outreach/forum-new-thread-denominator.md. "
        "Tags daml, canton.",
    ),
]

RULE = (
    "In none of the three forum posts: PR #860, the Dev Fund, or the word "
    "champion. Help first, ask nothing."
)


def main(argv: list) -> int:
    dry = "--dry" in argv
    width = max(len(name) for name, _, _ in TABS)

    for index, (name, url, paste) in enumerate(TABS, 1):
        print("{}. {}".format(index, name.ljust(width)))
        print("   {}".format(url))
        print("   {}".format(paste))
        print()
        if not dry:
            # new=2 asks for a tab rather than a window; the return value is
            # unreliable across platforms, so it is deliberately not checked.
            webbrowser.open(url, new=2)

    print(RULE)
    if dry:
        print("\n--dry: nothing was opened.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
