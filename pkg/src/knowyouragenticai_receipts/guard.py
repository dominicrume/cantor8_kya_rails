"""Wrap what an agent tries to do, so the refusals are on the record too.

Logs tell you what an agent did. Almost nothing tells you what it *tried* and
was stopped from doing, in a form you can hand to somebody who does not trust
you. That is the gap this closes:

    from knowyouragenticai_receipts import Policy, guard

    p = Policy(cap="100.00", currency="USD", allow=["acme"])
    chain = p.open()

    @guard(p, chain, what="refund a customer")
    def refund(amount, payee):
        return stripe.refund(amount, payee)

    refund("40.00", "acme")        # runs, and is recorded ACCEPTED
    refund("90.00", "acme")        # raises Refused, and is recorded REFUSED
    refund("1.00", "stranger")     # raises Refused, never reaches stripe

Two properties matter more than the convenience.

**A refusal is enforced, not merely noted.** The wrapped function is not called
when the policy says no. A decorator that recorded a refusal and then ran the
payment anyway would produce a chain that reads correctly and describes
something that did not happen, which is worse than no chain at all.

**The record says who did the refusing.** `enforced_by` is the honest part of
this module. Here it is the operator's own process: the party being checked is
also the party doing the checking, and a reader should discount it accordingly.
On a ledger, an independent party refuses and the receipt says so. The two are
never allowed to look alike, because the whole value of the format is that a
reader can tell how much to believe it.
"""
from __future__ import annotations

import functools
import time
from typing import Any, Callable, TypeVar

from . import Chain
from .policy import Policy

__all__ = ["Refused", "guard", "attempt", "SELF_ATTESTED"]

F = TypeVar("F", bound=Callable[..., Any])

SELF_ATTESTED = "self-attested (the operator's own process refused)"


class Refused(PermissionError):
    """The policy said no. Carries the rule, so a caller can show the reason
    rather than inventing one."""

    def __init__(self, rule: str, receipt: dict[str, Any]) -> None:
        super().__init__(rule)
        self.rule = rule
        self.receipt = receipt


def attempt(policy: Policy, chain: Chain, what: str, amount: str, payee: str,
            run: Callable[[], Any] | None = None,
            enforced_by: str = SELF_ATTESTED,
            instrument: str = "") -> Any:
    """One attempt: decide, record, and only then act.

    The order is the whole point. The receipt is written before the side
    effect, so a process killed mid-payment leaves a record of the attempt
    rather than a payment nobody can account for. `mcp_survives_kill` makes
    the same argument for the wallet.
    """
    # Decide, record and commit as one step. Anything less and two callers
    # can each be under the cap alone and over it together.
    with policy.lock:
        allowed, rule, receipt = _decide(policy, chain, what, amount, payee,
                                         enforced_by, instrument)
    if not allowed:
        raise Refused(rule, receipt)
    return None if run is None else run()


def _decide(policy: Policy, chain: Chain, what: str, amount: str, payee: str,
            enforced_by: str, instrument: str) -> tuple[bool, str, dict[str, Any]]:
    """The part that must not be interleaved: read the budget, seal the
    receipt, and spend the budget, with nothing else getting between them."""
    allowed, rule = policy.check(amount, payee)
    receipt = chain.stamp(
        what=what,
        amount=str(amount),
        payee=payee,
        currency=policy.currency,
        instrument=instrument or "policy-governed action",
        rule=rule,
        outcome="ACCEPTED" if allowed else "REFUSED",
        approved_by="the mandate, checked before the call",
        ledger=enforced_by,
        at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
    # Counted only once the policy has allowed it, and before the call, so a
    # failure inside `run` cannot hand the agent its budget back.
    if allowed:
        policy.commit(amount)
    return allowed, rule, receipt


def guard(policy: Policy, chain: Chain, what: str = "",
          amount_arg: str = "amount", payee_arg: str = "payee",
          enforced_by: str = SELF_ATTESTED) -> Callable[[F], F]:
    """Decorator form. The amount and payee are read from the call by NAME.

    By name rather than by position because a positional convention silently
    breaks the day somebody reorders the parameters -- and it would break in
    the direction of recording the wrong payee against the right amount, which
    is the shape of an error nobody catches by reading the log.
    """
    def decorate(fn: F) -> F:
        label = what or fn.__name__.replace("_", " ")

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            bound = _named(fn, args, kwargs)
            for name in (amount_arg, payee_arg):
                if name not in bound:
                    raise TypeError(
                        "%s() was guarded on '%s', but the call has no such "
                        "argument. The guard reads them by name; rename the "
                        "parameter or pass amount_arg/payee_arg."
                        % (fn.__name__, name))
            return attempt(policy, chain, label,
                           str(bound[amount_arg]), str(bound[payee_arg]),
                           run=lambda: fn(*args, **kwargs),
                           enforced_by=enforced_by)
        return wrapper  # type: ignore[return-value]
    return decorate


def _named(fn: Callable[..., Any], args: tuple[Any, ...],
           kwargs: dict[str, Any]) -> dict[str, Any]:
    """Call arguments as a name->value mapping, defaults included.

    inspect is stdlib, so this costs nothing the project's constraints forbid.
    """
    import inspect
    sig = inspect.signature(fn)
    bound = sig.bind_partial(*args, **kwargs)
    bound.apply_defaults()
    named = dict(bound.arguments)
    # A **kwargs parameter collects everything into one nested dict, so a tool
    # written as `def run(**kw)` -- which is how most tool-calling frameworks
    # shape a handler -- looked to the guard like a function with no `amount`
    # at all. Lift those to the top level, without letting them shadow a real
    # parameter of the same name.
    for name, param in sig.parameters.items():
        if param.kind is inspect.Parameter.VAR_KEYWORD:
            collected = named.pop(name, {}) or {}
            for key, value in collected.items():
                named.setdefault(key, value)
    return named
