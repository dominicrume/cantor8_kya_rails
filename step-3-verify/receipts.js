const RECEIPTS = [
  {
    "n": 1,
    "what": "Settle trade 1193, customer leg",
    "amount": "2.0",
    "payee": "VerifiedCustomer",
    "rule": "cap 5.0, spent 2.0, payee on allow-list",
    "outcome": "ACCEPTED",
    "approved_by": "mandate signed by DeskOwner + KyaAgent",
    "at": "2026-08-29T17:00:10Z",
    "prev": "GENESIS",
    "seal": "7a8ae317a43da117ac1a2a146a3724b3adf96fcb24fb815efa4874834acfdb2c"
  },
  {
    "n": 2,
    "what": "Settle trade 1193, liquidity leg",
    "amount": "1.5",
    "payee": "LiquidityPartner",
    "rule": "cap 5.0, spent 3.5, payee on allow-list",
    "outcome": "ACCEPTED",
    "approved_by": "mandate signed by DeskOwner + KyaAgent",
    "at": "2026-08-29T17:00:10Z",
    "prev": "7a8ae317a43da117ac1a2a146a3724b3adf96fcb24fb815efa4874834acfdb2c",
    "seal": "85c0e3eca8b3f8506468aab3015eef573cabc499866addbe2cb1c436f6d5cce4"
  },
  {
    "n": 3,
    "what": "ATTACK: overspend past the cap",
    "amount": "3.0",
    "payee": "VerifiedCustomer",
    "rule": "cap: charge would exceed the cap",
    "outcome": "REFUSED",
    "approved_by": "mandate signed by DeskOwner + KyaAgent",
    "at": "2026-08-29T17:00:10Z",
    "prev": "85c0e3eca8b3f8506468aab3015eef573cabc499866addbe2cb1c436f6d5cce4",
    "seal": "95d4de6a30b9c13cb9069ae2922adc41f8d5f550138c7eb32290cb724a0d3e2f"
  },
  {
    "n": 4,
    "what": "ATTACK: pay an unverified wallet",
    "amount": "1.0",
    "payee": "UnverifiedWallet",
    "rule": "allowed: payee is not on the allow-list",
    "outcome": "REFUSED",
    "approved_by": "mandate signed by DeskOwner + KyaAgent",
    "at": "2026-08-29T17:00:10Z",
    "prev": "95d4de6a30b9c13cb9069ae2922adc41f8d5f550138c7eb32290cb724a0d3e2f",
    "seal": "0ab0f15693f37f35c5985a1f63e49fbd88f23dd97cf6165792a5afc265d67241"
  },
  {
    "n": 5,
    "what": "ATTACK: charge after the mandate expired",
    "amount": "1.0",
    "payee": "VerifiedCustomer",
    "rule": "expiresAt: mandate expired",
    "outcome": "REFUSED",
    "approved_by": "mandate signed by DeskOwner + KyaAgent, clock past expiresAt",
    "at": "2026-08-29T17:00:10Z",
    "prev": "0ab0f15693f37f35c5985a1f63e49fbd88f23dd97cf6165792a5afc265d67241",
    "seal": "09bd6149f49ccc0e160017cc4ce11c87b55d677071b828afa0eaaf8363c3162e"
  },
  {
    "n": 6,
    "what": "ATTACK: charge after revoke",
    "amount": "0.5",
    "payee": "VerifiedCustomer",
    "rule": "Revoke: owner stopped the mandate",
    "outcome": "REFUSED",
    "approved_by": "owner exercised Revoke",
    "at": "2026-08-29T17:00:10Z",
    "prev": "09bd6149f49ccc0e160017cc4ce11c87b55d677071b828afa0eaaf8363c3162e",
    "seal": "683b2cf33be146ce5713c25c8bed38d46f561729be9661653ad166974c714001"
  }
];