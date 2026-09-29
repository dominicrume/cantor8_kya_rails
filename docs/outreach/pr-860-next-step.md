# PR #860: what the email meant, and the one move that follows

## The email

`SIG labels auto-detected and applied: regulatory-compliance`

A robot read the proposal, decided which Special Interest Group it belongs to,
and tagged it. That is all it was. It is not approval, not rejection, and not a
person.

**State today:** open, both checks passing, one comment, that comment being the
robot. No human has read it. That is normal: proposals here sit six to eleven
days before anyone speaks.

## Filing was right, and the reason is narrower than I said

I told you the champion gate had been removed. That was wrong in the other
direction, and the record needs it straight.

The gate still exists and it still closes proposals. #851 on 21 September and
#811 on 18 September were both closed automatically for having no valid
champion, citing **CIP-0100**:

> "If no champion can be found, the Tech & Ops committee should communicate
> back to the proposer(s) that the proposal will not be taken forward... and
> funding from the development fund will not be available."

What actually changed is the enforcement. **Every proposal filed since Dev Fund
2.0 merged on 22 September is still open, and not one carries a champion
label.** The robot stopped closing them. The rule did not go away.

So: filing was correct, #860 is safe, and it will not be funded without a
champion. Both halves are true at once.

## The move, and it is the process working as designed

The review process says it plainly:

> "Members of the various SIGs are encouraged to review proposals aligned with
> their area of interest and may **self assign proposals they want to review
> directly**."
>
> "Participation in SIGs is **not limited to Foundation members**."

And the robot tells closed proposals: *"If you need help finding a champion,
reach out to SIGs."*

Our proposal is already labelled into one. The **Regulatory Compliance** SIG:

| Name | Organization | GitHub |
|---|---|---|
| Julie Lascar | Digital Asset | |
| Kelly Mathiesen | Digital Asset | |
| Shaul Kfir | Digital Asset | `shaul-da` |
| Nikos Andrikogiannopoulos | Metrika | `nikos-metrika` |

Two have public handles. **Digital Asset is on the champion list.** This is not
a back door. It is the door.

## Post this as a comment on #860

```
Adding context for anyone from the Regulatory Compliance SIG who picks
this up.

The gap: on Canton a failed assertMsg aborts the transaction. An action
a rule stopped leaves nothing on the ledger. Settled actions are
corroborated by the ledger. Refused ones sit in the operator's own logs,
written by the operator, about the operator.

RFP 27 asks for audit trails and compliance evidence while preserving
Canton's privacy model, with selective disclosure handled explicitly.
That is what this is.

The reference implementation already exists, MIT licensed. A Daml
package with no dependencies beyond daml-prim and daml-stdlib. 111 test
scripts. A browser verifier that needs no wallet and no install.

I am seeking a champion. Happy to answer anything, or to narrow the scope
if that makes it easier to assess.
```

### On tagging people

The draft above tags nobody. That is deliberate for a first comment.

If it is still silent in a week, `@nikos-metrika` is the softer second step:
Metrika rather than Digital Asset, and a public handle offered in a directory
that exists so people can be found.

`@shaul-da` is Digital Asset's co-founder. That is a real swing and it is
available, and it should be a decision you make on purpose rather than one I
make for you.

**Do not tag anyone in the first comment.** One ask at a time.
