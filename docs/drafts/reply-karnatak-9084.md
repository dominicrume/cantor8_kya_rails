Post-To: https://forum.canton.network/t/9084  (Reply)

Arpit, you wrote that there was no standard pattern out there for committing
refused actions on-chain, and that this was why #627 keeps those logs off
ledger. That sentence is now quoted in a CIP draft on cip-discuss, because it
is better evidence than anything I could assert that the gap is real and costs
people design decisions.

There is a pattern now, if it is any use to you. Two Daml packages, MIT, no
dependency beyond the standard library, 170 scripts:
github.com/dominicrume/cantor8_kya_rails/tree/main/step-0-refusal

Two limits before you spend time on it. It has never run on DevNet, because I
have never held a credential. And it counts refusals by a cooperating actor,
not attacks: an attacker with a stolen key never opens an attempt, so the
counter stays at zero. Both are in the draft.

My question from 22 October is still open. At execute time your authority set
is the operator's, and my asset needs the guard too, so the exercise fails.
Second authorization, operator as guard, or guard pre-commits?

Separately: you are seeking a champion and so am I, under adjacent RFPs. If a
joint walkthrough is worth anything to you, I am up for it.
