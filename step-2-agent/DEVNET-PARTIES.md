# DevNet parties for KYA Rails

Allocated on the shared Cantor8 DevNet validator. Party IDs are public
identifiers, not secrets. The credential itself lives in the shell only.

All five share one namespace fingerprint because they are hosted on the
same shared participant node.

| Role in the demo | Party ID |
| --- | --- |
| desk owner (mandate owner) | `kya-owner-1::12204e94c0e449c0efcd270dd1e68259c36471cebef132e5c7dfc2750fe8c9eed77f` |
| the AI agent (spender) | `kya-agent-1::12204e94c0e449c0efcd270dd1e68259c36471cebef132e5c7dfc2750fe8c9eed77f` |
| verified customer (allow-list) | `kya-customer-1::12204e94c0e449c0efcd270dd1e68259c36471cebef132e5c7dfc2750fe8c9eed77f` |
| liquidity partner (allow-list) | `kya-partner-1::12204e94c0e449c0efcd270dd1e68259c36471cebef132e5c7dfc2750fe8c9eed77f` |
| unverified wallet (NOT allow-listed, attack target) | `kya-unverified-1::12204e94c0e449c0efcd270dd1e68259c36471cebef132e5c7dfc2750fe8c9eed77f` |

## Six-step lab status

1. Get a token — DONE
2. Allocate a party — DONE, all five above
3. TransferPreapproval — NOT DONE. Needs the validator's provider party,
   which is not discoverable from the party list (10,000 entries, paginated,
   DSO not surfaced). Without it transfers arrive as `offer` and the receiver
   accepts; `c8lab.accept_transfer` handles that. Not on the critical path.
4. Read balance from the ACS — DONE, all five read 0.00 Amulet
5. Get Canton Coin — BLOCKED, needs the Cantor8 team to fund a party
6. Send a transfer — BLOCKED by step 5

## Environment

    export C8_BASE=https://api.validator.dev.digik.cantor8.tech/api/ledger
    export C8_IDP=https://auth.dev.digik.cantor8.tech
    export C8_CLIENT_ID=hackathon
    export C8_CLIENT_SECRET=...        # shell only, never committed
    export C8_REGISTRY=https://sv-proxy.dev.digik.cantor8.tech
    export SSL_CERT_FILE=/etc/ssl/cert.pem

## Notes for anyone repeating this

- `c8lab.allocate_party` defaults `grant_to="ledger-api-user"`, which does not
  exist on DevNet (404 USER_NOT_FOUND). Pass `grant_to="participant_admin"`.
- It also re-scans every local party (5,784) on each call. Calling
  `POST /v2/parties` directly plus `grant_act_as` is far faster.
- The venue network drops TLS handshakes under repeated load. Retry 3-4 times.
