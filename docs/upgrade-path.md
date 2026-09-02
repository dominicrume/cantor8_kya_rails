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
started a clean lineage: `kya-rails-mandate` 1.0.0, tests excluded from the
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
cd test && daml build && daml test                                            # 82/82
```

Then upload and read the response:

```bash
python3 tests/devnet_upload.py
```

A `NOT_VALID_UPGRADE_PACKAGE` names the type that changed; HTTP 200 means
Canton vetted it as an upgrade of what was already there. The tool refuses to
upload a DAR containing test types at all, which is the mistake that cost us
the first lineage.
