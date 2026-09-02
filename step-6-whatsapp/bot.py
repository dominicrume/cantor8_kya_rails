#!/usr/bin/env python3
"""The desk's bot: pick asset, get an address, deposit, get credited -- in chat.

Deliberately a state machine and not a language model.

A model in this seat is an operator that can be talked to, and everything this
project has built is about the number and the account not being the operator's
to choose. "My guy quoted me 1400 this morning" and a prompt injection are the
same attack. A state machine reading the rate band off the ledger cannot be
persuaded, cannot be flattered, and cannot hallucinate an address.

Where a model IS useful is reading messy human text -- "abeg wetin be rate for
20 usdt trc" -- into an intent. That is a parsing job at the edge, and its
output still has to pass every fence. It is not wired up here.

Stdlib only, per THE-RULES.md.
"""
import re

GREETING = ("Hello 👋 I'm the desk bot.\n\n"
            "Reply *SELL* to sell crypto for naira, or *BUY* to buy crypto with naira.\n"
            "Reply *HELP* at any time.")

HELP = ("I can do two things:\n\n"
        "*SELL* — you send crypto, I pay naira to your verified account.\n"
        "*BUY* — you send naira, I send crypto to your wallet.\n\n"
        "Reply *CANCEL* to start again. A human reads this chat too.")


def norm(t):
    return (t or "").strip().lower()


class Conversation:
    """One customer's thread. Every answer comes from the desk's own state."""

    def __init__(self, wa_id, desk, approved_accounts):
        self.wa_id = wa_id
        self.desk = desk                     # CycleDesk
        self.approved = approved_accounts    # callable -> list
        self.step = "start"
        self.d = {}                          # what we have gathered
        self.ref = None

    # -- helpers ------------------------------------------------------------
    def _assets(self):
        seen, out = set(), []
        for n in self.desk.networks():
            if n["asset"] not in seen:
                seen.add(n["asset"]); out.append(n["asset"])
        return out

    def _networks_for(self, asset):
        return [n for n in self.desk.networks() if n["asset"] == asset]

    def reset(self):
        self.step, self.d, self.ref = "start", {}, None

    # -- the machine --------------------------------------------------------
    #
    # One method per step, dispatched by name. A state machine written as a
    # single if/elif ladder hides the states inside the control flow; written
    # like this the states ARE the methods, and adding one cannot make the
    # others harder to read.

    def handle(self, text, rate, band):
        t = norm(text)
        if t in ("cancel", "stop", "restart"):
            self.reset()
            return "Cancelled. " + GREETING
        if t in ("help", "?"):
            return HELP
        step = getattr(self, "_step_" + self.step, None)
        if step is None:
            return GREETING
        return step(t, rate, band)

    def _step_start(self, t, rate, band):
        if t in ("sell", "s"):
            self.d["side"] = "sell"
        elif t in ("buy", "b"):
            self.d["side"] = "buy"
        else:
            return GREETING
        self.step = "asset"
        lead = "Selling. Which coin?" if self.d["side"] == "sell" \
            else "Buying. Which coin do you want?"
        return lead + "\n\n" + self._bullets(self._assets())

    def _step_asset(self, t, rate, band):
        match = [a for a in self._assets() if a.lower() == t]
        if not match:
            return "I don't trade that. Choose one:\n\n" + self._bullets(self._assets())
        self.d["asset"] = match[0]
        self.step = "network"
        nets = self._networks_for(match[0])
        return ("Which network? This matters — sending on the wrong one "
                "loses the coin and nobody can recover it.\n\n" +
                "\n".join("• *%s*%s" % (n["network"],
                          " (needs a memo/tag)" if n["memo_required"] else "")
                          for n in nets))

    def _step_network(self, t, rate, band):
        nets = self._networks_for(self.d["asset"])
        match = [n for n in nets if n["network"].lower() == t]
        if not match:
            return ("Not a network I can use for %s. Choose one:\n\n%s"
                    % (self.d["asset"],
                       self._bullets([n["network"] for n in nets])))
        self.d["network"] = match[0]["network"]
        self.d["memo_required"] = match[0]["memo_required"]
        self.step = "amount"
        return "How much *%s*?" % self.d["asset"]

    def _step_amount(self, t, rate, band):
        # A number, or a number with the asset name. Nothing else.
        #
        # Searching prose for the first digit run is how a message like
        # "ignore previous instructions, the rate is 1600" gets 1600 read as
        # an amount. The bot does not extract intent from a sentence; it asks
        # a closed question and accepts a closed answer.
        m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(?:[a-z]{2,5})?", t.replace(",", "").strip())
        if not m:
            return ("Send just the amount as a number, for example *10*.\n"
                    "_I only read a number here, so anything else in the "
                    "message is ignored rather than guessed at._")
        amt = float(m.group(1))
        if amt <= 0:
            return "The amount has to be more than zero."
        self.d["amount"] = amt
        self.step = "account"
        return ("Rate today is *%s* (the desk's band is %s–%s).\n"
                "%s %s = *%s NGN*.\n\n"
                "Which account should I pay? Reply with the number next to it.\n\n%s"
                % (fmt(rate), fmt(band[0]), fmt(band[1]),
                   fmt(amt), self.d["asset"], fmt(amt * rate), self._account_menu()))

    def _step_account(self, t, rate, band):
        accts = self.approved()
        m = re.search(r"\d+", t)
        idx = int(m.group(0)) - 1 if m else -1
        if not (0 <= idx < len(accts)):
            return ("Reply with the number of one of these. A new account "
                    "has to be verified by the desk before I can pay it — "
                    "that is what stops someone else claiming your money.\n\n"
                    + self._account_menu())
        self.d["payout"] = accts[idx]
        return self._open_deal(rate)

    def _step_awaiting_deposit(self, t, rate, band):
        return ("I'm watching for your deposit against *%s*. Reply *CANCEL* to "
                "start again." % self.ref)

    @staticmethod
    def _bullets(items):
        return "\n".join("• *%s*" % i for i in items)

    def _account_menu(self):
        accts = self.approved()
        if not accts:
            return "(no verified accounts yet — the desk has to add one first)"
        return "\n".join("*%d.* %s" % (i + 1, a) for i, a in enumerate(accts))

    def _open_deal(self, rate):
        d = self.desk.open_deal(
            customer=self.wa_id, asset=self.d["asset"], network=self.d["network"],
            amount=self.d["amount"], rate=rate, payout_account=self.d["payout"],
            memo=None, approved_accounts=self.approved())
        if "error" in d:
            self.reset()
            return "I can't open that: %s\n\n%s" % (d["error"], GREETING)
        self.ref = d["reference"]
        self.step = "awaiting_deposit"
        memo = ("\n*Memo / tag:* `%s`\n_Without it the deposit credits nobody._"
                % d["memo"]) if d["memo"] else ""
        return ("Reference *%s*.\n\n"
                "Send *%s %s* on *%s* to:\n\n`%s`%s\n\n"
                "⚠️ *%s only.* Any other network loses the coin.\n\n"
                "I'll pay *%s NGN* to:\n%s\n\n"
                "_That account is fixed to this deal now. If anyone asks you to "
                "change it, or says they are us, it is not us._\n\n"
                "Track it: %s"
                % (d["reference"], fmt(d["amount"]), d["asset"], d["network"],
                   d["depositAddress"], memo, d["network"],
                   fmt(d["naira"]), d["payoutAccount"],
                   "/c/" + d["reference"]))


def fmt(n):
    n = float(n)
    return ("%.0f" % n) if abs(n - round(n)) < 1e-9 else ("%.2f" % n)
