# Ask Cantor8 for a DevNet credential

**Status:** not sent. There is no written support channel in anything I can
reach, so the route is yours to pick.

## The environment is still up, checked 14 September

This matters, because asking for a credential to a decommissioned lab wastes
the ask.

| endpoint | |
|---|---|
| `auth.dev.digik.cantor8.tech` | **200** on the OpenID configuration |
| `sv-proxy.dev.digik.cantor8.tech` | **200** |
| `api.validator.dev.digik.cantor8.tech` | 404 at root, which is normal: the API lives at `/api/ledger` |
| `scanner-ledger-read-api...` | 404 at root, health is at a subpath |

Two of these timed out on a first attempt and answered on a second. Transient,
not down. Retry before concluding anything is broken.

## Where to ask

The toolkit says "Ask us for DevNet credentials on the day" and "on DevNet ask
the team", so the channel was the room. Cantor8 is at `cantor8.io` and
[`@cantor8`](https://x.com/cantor8) on X, and the hackathon was run in London
on 29 August with Encode Club, so their programme page is a route too.

Best first: whoever handed you the original credential. A name you already have
beats a contact form.

## What to say

Short, specific, and it gives them a reason to care rather than only a request.

```
Hi, Rume from the Build on Canton hackathon on 29 August.

Could I get a fresh C8_CLIENT_SECRET for the DevNet validator? Mine has
expired.

I want to redeploy kya-rails-mandate as an upgrade of the vetted 1.1.0.
Then run one charge that gets refused.

The point is to check what a blocked payment leaves behind. Right now it
leaves nothing, because a failed assertMsg aborts the transaction. That
is the whole project, and it is the one thing I have never run.

It takes a few minutes and moves no coin. The refusal path is the one
that does not pay.

The work is at github.com/dominicrume/cantor8_kya_rails. It is in the
Canton Developer Hub catalogue. Happy to write up what the run shows.
```

## Why it is worth asking even if they say no

`tools/prove_refusal_on_devnet.py` is written, dry-run tested and in the float.
The moment the secret exists, one command deploys 1.1.1 and either prints a
real `ChargeRefused` contract id or stops and says which of four things went
wrong. Nothing else is blocking it.

Until then, SHORTCUTS.md records that the on-ledger refusal has never been run
against a ledger, and that entry stays.
