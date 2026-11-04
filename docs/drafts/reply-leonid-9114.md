Post-To: https://forum.canton.network/t/9114  (Reply, and tick PREDGE's post 6 as the solution while you are there)

The use case, since you asked for it.

An agent holds a spending mandate. Its principal has to answer one question to
an auditor: did it ever try to exceed it? Today that answer comes from the
application's own logs, which is the party the question is about.

Your confirmation stage protects the stakeholder who hosts a confirming party.
The principal here usually hosts nothing. They are a counterparty to a
mandate, not a validator operator, so the rejection is logged on a participant
they do not run and cannot read. That is the narrow thing I would want
exposed, and it is narrower than what I claimed: not the reason, just that an
attempt against a named mandate was rejected.

I cannot evaluate the log-alerting path. No participant and no credential, so
I am taking it as read rather than reporting on it.

One question from reading the Scan Bulk Data reference: it says verdict data
is ephemeral and routinely pruned, and that Scan cannot recreate pruned data.
Does that cap how far back such an API could ever answer?
