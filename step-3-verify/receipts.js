const RECEIPTS = [
  {
    "n": 1,
    "what": "Pay RiceSupplier for 2 bags",
    "amount": "40.0",
    "payee": "RiceSupplier",
    "rule": "cap 100, spent 40, payee on allow-list",
    "outcome": "ACCEPTED",
    "approved_by": "mandate signed by MarketWoman + VoremAgent",
    "at": "2026-08-29T08:40:27Z",
    "prev": "GENESIS",
    "seal": "c45175d056fde75bcb40485af9039129b1244e8bc9554efd2a3300103d71d558"
  },
  {
    "n": 2,
    "what": "Pay OilSupplier for 5 litres",
    "amount": "35.0",
    "payee": "OilSupplier",
    "rule": "cap 100, spent 75, payee on allow-list",
    "outcome": "ACCEPTED",
    "approved_by": "mandate signed by MarketWoman + VoremAgent",
    "at": "2026-08-29T08:40:27Z",
    "prev": "c45175d056fde75bcb40485af9039129b1244e8bc9554efd2a3300103d71d558",
    "seal": "f097a7f3a2286c8ab394fc72345fc626bb407b77c8654fa558217691b35d533d"
  },
  {
    "n": 3,
    "what": "ATTACK: overspend attempt",
    "amount": "60.0",
    "payee": "RiceSupplier",
    "rule": "cap: charge would exceed the cap",
    "outcome": "REFUSED",
    "approved_by": "mandate signed by MarketWoman + VoremAgent",
    "at": "2026-08-29T08:40:27Z",
    "prev": "f097a7f3a2286c8ab394fc72345fc626bb407b77c8654fa558217691b35d533d",
    "seal": "09ba76aa177f779fbd63b3f0c9c804896c9d0a210c3e33afb8964d56546e5326"
  },
  {
    "n": 4,
    "what": "ATTACK: pay a stranger",
    "amount": "10.0",
    "payee": "StrangerParty",
    "rule": "allowed: payee is not on the allow-list",
    "outcome": "REFUSED",
    "approved_by": "mandate signed by MarketWoman + VoremAgent",
    "at": "2026-08-29T08:40:27Z",
    "prev": "09ba76aa177f779fbd63b3f0c9c804896c9d0a210c3e33afb8964d56546e5326",
    "seal": "5a265c5bc99f84a2ae541e01a71b56e78f8bdad36f753a7e0948b6808d3ef17f"
  },
  {
    "n": 5,
    "what": "ATTACK: charge after revoke",
    "amount": "5.0",
    "payee": "RiceSupplier",
    "rule": "Revoke: owner stopped the mandate",
    "outcome": "REFUSED",
    "approved_by": "owner exercised Revoke",
    "at": "2026-08-29T08:40:27Z",
    "prev": "5a265c5bc99f84a2ae541e01a71b56e78f8bdad36f753a7e0948b6808d3ef17f",
    "seal": "db917a217c6850915f0cc27b08563a6e4a1f383164f9cf826bd5e77a68857fb5"
  }
];