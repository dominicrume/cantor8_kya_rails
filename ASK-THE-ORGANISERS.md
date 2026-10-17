# Questions for the people who run this ecosystem

*Prepared 2026-10-17. Written before the Cantor8 winners' dinner, 18 October.*

The team that won the Cantor8 hackathon kept a file called `ASK-DAVIDE.md`:
questions for the organiser, written down **before** the conversation. That is
"seek to understand before being understood" turned into an artefact rather
than a sentiment, and it is the single cheapest habit in this repository to
copy.

The rule for every question below: **it is a question, not a request wearing a
question mark.** If the honest shape of it is "please give me something", it
goes in the ask section at the bottom, once, and nowhere else.

---

## For Davide, Cantor8 developer

1. In Daml a failed `assertMsg` aborts the transaction, so a blocked payment
   leaves nothing on the ledger. Is that how Cantor8 sees it, or is there a
   pattern in the toolkit that already handles it?
2. The four toolkit pull requests (#7 to #10) have been open since 31 August.
   Are they wanted, or is the toolkit frozen? **Either answer is useful.**
3. What actually broke for teams on the day? The DevNet findings from the
   winning team read like they hit the same walls.
4. Does Cantor8 run its own validator, and would an external builder ever get
   read access to it rather than a full credential?

## For Philip Kaddaj, CEO, Cantor8

1. Where does Cantor8 go after the accelerator? What is the twelve-month shape?
2. p402 settled an agent payment in April. Is there a spec or a repo for it, or
   is it still internal? *(Nothing public is findable, so this is a real
   question, not a trap.)*
3. Cantor8 funded a Cambridge researcher on agentic AI on Canton in March. Who
   handles research grants, and is that a programme or a one-off?
4. Is Cantor8 building agent identity or agent mandates itself? If so, an
   outside implementation is a complement or a competitor and it matters which.

## For Dr Adaku Agwunobi, Oxford Blockchain Society

1. What does the accelerator need from a team, and by when?
2. Is it for teams or for projects? A solo entrant is a different proposition.
3. What happens to the teams who were not placed?

## For the Canton Foundation, if anyone from it is in the room

1. The roadmap lists 28 RFPs. **RFP 27 asks for audit trails and compliance
   evidence while preserving the privacy model.** Who reviews that category?
2. The review process says a proposal does not enter review without a champion.
   How does an independent contributor find one?
3. Agentic AI appears once in the whole 269-line roadmap, as read-only MCP
   access. Is agent authorisation deliberately out of scope for now?
4. There was a CIP for agent identity and mandate-bound payments (cips #202).
   It was closed in August with no comments. Was that scope, timing, or
   process?

## For C7 / 7RIDGE and Alchemy, if present

1. What is the hardest part of getting an institution from pilot to live on
   Canton?
2. Who in your portfolio is building with Daml and short of hands?
3. *(Alchemy only)* What did you make of the Canton entries? You see a lot of
   chains, so where does Canton actually sit for you?

## For the other teams

1. **How did you get DevNet access?** Ask this first. One team moved real
   Canton Coin through their mandate and this project never has.
2. What broke that you did not expect?
3. Are you carrying on, or was it a weekend? *(Both first and second place have
   not committed since 29 August. Worth knowing why.)*

---

## The asks, once each, and never two to the same person

| Who | The one ask |
|---|---|
| Davide | `C8_CLIENT_SECRET`. Say openly that Philip was asked first. |
| Philip | Who handles research grants. **Not** the job, **not** the credential: he already has both asks. |
| Dr Adaku | "I would like to be considered for the accelerator. What do you need from me?" |
| Canton Foundation | A name for a Tech and Ops champion. |
| C7 / Alchemy | An introduction, not an application. |

## What not to say

- *"Nobody else does this."* Someone does. `docs/prior-art.md` names them.
- *"The EU AI Act requires it."* It almost certainly does not apply.
- Any second ask. A person asked once remembers the ask. A person asked three
  times remembers that you wanted things.
