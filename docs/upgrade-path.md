# Upgrading the mandate package

Canton checks that a new version of a package is a valid upgrade of the one
already vetted. This document exists because we failed that check, and the
reason was not the one we expected.

## What happened

We added per-period limits to `KyaMandate` — two `Optional` fields plus two
new required ones — and expected the upgrade check to object to the required
fields. It did not get that far:

```
Upgrade checks indicate that kya-mandate v0.0.3 cannot be an upgrade of
kya-mandate v0.0.2. Reason: Data type Desk appears in package that is being
upgraded, but does not appear in the upgrading package.
```

`Desk` was a record in the **test** module, renamed to `Book` during a
cosmetic rewrite of the demo's story. It had nothing to do with the mandate.
But `daml.yaml` had `source: daml`, so the test module was compiled into the
same package and shipped in the DAR — which made a test-only type part of the
deployed package's public surface, and renaming it an on-ledger breaking
change.

**A cosmetic rename inside a deployed package is not cosmetic.**

## The fix, and why it is the right one

Not to restore the name. Test scripts should never have been in the deployed
DAR at all.

`step-1-mandate/` now builds only the mandate. `step-1-mandate/test/` is a
separate package that takes the built DAR as a `data-dependency` and holds
every script. The deployed artefact contains the mandate and nothing else,
verified by `daml damlc inspect-dar` finding zero `KyaTest` references.

The `kya-mandate` lineage stayed poisoned regardless — v0.0.2 is vetted on
DevNet **with** the test types inside it, so no successor can drop them. We
started a clean lineage: `kya-rails-mandate` 1.0.0 (now at 1.1.0), tests excluded from the
first version rather than the third.

## Rules for the next change

1. **Never put test scripts in a package you deploy.** Everything below
   follows from this one.
2. **New fields must be `Optional`.** `periodLimit` and `periodLength` are.
   `periodSpent` and `periodStart` are not, which is why they arrived in a new
   lineage rather than an upgrade — do not repeat that; give any future
   required field a default by making it `Optional` and resolving at use.
3. **Do not rename or remove a data type, field, choice or template** that a
   deployed version contains. Add alongside instead.
4. **Bump the version and run the upload against DevNet before merging.** The
   upgrade check runs at vetting time, not build time — `daml build` will
   happily produce a DAR that Canton refuses.
5. **The error names the offending type.** Read it literally; ours pointed at
   a test record and we assumed it meant the feature we had just added.

## Checking before you deploy

```bash
cd step-1-mandate && daml build
daml damlc inspect-dar .daml/dist/kya-rails-mandate-*.dar | grep -c KyaTest   # must be 0
python3 tests/daml_tests.py                                                   # 100/100
```

Then upload and read the response:

```bash
python3 tests/devnet_upload.py
```

A `NOT_VALID_UPGRADE_PACKAGE` names the type that changed; HTTP 200 means
Canton vetted it as an upgrade of what was already there. The tool refuses to
upload a DAR containing test types at all, which is the mistake that cost us
the first lineage.

## SDK 3.4.11: tested, deliberately not adopted yet (2026-09-06)

3.4.11 was released while 1.1.0 was deployed. It was built and run rather than
assumed about:

| | 3.4.10 | 3.4.11 |
|---|---|---|
| `daml build` | ok | ok |
| attack scripts | 92 / 92 | **92 / 92** |
| choice coverage | 28 of 42 | **30 of 44** |
| package id | `fd3f43a2…f12ab9` | **`48fe2c12…5c2346`** |

The code is compatible. The package id is not the same, and that is the whole
decision: the DAR vetted on DevNet as an upgrade of 1.0.0 is `fd3f43a2…`.
Rebuilding on 3.4.11 produces a *different package* wearing the *same*
name and version, which is precisely what versioning exists to prevent.

So the upgrade is not a one-line edit to `daml.yaml`. Done properly it is:

1. bump to **1.1.1** — a new package id needs a new version, or `1.1.0` means
   two different things depending on who built it;
2. rebuild, upload and vet on DevNet;
3. confirm the upgrade check still passes against 1.1.0;
4. update the Developer Hub entry **with a link to the release**, which their
   contributing guide asks for on any SDK-version change;
5. update every doc that cites 1.1.0.

Held for now, on evidence rather than inertia: the Hub's stated rule is that a
tool more than **one major version** behind may be marked outdated. One patch
behind is not that, and `docs/dev-hub-entry.json` states 3.4.10, which is true.
Shipping a false version number to avoid looking stale would be the worse
trade.
