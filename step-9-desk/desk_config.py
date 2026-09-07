#!/usr/bin/env python3
"""The desk's own settings, so it stops being a demo and starts being yours.

Everything a desk needs to be ITS desk was hardcoded: a rate of 1250, a band of
1000-1500, a cap of 5, an allow-list of two role names, and twenty-six lines of
Chidi and Blessing. That is correct for a demo and useless for an operator, who
has different counterparties, a different rate, and real money.

Two rules shape this file, and the second is the one that matters.

**A desk that cannot understand its own settings must not start.** Every field
is checked, and anything ambiguous is a refusal with the field named, not a
default quietly substituted. A desk that starts on a half-understood config is
worse than one that will not start, because it looks like it is working.

**Configuration parameterises the fences. It does not become them.** The cap,
the period limit and the allow-list are read here and handed to `open_mandate`,
where they become assertions in a Daml choice body. Nothing in this file
decides whether a payment is allowed. If it ever does, the whole argument of
this project is gone -- see THE-RULES.md.

    python3 step-9-desk/desk_config.py            explain the current config
    python3 step-9-desk/desk_config.py --example  print a starting file

The file is `desk.json` beside the repository, or wherever KYA_DESK points.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PATH = os.path.join(HERE, "..", "desk.json")

# A desk with no config is not a desk with sensible defaults. It is a desk that
# has not been set up, and the safe reading of "not set up" is "may pay nobody".
FALLBACK = {
    "desk": {"name": "Unconfigured desk", "operator": "unknown"},
    "money": {"cap": 0.0, "period_limit": None, "period_seconds": None,
              "rate": 0.0, "band": [0.0, 0.0]},
    "counterparties": [],
}


class BadConfig(Exception):
    """The settings file cannot be acted on. Says which field, and why."""


def _need(obj, key, kinds, where):
    if key not in obj:
        raise BadConfig("%s.%s is missing" % (where, key))
    value = obj[key]
    # In Python a bool IS an int, so isinstance(True, (int, float)) is True and
    # float(True) is 1.0. Without this, `"cap": true` becomes a cap of one and
    # the desk starts, having silently invented a limit nobody typed. The first
    # version of this guard read `float not in kinds`, which is exactly
    # backwards and let every boolean through.
    if isinstance(value, bool) and bool not in kinds:
        raise BadConfig("%s.%s must not be true/false" % (where, key))
    if not isinstance(value, kinds):
        raise BadConfig("%s.%s must be %s, not %s"
                        % (where, key, " or ".join(k.__name__ for k in kinds),
                           type(value).__name__))
    return value


def _money(cfg):
    m = _need(cfg, "money", (dict,), "config")
    cap = float(_need(m, "cap", (int, float), "money"))
    if cap <= 0:
        raise BadConfig("money.cap must be greater than zero -- a desk with a "
                        "cap of nothing cannot pay anyone, which is probably "
                        "not what you meant")
    rate = float(_need(m, "rate", (int, float), "money"))
    band = _need(m, "band", (list,), "money")
    if len(band) != 2:
        raise BadConfig("money.band must be exactly [low, high]")
    low, high = float(band[0]), float(band[1])
    if not low < high:
        raise BadConfig("money.band low (%s) must be below high (%s)" % (low, high))
    if not low <= rate <= high:
        raise BadConfig("money.rate %s sits outside its own band [%s, %s]. "
                        "A desk that opens outside its band refuses its first "
                        "quote." % (rate, low, high))
    return {"cap": cap, "rate": rate, "band": [low, high],
            "period_limit": _optional_limit(m, cap),
            "period_seconds": _optional_seconds(m)}


def _optional_limit(m, cap):
    value = m.get("period_limit")
    if value is None:
        return None
    limit = float(value)
    if limit <= 0:
        raise BadConfig("money.period_limit must be above zero, or absent")
    if limit > cap:
        raise BadConfig("money.period_limit (%s) is above money.cap (%s), so it "
                        "can never refuse anything the cap has not already "
                        "refused. Remove it, or lower it." % (limit, cap))
    return limit


def _optional_seconds(m):
    value = m.get("period_seconds")
    if value is None:
        return None
    seconds = int(value)
    if seconds <= 0:
        raise BadConfig("money.period_seconds must be above zero, or absent")
    return seconds


def _counterparties(cfg):
    rows = _need(cfg, "counterparties", (list,), "config")
    seen, out = set(), []
    for i, row in enumerate(rows):
        where = "counterparties[%d]" % i
        if not isinstance(row, dict):
            raise BadConfig("%s must be an object" % where)
        cid = _need(row, "id", (str,), where).strip()
        if not cid:
            raise BadConfig("%s.id cannot be empty" % where)
        if cid in seen:
            raise BadConfig("%s.id %r appears twice -- two counterparties with "
                            "one id means a payout could be attributed to "
                            "either" % (where, cid))
        seen.add(cid)
        out.append({
            "id": cid,
            "name": _need(row, "name", (str,), where),
            "account": _need(row, "account", (str,), where),
            "allowed": bool(row.get("allowed", False)),
        })
    return out


def found():
    """Where the operator is standing first, then beside the repository.

    The single-file build runs from any directory, and a desk.json sitting next
    to it is unmistakably the one meant. Resolving only a path relative to this
    module found nothing and reported "Unconfigured desk" with the file in
    plain sight.
    """
    for candidate in (os.path.join(os.getcwd(), "desk.json"), DEFAULT_PATH):
        if os.path.exists(candidate):
            return candidate
    return None


def load(path=None):
    """The desk's settings, fully checked, or BadConfig naming the field."""
    path = path or os.environ.get("KYA_DESK") or found()
    if path is None or not os.path.exists(path):
        return dict(FALLBACK, path=None, configured=False)
    try:
        raw = json.load(open(path))
    except ValueError as e:
        raise BadConfig("%s is not valid JSON: %s" % (path, e)) from e
    if not isinstance(raw, dict):
        raise BadConfig("%s must contain a JSON object" % path)
    desk = _need(raw, "desk", (dict,), "config")
    return {
        "desk": {"name": _need(desk, "name", (str,), "desk"),
                 "operator": _need(desk, "operator", (str,), "desk")},
        "money": _money(raw),
        "counterparties": _counterparties(raw),
        "path": path,
        "configured": True,
    }


def allow_list(cfg):
    """The ids the mandate may pay. Handed to open_mandate, enforced in Daml."""
    return [c["id"] for c in cfg["counterparties"] if c["allowed"]]


def describe(cfg):
    """What an operator needs to read before the first real payout."""
    lines = []
    if not cfg["configured"]:
        # The command differs depending on how the desk was started, and
        # telling somebody to run a path they do not have is worse than saying
        # nothing. sys.argv[0] is the thing they actually typed.
        how = os.path.basename(sys.argv[0]) or "desk_config.py"
        lines.append("NO desk.json -- running unconfigured. Cap is 0, so every")
        lines.append("payment refuses. Write one:")
        lines.append("    python3 %s --example > desk.json" % how)
        return lines
    m, allowed = cfg["money"], allow_list(cfg)
    lines.append("desk:     %s (operator: %s)" % (cfg["desk"]["name"], cfg["desk"]["operator"]))
    lines.append("cap:      %.2f total" % m["cap"])
    if m["period_limit"]:
        lines.append("period:   %.2f per %s seconds" % (m["period_limit"], m["period_seconds"]))
    else:
        lines.append("period:   no per-period limit -- the total cap is the only ceiling")
    lines.append("rate:     %.2f, band [%.2f, %.2f]" % (m["rate"], m["band"][0], m["band"][1]))
    lines.append("may pay:  %s" % (", ".join(allowed) if allowed else
                                   "NOBODY -- no counterparty has allowed: true"))
    refused = [c["id"] for c in cfg["counterparties"] if not c["allowed"]]
    if refused:
        lines.append("known but not allowed: %s" % ", ".join(refused))
    return lines


EXAMPLE = {
    "desk": {"name": "VOREM Desk", "operator": "Rume Dominic"},
    "money": {
        "cap": 5.0,
        "period_limit": 2.0,
        "period_seconds": 86400,
        "rate": 1250.0,
        "band": [1000.0, 1500.0],
    },
    "counterparties": [
        {"id": "customer", "name": "Verified customer payouts",
         "account": "GTB 0123456789 / EXAMPLE NAME", "allowed": True},
        {"id": "partner", "name": "Settlement partner",
         "account": "UBA 2233445566 / EXAMPLE PARTNER", "allowed": True},
        {"id": "unverified", "name": "Unverified account, kept on file",
         "account": "OPAY 9999999999 / UNKNOWN", "allowed": False},
    ],
}


def main(argv):
    if "--example" in argv:
        print(json.dumps(EXAMPLE, indent=2))
        return 0
    try:
        cfg = load()
    except BadConfig as e:
        print("The desk cannot read its settings.")
        print(" ", e)
        return 2
    print("settings: %s" % (cfg["path"] or "none found"))
    for line in describe(cfg):
        print("  " + line)
    print()
    print("The cap, the period limit and the allow-list above are handed to the")
    print("mandate, where they become assertions in a Daml choice body. Nothing")
    print("in this file decides whether a payment is allowed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
