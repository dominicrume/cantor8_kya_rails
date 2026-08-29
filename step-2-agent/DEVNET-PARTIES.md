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
3. TransferPreapproval — SKIPPED, and not needed. Without it a transfer
   arrives as `offer` and the receiver accepts it; `c8lab.accept_transfer`
   handles that, and we do not move coin in the Charge flow yet.
4. Read balance from the ACS — DONE, all five
5. Get Canton Coin — DONE. kya-agent-1 holds 5.0000 Amulet, unlocked and
   spendable, admin DSO. Funded by the Cantor8 team on request.
6. Send a transfer — DONE (the accept that unlocked the holding).

Beyond the six steps:

7. Upload our own DAR — DONE. `POST /v2/packages` with the dar as
   octet-stream. Participant went 907 -> 909 packages. KyaMandate main
   package id `1032e858662a4a9aa61774e8ddad9b7d8e968708897aca55dc90ac5fc150f874`.
8. Run the mandate for real — DONE. Owner proposes, agent accepts, and
   DevNet returns every refusal itself: over-cap, non-allow-listed payee,
   after-revoke, after-expiry, and agent-only Adjust. `python3 agent.py --devnet`.

## Rights we actually hold

`validator-backend@clients` is the user the `hackathon` client maps to; the
token's `sub` says so, and C8_USER does not change that. Of 325 rights
entries, exactly one names a kya party:

    CanActAs  kya-agent-1::12204e94c0...

Reads on the other four work through `CanReadAsAnyParty`. Act-as on
kya-owner-1 was granted with `ParticipantAdmin` so the owner could sign the
mandate into existence. That is the KYA posture stated out loud: the agent
holds act-as on itself and nothing else, and the ledger refused an
agent-only `Adjust` with "missing authorization from owner" even while our
token could act as both.

## Environment

    export C8_BASE=https://api.validator.dev.digik.cantor8.tech/api/ledger
    export C8_IDP=https://auth.dev.digik.cantor8.tech
    export C8_CLIENT_ID=hackathon
    export C8_CLIENT_SECRET=...        # shell only, never committed
    export C8_REGISTRY=https://sv-proxy.dev.digik.cantor8.tech
    export SSL_CERT_FILE=/etc/ssl/cert.pem

## Notes for anyone repeating this

- `c8lab.submit` writes `"userId": sub` into the request body, and binds
  `sub=USER` as a DEFAULT ARGUMENT at import time. Export C8_USER after
  `import c8lab` and it is silently ignored: every command goes out as
  `ledger-api-user`, a LocalNet name, and DevNet answers
  `403 {"cause":"A security-sensitive error occurred"}` which names neither
  the user nor the cause. Set the env before the import AND pass `sub=`
  explicitly. This cost an hour.
- `c8lab.allocate_party` defaults `grant_to="ledger-api-user"`, which does
  not exist on DevNet (404 USER_NOT_FOUND). Pass
  `grant_to="validator-backend@clients"` — NOT `participant_admin`, which
  grants rights to a user the token never acts as, so submits still fail.
- `c8lab.py check` and `c8lab.py holdings <name>` both route through
  `find_party()`, which pulls every local party. Call the library with the
  full party id instead and neither scan happens.
- `c8lab.token()` caches for the life of the process and never refreshes,
  against a 900s expiry. Clear `c8lab._tok` on any retry.
- The venue network drops TLS handshakes under load. Retry 4-8 times with
  backoff; a hang is the network, not your code.
