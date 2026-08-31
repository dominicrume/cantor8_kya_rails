#!/usr/bin/env python3
"""Breet deposit webhook -> ConfirmDepositSeen.

The first real provider wired in. An endpoint that confirms deposits is an
endpoint that causes payouts, so this file is mostly refusals.

Breet's own scheme, from their docs:
  - every request carries an `x-webhook-secret` header, compared against the
    secret in your dashboard
  - requests come from a fixed IP allowlist
  - deposit events are `trade.pending`, `trade.completed`, `trade.flagged`
  - retries up to 7 times with backoff; dedupe on `id` + `event`
  - `isWrongAssetDeposit` flags a deposit of the wrong asset

A shared secret in a header is a BEARER credential, not a signature: anyone
who obtains it can forge a confirmation, and unlike an HMAC it does not bind
the secret to the body. It is what the provider offers, so it is what we
check -- with a constant-time comparison, alongside the IP allowlist, and
never as the only thing standing between a message and a payout. Every field
is matched against the deal we already hold before anything is confirmed.

Stdlib only.
"""
import hmac, json, time

# From Breet's documentation. Kept here rather than in config because a
# silently-empty allowlist is an allowlist that permits everything.
BREET_IPS = frozenset([
    "46.101.201.155", "46.101.225.109", "46.101.225.97",
    "46.101.225.251", "159.89.20.62",
])

DEPOSIT_COMPLETED = "trade.completed"


class Refused(Exception):
    """Understood, and not acted on. Returns 2xx so the provider stops retrying."""


class BreetAdapter:
    def __init__(self, desk, secret, allow_ips=BREET_IPS, require_ip=True):
        if not secret:
            raise ValueError("a webhook secret is required; without one any "
                             "caller can confirm a deposit")
        self.desk = desk
        self._secret = secret
        self.allow_ips = frozenset(allow_ips)
        self.require_ip = require_ip
        self.seen = set()        # (id, event) -- their documented dedupe key
        self.log = []            # every delivery, accepted or refused

    # -- the checks, in the order that fails cheapest first -----------------
    def _authenticate(self, headers, src_ip):
        got = headers.get("x-webhook-secret") or headers.get("X-Webhook-Secret") or ""
        # Constant time: a plain == leaks the secret one byte at a time to
        # anyone who can measure the response.
        if not hmac.compare_digest(str(got), str(self._secret)):
            raise Refused("bad or missing x-webhook-secret")
        if self.require_ip and src_ip not in self.allow_ips:
            raise Refused("source IP %s is not on the provider's allowlist" % src_ip)

    def handle(self, headers, src_ip, body):
        """Returns (http_status, response_dict). Never raises to the caller.

        Always 2xx once the request is authenticated, including when refused:
        their retry policy is up to seven attempts with backoff, and retrying
        a message we have understood and rejected achieves nothing except
        seven chances for a race.
        """
        entry = {"at": time.time(), "ip": src_ip, "outcome": None, "why": None}
        try:
            self._authenticate(headers, src_ip)
        except Refused as e:
            entry.update(outcome="REJECTED", why=str(e))
            self.log.append(entry)
            # Unauthenticated: 401, and no detail about why.
            return 401, {"error": "unauthorised"}

        try:
            result = self._apply(body, entry)
            entry.update(outcome="CONFIRMED", why=result.get("reference"))
            self.log.append(entry)
            return 200, result
        except Refused as e:
            entry.update(outcome="REFUSED", why=str(e))
            self.log.append(entry)
            return 200, {"received": True, "acted": False, "reason": str(e)}

    def _apply(self, body, entry):
        if not isinstance(body, dict):
            raise Refused("body is not an object")

        event = body.get("event")
        event_id = body.get("id")
        if not event_id:
            raise Refused("no id on the event, so it cannot be deduplicated")
        entry["id"] = event_id

        key = (event_id, event)
        if key in self.seen:
            raise Refused("duplicate delivery of %s" % event)

        # Only a completed deposit confirms anything. Pending is not money,
        # and flagged is the provider telling you not to.
        if event != DEPOSIT_COMPLETED:
            self.seen.add(key)
            raise Refused("event %r is not a completed deposit" % event)

        if body.get("isWrongAssetDeposit"):
            self.seen.add(key)
            raise Refused("provider flagged a wrong-asset deposit")

        address = body.get("destinationAddress")
        if not address:
            raise Refused("no destinationAddress on the event")

        # Find OUR deal by the address we issued. The webhook does not get to
        # tell us which deal it is; it tells us where money landed, and we
        # match that against what we already hold.
        deals = [d for d in self.desk.deals.values()
                 if d["depositAddress"] == address and d["state"] == "QUOTED"]
        if not deals:
            raise Refused("no open deal is expecting a deposit at that address")
        if len(deals) > 1:
            # Ambiguous by construction. A unique address per deal removes
            # this entirely and is worth asking the provider for.
            raise Refused("%d open deals share that address; cannot attribute"
                          % len(deals))
        deal = deals[0]

        asset = body.get("asset")
        if asset and str(asset).upper() != deal["asset"].upper():
            raise Refused("deposit asset %s does not match the deal's %s"
                          % (asset, deal["asset"]))

        try:
            amount = float(body.get("cryptoAmount"))
        except (TypeError, ValueError):
            raise Refused("cryptoAmount is missing or not a number")
        if abs(amount - float(deal["amount"])) > 1e-9:
            raise Refused("deposit of %s does not match the quoted %s"
                          % (amount, deal["amount"]))

        tx = body.get("txHash")
        if not tx:
            raise Refused("no txHash; a confirmation must point at something checkable")

        self.seen.add(key)
        self.desk.confirm_deposit(deal["reference"])
        deal["txReference"] = tx
        return {"received": True, "acted": True,
                "reference": deal["reference"], "txHash": tx}
