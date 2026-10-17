# Moving this repository to a Vorem GitHub organisation

*Written 17 October 2026. Every claim marked VERIFIED was read off GitHub's own
docs or measured in this tree today. Everything else is marked as a judgement.*

Short answer: **do it, but not this week, and not before the dinner.** There is
exactly one issue that is expensive and irreversible, and four that are an
afternoon of work.

---

## The one that actually hurts

**GitHub Pages is not redirected.** VERIFIED, GitHub's transfer doc, in these
words:

> *"If the transferred repository contains a GitHub Pages site, then links to
> the Git repository on the Web and through Git activity are redirected.
> However, we don't redirect GitHub Pages associated with the repository."*

The live verifier is at `https://dominicrume.github.io/cantor8_kya_rails/`.
After a transfer it is served from `https://vorem.github.io/cantor8_kya_rails/`
and **the old URL stops working with no redirect**.

That URL is not just in this repo. It is in places you cannot edit:

| Where it is | Can you fix it after? |
|---|---|
| The Cantor8 Dev Hub entry, submitted and approved | **Probably not.** You would have to ask the organisers to re-point it |
| Forum post 9114, your own post, 114 views | Yes, Discourse posts stay editable |
| Forum post 9059 and the OpenZeppelin post | Yes |
| **PyPI `knowyouragenticai-receipts` 1.1.0 metadata** | **No. A published version's metadata is immutable** |
| The CVs and the one-page finding already printed | No. Paper does not redirect |
| 17 absolute Pages URLs inside this tree | Yes, one `sed` |
| 6 of those point at `examples/settlement-refusals.json`, the file the forum post told people to download | Yes in the repo, no in the post history |

**The judgement:** a broken demo link on an approved Dev Hub entry, two days
after placing third, is a worse first impression than a repo under a personal
account. The link is the only thing a stranger clicks.

### What makes it survivable

A custom domain on Pages, set up **before** the transfer. Point
`rails.vorem.io` (or whatever you own) at the Pages site now, change every
reference to the custom domain, let that be the public URL for a few weeks, and
*then* transfer. The custom domain follows the repo. The `github.io` URL is the
thing that breaks, so stop depending on it first.

That is the whole fix, and it is the reason to wait.

---

## The one that is irreversible

VERIFIED, same doc:

> *"If the transferred repository contains an action listed on GitHub
> Marketplace, or had more than 100 clones or more than 100 uses of GitHub
> Actions in the week prior to the transfer, GitHub permanently retires the
> owner name and repository name combination"*

This repo ships `action.yml`, a composite action. The README documents it as:

```
- uses: dominicrume/cantor8_kya_rails@main
```

If that action is listed on Marketplace, `dominicrume/cantor8_kya_rails` is
**permanently retired** on transfer: you can never move back, and anyone whose
workflow pins that path breaks for good with no redirect.

**Check before you transfer, not after.** If it is not on Marketplace and
clones are under 100 a week, which is likely at 0 stars and 0 forks, the name
stays reusable and this is a non-issue. Either way: tag a `v1`, publish the
action under the org afterwards, and change the README's `uses:` line in the
same commit as the move.

---

## The four that are just work

**1. 38 files carry `dominicrume` in a hardcoded URL.** 64 absolute URLs total,
measured today. Twenty of them are `github.com/dominicrume/cantor8_kya_rails`,
which GitHub **does** redirect (VERIFIED: *"All links to the previous
repository location are automatically redirected"*), so those degrade rather
than break. Fix them anyway, in one commit, because a redirect is a thing that
can be deleted and the doc says so:

> *"If you create a new repository or fork at the previous repository location,
> the redirects to the transferred repository will be permanently deleted."*

So never create a repo at the old name afterwards. That is a footgun with your
name on it.

**2. Six URLs are pinned to commit SHAs.** `7b9eeb2d5`, `2c4948ff3`, `c96456f`,
`fbc6392`. SHAs survive a transfer, so these are fine, and that is an argument
for pinning more of them rather than fewer.

**3. CI.** The badge URL changes. Actions secrets *"remain associated after the
transfer"* (VERIFIED), but **verify each one by re-running the workflow** rather
than trusting that sentence, because "associated" is not "working".

**4. The author identity stays.** VERIFIED: *"Git information about commits,
including contributions, is preserved."* Your commits still count toward your
profile, and the CVs' claim about commit history survives. Good.

---

## What you need in hand before you can do it

VERIFIED requirements:

- Admin access on the repo. You have it.
- *"To transfer repositories to an organization, you must have permission to
  create repositories in the receiving organization."* So the Vorem org must
  exist and you must be able to create repos in it.
- *"The target account must not have a repository with the same name, or a fork
  in the same network."*
- A GitHub Free **organisation** keeps Pages and branch protection for public
  repos. VERIFIED, the loss applies to private repos: *"If you transfer a
  private repository to a GitHub Free user or organization account, the
  repository will lose access to features like protected branches and GitHub
  Pages."* **This repo is public, so there is no cost here. Do not make it
  private on a Free org.**

---

## Two things found in the tree while checking

Not about the move, found by the same pass.

**`desk.json` is still tracked**, 715 bytes, and it is desk configuration:
operator name, a cap, a rate band, and counterparty account numbers. The
numbers are fake (`GTB 0123456789 / EXAMPLE NAME`) and `tests/no_real_addresses.py`
passes, so nothing here is spendable. But `CLAUDE.md` says the desk moved out on
2026-09-12 and that desk settings are no longer here. This file contradicts
that, and `tests/mutation_suite.py` reads it, so it cannot just be deleted.
**Decide: rename it to something that says what it is for, or move the fixture
under `tests/`.** Either way the rule and the tree should agree.

**`kya-desk.db`, `-shm` and `-wal` are on disk and untracked**, correctly
gitignored at `.gitignore:28`. Clean, and worth confirming rather than assuming,
because a transferred repo carries its whole history and a database that was
*ever* committed would come with it.

**Secret scan: clean, with a positive control that matched**, so the scan was
reading files and not passing vacuously. Patterns: `ghp_`, `github_pat_`,
`AKIA`, PEM private keys, `xoxb-`, `sk-`. Zero hits across every tracked file.
The control file planted a fake token and a fake AWS key and the same regex
found them.

---

## The order to do it in

1. **Not before Sunday.** A broken demo link is the one thing that cannot be
   explained away in a room.
2. Check whether `action.yml` is listed on Marketplace. That answer decides
   whether the old name is recoverable.
3. Register a domain you control and put it on Pages. Change the 17 Pages URLs
   to it. Push. Confirm the custom domain serves the verifier.
4. Edit the forum posts and the Dev Hub entry to the custom domain. Wait a week.
5. Create the org. Transfer. Fix the 20 `github.com` URLs, the badge, and the
   `uses:` line in one commit.
6. Re-run CI and confirm every secret still works.
7. Never create a repo named `cantor8_kya_rails` under `dominicrume` again.

Step 3 is the whole job. Everything else is a find-and-replace.
