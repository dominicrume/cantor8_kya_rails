#!/usr/bin/env python3
"""Meta WhatsApp Cloud API webhook -> the desk bot.

This is the door the customer's own WhatsApp comes through, so it is the door
most worth attacking. Everything below is a refusal or the reason for one.

Meta's scheme, from their Cloud API documentation:
  - a one-time GET carrying hub.mode / hub.verify_token / hub.challenge, which
    you answer by echoing the challenge if the token matches
  - every POST carries `X-Hub-Signature-256: sha256=<hex>`, an HMAC-SHA256 of
    the RAW request body using the app secret
  - deliveries retry, so a message id may arrive more than once
  - `value.messages` are inbound messages; `value.statuses` are delivery
    receipts for messages WE sent, and are not customer input

Three things that are easy to get wrong and expensive here:

  1. The signature covers the bytes on the wire. Parsing the JSON and
     re-serialising it before verifying means you verify a body nobody sent,
     and any difference in key order, spacing or unicode escaping breaks it.
     `handle` therefore takes raw bytes and verifies before parsing.

  2. A signature does not expire. A body captured once stays valid forever
     unless something bounds it, so each message's own timestamp is checked
     against a window. Retries of a message already seen are handled by the
     id, not by re-running it.

  3. `contacts[].profile.name` is a display name the sender sets themselves.
     It is never used to identify anyone. The conversation key is the `from`
     number inside the signed body.

What is NOT here: sending the reply back. That needs a Graph API call with an
access token this repository does not have, so `send` is a recording stub and
is labelled MOCKED wherever it appears. The reply text is returned instead.

Stdlib only.
"""
import hmac, hashlib, json, time

MAX_BODY = 256 * 1024      # a webhook body this large is not a chat message
MAX_TEXT = 4096            # WhatsApp's own limit; anything longer is not real
DEFAULT_WINDOW = 300       # seconds a signed delivery stays acceptable


class Refused(Exception):
    """Understood, and not acted on. Answered 2xx so Meta stops retrying."""


class MetaAdapter:
    def __init__(self, rail, app_secret, verify_token, phone_number_id,
                 window=DEFAULT_WINDOW, send=None, now=time.time):
        if not app_secret:
            raise ValueError("an app secret is required; without one anyone "
                             "who finds the URL can talk to the desk")
        if not verify_token:
            raise ValueError("a verify token is required")
        if not phone_number_id:
            raise ValueError("a phone_number_id is required; without it this "
                             "endpoint accepts traffic for any business account")
        self.rail = rail
        self._secret = app_secret.encode() if isinstance(app_secret, str) else app_secret
        self._verify_token = str(verify_token)
        self.phone_number_id = str(phone_number_id)
        self.window = window
        self.now = now
        self.send = send or self._mocked_send
        self.seen = set()      # wamid, Meta's own idempotency key
        self.log = []          # every delivery, accepted or refused
        self.sent = []         # MOCKED outbound, for the demo and the tests

    # -- MOCKED ------------------------------------------------------------
    def _mocked_send(self, to, text):
        """MOCKED: records what would be sent. No Graph API call is made."""
        self.sent.append({"to": to, "text": text, "at": self.now()})

    # -- the one-time verification handshake -------------------------------
    def verify(self, params):
        """Meta's GET challenge. Returns (status, body_text).

        The token is compared in constant time like any other secret, and the
        challenge is echoed only on a match -- an endpoint that echoes what it
        is sent is a reflector for anyone who finds it.
        """
        if params.get("hub.mode") != "subscribe":
            return 400, "unexpected hub.mode"
        if not hmac.compare_digest(str(params.get("hub.verify_token", "")),
                                   self._verify_token):
            return 403, "verification token does not match"
        challenge = str(params.get("hub.challenge", ""))
        if not challenge.isdigit():
            # Meta always sends an integer. Anything else is someone probing
            # for a reflection.
            return 400, "challenge is not a number"
        return 200, challenge

    # -- authentication ----------------------------------------------------
    def _authenticate(self, headers, raw):
        header = (headers.get("X-Hub-Signature-256")
                  or headers.get("x-hub-signature-256") or "")
        if not header.startswith("sha256="):
            raise Refused("missing or malformed X-Hub-Signature-256")
        expected = hmac.new(self._secret, raw, hashlib.sha256).hexdigest()
        # Constant time: a plain == leaks the correct digest a byte at a time.
        if not hmac.compare_digest(header[len("sha256="):], expected):
            raise Refused("signature does not match the body")

    def handle(self, headers, raw):
        """One delivery. Returns (http_status, response_dict).

        Never raises to the caller. 2xx once authenticated even when refused:
        Meta retries on non-2xx, and retrying something we have understood and
        rejected achieves nothing but more chances to race.
        """
        entry = {"at": self.now(), "outcome": None, "why": None}
        if not isinstance(raw, (bytes, bytearray)):
            raise TypeError("handle needs the raw bytes; the signature covers "
                            "the bytes on the wire, not a re-serialised parse")
        if len(raw) > MAX_BODY:
            entry.update(outcome="REJECTED", why="body too large")
            self.log.append(entry)
            return 413, {"error": "body too large"}
        try:
            self._authenticate(headers, raw)
        except Refused as e:
            entry.update(outcome="REJECTED", why=str(e))
            self.log.append(entry)
            return 401, {"error": "unauthorised"}     # no detail about why
        return self._dispatch(raw, entry)

    def _dispatch(self, raw, entry):
        try:
            replies = self._apply(raw, entry)
        except Refused as e:
            entry.update(outcome="REFUSED", why=str(e))
            self.log.append(entry)
            return 200, {"received": True, "acted": False, "reason": str(e)}
        entry.update(outcome="HANDLED", why="%d message(s)" % len(replies))
        self.log.append(entry)
        return 200, {"received": True, "acted": bool(replies), "replies": replies}

    # -- authenticated from here on ----------------------------------------
    def _apply(self, raw, entry):
        try:
            body = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as e:
            raise Refused("body is not valid JSON: %s" % e)
        if not isinstance(body, dict):
            raise Refused("body is not an object")
        if body.get("object") != "whatsapp_business_account":
            raise Refused("not a WhatsApp business account event")
        replies = []
        for value in self._values(body):
            self._check_account(value)
            replies.extend(self._messages(value, entry))
        if not replies:
            raise Refused("no inbound message in this delivery")
        return replies

    @staticmethod
    def _listing(obj, key):
        """A list at obj[key], however absent, null or wrong-typed the path is.

        Meta's shape is nested four deep and every level is attacker-supplied
        once the signature is stripped off. `entry` arriving as a string would
        otherwise iterate its characters and crash on the next .get.
        """
        if not isinstance(obj, dict):
            return []
        value = obj.get(key)
        return value if isinstance(value, list) else []

    def _values(self, body):
        """The `value` block of every messages change in this delivery."""
        for item in self._listing(body, "entry"):
            for change in self._listing(item, "changes"):
                if isinstance(change, dict) and change.get("field") == "messages":
                    yield change.get("value") or {}

    def _check_account(self, value):
        """Ours, or someone else's business account pointed at our URL?"""
        got = str((value.get("metadata") or {}).get("phone_number_id", ""))
        if not hmac.compare_digest(got, self.phone_number_id):
            raise Refused("delivery is for phone_number_id %r, not ours" % got)

    def _messages(self, value, entry):
        # `statuses` are receipts for messages we sent. Treating one as
        # customer input would let a delivery report drive the conversation.
        if value.get("statuses") and not value.get("messages"):
            raise Refused("delivery status callback, not a customer message")
        out = []
        for msg in self._listing(value, "messages"):
            text = self._gate(msg or {}, entry)
            if text is None:
                continue
            reply = self.rail.on_message(msg["from"], text)
            self.send(msg["from"], reply)       # MOCKED
            out.append({"to": msg["from"], "reply": reply})
        return out

    def _gate(self, msg, entry):
        """Every reason not to hand this message to the bot. None = skip it."""
        wamid = msg.get("id")
        if not wamid:
            raise Refused("message has no id, so it cannot be deduplicated")
        entry["wamid"] = wamid
        if wamid in self.seen:
            raise Refused("duplicate delivery of %s" % wamid)
        if not msg.get("from"):
            raise Refused("message has no sender")
        self._check_fresh(msg, wamid)
        self.seen.add(wamid)
        return self._text_of(msg)

    def _check_fresh(self, msg, wamid):
        """A signature never expires on its own; this is what bounds it."""
        try:
            sent_at = int(msg.get("timestamp"))
        except (TypeError, ValueError):
            raise Refused("message has no usable timestamp")
        age = self.now() - sent_at
        if age > self.window:
            self.seen.add(wamid)
            raise Refused("message is %ds old, outside the %ds window"
                          % (age, self.window))
        if age < -60:
            self.seen.add(wamid)
            raise Refused("message is dated %ds in the future" % -age)

    def _text_of(self, msg):
        """Text only. Anything else gets an honest answer, not a crash.

        Note what is NOT read here: `contacts[].profile.name` is a display
        name the sender chooses, and no branch in this file reads it.
        """
        kind = msg.get("type")
        if kind != "text":
            self.send(msg["from"],                                  # MOCKED
                      "I can only read text messages. Please type your request.")
            return None
        text = (msg.get("text") or {}).get("body")
        if not isinstance(text, str) or not text.strip():
            return None
        if len(text) > MAX_TEXT:
            raise Refused("message text is %d characters; refusing to parse it"
                          % len(text))
        return text
