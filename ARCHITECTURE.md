# Architecture
User story: a market woman gives an AI agent a note: spend at most 100 CC,
only with these two suppliers, until Sunday. The agent trades. Every action,
allowed or refused, becomes a sealed receipt anyone can check.

  [chat demo UI]        [agent.py]              [Canton ledger]
  scripted customer --> reads mandate,   -->    KyaMandate.daml
  conversation          attempts charges        cap / allow-list / expiry
                          |                     enforced IN THE CHOICE BODY
                          v
                      kya_chain.py
                      stamp: what, when, rule, who
                      seal: sha256(canonical + prev seal)
                          |
                          v
                      receipts.js  -->  verifier.html
                                        green chain, tamper button, red cascade

Ledger targets, in order of demo preference:
1. Venue shared DevNet via ~/hackathon-toolkit/c8lab.py (real transfers)
2. LocalNet in Docker (downloaded at home)
3. MockLedger inside agent.py, same assertions as the Daml, clearly labelled MOCKED.
The receipts and verifier work identically in all three. The demo can NEVER be blocked by wifi.
