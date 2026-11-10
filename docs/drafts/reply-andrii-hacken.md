Post-To: LinkedIn direct message to Andrii Semibratov (Partnerships & Marketing Manager, Hacken)
How: open the conversation, paste into the message box at the bottom, press Send.

Honest answer first: pre-revenue, so not an audit buyer yet.

Stage is a Daml specification with three implementations agreeing on 20
conformance vectors, and 32 fences where breaking any one of them turns a named
test red. Next milestone is running it on a real ledger, blocked on a DevNet
credential.

The part that may interest you. I built the mutation runner to emit its findings
as a hash-chained record, so a client can check afterwards that no finding was
softened or removed, including by the auditor. Ran it over three OpenZeppelin
Canton packages in September:

https://github.com/dominicrume/cantor8_kya_rails/blob/main/docs/findings-openzeppelin.md

How does Hacken handle that part, where the client has to trust the report?
