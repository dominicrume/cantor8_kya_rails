# KYA RAILS. THE RULES.
Build for Cantor8 "Build on Canton" Hackathon, challenge D1: a spend-limited wallet for an AI agent.
Built with the KYA Method: Promise it. Attack it. Inspect it. Prove it.

## The promise
An AI agent may spend money ONLY under a written mandate: a cap, an allow-list
of counterparties, an expiry. Every action the agent takes, including the ones
the ledger REFUSES, produces a sealed receipt a human can read and anyone can verify.

## Must always
- Enforce cap, allow-list and expiry IN DAML, in the choice body. Never only in Python.
- Record every attempt as a receipt: what, when, which rule allowed or refused it.
- Seal each receipt over the previous seal. Chain must verify end to end.
- Say what is mocked, out loud, in the demo. Overclaiming loses; honesty scores.

## The rule that outranks the others

**Never do anything that is the opposite of becoming worth championing.**

Nothing here gets built, filed, published or sent unless it would still have
been the right thing to do if the other side never reciprocated. That is the
whole test, and it is a single question asked before every outward action:

> *Would I still do this if they never replied, never funded it, and never
> knew my name?*

If the answer is no, it is leverage wearing the costume of a contribution, and
it fails even when it works -- because the people worth being championed by can
tell the difference, and they are the only audience that matters.

This rule was written after breaking it. Three hours went into mutation testing
`digital-asset/daml-finance` -- 71 fences in a company's flagship library -- so
that 71 unrequested findings could be handed to an organisation whose signature
the Dev Fund requires. OpenZeppelin had ASKED: *"clone the repos, open an issue
with how it works for what you're building."* Digital Asset asked for nothing,
and the repository had been frozen for seventeen months. An uninvited audit of
dormant code, delivered by someone who then appears in your funding queue, is
not a gift. The run was stopped and their working tree restored.

What it forbids, concretely:

- **Uninvited work aimed at someone we need something from.** Invited work is a
  contribution. The same work uninvited, timed to a request, is pressure.
- **Volume.** Five messages in an afternoon is a campaign, not five
  conversations. Two across a week is two conversations.
- **Chasing.** An update is welcome; "did you see this?" is a debt collector.
  Every message says what it adds and asks for nothing.
- **Publishing what we learned about people whose help we want.** The Dev Fund
  measurements in `docs/dev-fund-reality.md` are true and useful and stay
  internal. Knowing a thing does not require saying it out loud.
- **Being wrong in public about somebody else's code.** A false finding filed
  against a stranger's repository is the single most expensive mistake
  available here. Verify by hand, check the DAR hash changed, and say what the
  tool cannot see.

What it requires:

- Fix things for other people where our own problem is the smallest part.
  `Canton-Developer-Hub#160` renders the links of nineteen entries; ours is one
  of them, and the pull request is written about the other eighteen.
- Take corrections faster than we give them.
- Publish the limits beside the claims -- `docs/what-this-proves.md` is more
  persuasive than any feature list, because it is the part nobody fakes.

## Must never
- No production keys, no real funds, no Vorem wallets. Testnet and LocalNet only.
- No secrets in this repo. Ever.
- Never modify the organisers' toolkit; it is a dependency, not our code.
- No claim without a number behind it.

## The NOT list
- step-1-mandate does not read the chain library or the UI.
- step-2-agent does not contain business rules; rules live in Daml. The agent only tries.
- step-3-verify does not talk to the ledger; it reads receipts.js only.

## Stage map
step-1-mandate: the Daml contract, caps and allow-list enforced on ledger.
step-2-agent:   the agent, the charge attempts, the receipt chain writer.
step-3-verify:  the chat demo + verifier page + tamper test.

## The numbers we bring to judging
- charges under cap: accepted on ledger
- charge over cap: REFUSED on ledger (show the Daml line)
- charge to non-allow-listed party: REFUSED on ledger
- charge after revoke: REFUSED on ledger
- receipts in chain: N, chain verifies: true, tamper detected: true
