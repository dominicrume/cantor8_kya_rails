Post-To: https://forum.canton.network/t/9114  (Reply, and tick PREDGE's post 6 as the solution while you are there)

Leonid, thank you. My claim was too broad and your reply is the correction.

I said a refusal reaches no monitor. That is only true of one decided in the
submitter's own interpretation. I had no model of the confirmation stage, and
this repository mentioned neither the mediator nor Scan anywhere.

I checked /v0/events rather than take it: rejected verdicts since Splice
0.4.21, and no reject reason field in the schema. So Canton already publishes
that a rejection happened without publishing what was refused. That is the
asymmetry I was designing, and the protocol got there first. It is in the
draft now, crediting you.

One thing I found while checking, in case it is new to you rather than old:
the Scan Bulk Data reference says verdict data is ephemeral and routinely
pruned within the mediator, and that Scan cannot recreate pruned data. That is
the one argument I now have for a contract over an event, and I would not have
gone looking for it without your reply.
