const RECEIPTS = [
  {
    "n": 1,
    "what": "Settle trade 1193, customer leg",
    "amount": "2.0",
    "payee": "customer",
    "rule": "cap and allow-list satisfied, committed on DevNet",
    "outcome": "ACCEPTED",
    "approved_by": "mandate signed by DeskOwner + KyaAgent",
    "at": "2026-08-29T17:35:35Z",
    "prev": "GENESIS",
    "seal": "e2c5382eab835802febe75c7a52d9dda58335affb5588ff3a280bbd199e0758c"
  },
  {
    "n": 2,
    "what": "Settle trade 1193, liquidity leg",
    "amount": "1.5",
    "payee": "partner",
    "rule": "cap and allow-list satisfied, committed on DevNet",
    "outcome": "ACCEPTED",
    "approved_by": "mandate signed by DeskOwner + KyaAgent",
    "at": "2026-08-29T17:35:41Z",
    "prev": "e2c5382eab835802febe75c7a52d9dda58335affb5588ff3a280bbd199e0758c",
    "seal": "29d5303855de3186cf6c7acf5f5e59d066aa3a48089d1cdb24286465202d9836"
  },
  {
    "n": 3,
    "what": "ATTACK: overspend past the cap",
    "amount": "3.0",
    "payee": "customer",
    "rule": "charge would exceed the cap",
    "outcome": "REFUSED",
    "approved_by": "mandate signed by DeskOwner + KyaAgent",
    "at": "2026-08-29T17:35:41Z",
    "prev": "29d5303855de3186cf6c7acf5f5e59d066aa3a48089d1cdb24286465202d9836",
    "seal": "c2196d97e4b56ece031f7f7d20b3a8a43d7e206b5f3c9e7b2b5776bb0cf88cc1"
  },
  {
    "n": 4,
    "what": "ATTACK: pay an unverified wallet",
    "amount": "1.0",
    "payee": "unverified",
    "rule": "payee is not on the allow-list",
    "outcome": "REFUSED",
    "approved_by": "mandate signed by DeskOwner + KyaAgent",
    "at": "2026-08-29T17:35:41Z",
    "prev": "c2196d97e4b56ece031f7f7d20b3a8a43d7e206b5f3c9e7b2b5776bb0cf88cc1",
    "seal": "abadc3fd2cf242b5c92f129f7b773abbbaa69c0d151af9624ea7f783c4864c8b"
  },
  {
    "n": 5,
    "what": "ATTACK: charge after the mandate expired",
    "amount": "1.0",
    "payee": "customer",
    "rule": "mandate expired",
    "outcome": "REFUSED",
    "approved_by": "mandate signed by DeskOwner + KyaAgent, clock past expiresAt",
    "at": "2026-08-29T17:36:08Z",
    "prev": "abadc3fd2cf242b5c92f129f7b773abbbaa69c0d151af9624ea7f783c4864c8b",
    "seal": "bbfbd7e606d628581bb08af60acbdf73dd32c0a3e61a80228c69f6a6408a65f8"
  },
  {
    "n": 6,
    "what": "ATTACK: charge after revoke",
    "amount": "0.5",
    "payee": "customer",
    "rule": "Revoke: mandate no longer active on the ledger",
    "outcome": "REFUSED",
    "approved_by": "owner exercised Revoke",
    "at": "2026-08-29T17:38:19Z",
    "prev": "bbfbd7e606d628581bb08af60acbdf73dd32c0a3e61a80228c69f6a6408a65f8",
    "seal": "2e81435a3292b35a7251f1aaea74f0be7c3d5b0766153e40f1960bce2de3784b"
  }
];