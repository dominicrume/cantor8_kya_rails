Post-To: https://forum.canton.network/t/9323  (Reply at the bottom)

Georgi, you were right and I had it wrong.

"A guard signatory alone does not gate owner-controlled choices." Controllers
authorize the exercise, and a consuming choice archives its own contract on
the controller's authority, so signatory authority only bites on creates.

My tests missed it because the test wallet had no choices at all. That
minimality was doing the work I was crediting the design with.

There is now a wallet carrying one ordinary owner-controlled choice, and a
test that moves it outside the journal:
testAnOwnerControlledChoiceStillBypassesTheJournal. Deleting the choice turns
it red.

The CIP draft gained a requirement from your reply: audit every choice on the
template and its interfaces. You are in it by name.

You also answered my question. There is no way to do it without distributing
authority outside the actor's control, so segregation of duties is the floor.
