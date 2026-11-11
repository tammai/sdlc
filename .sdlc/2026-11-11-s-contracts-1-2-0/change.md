# Re-vendor contracts 1.2.0 (C3: level 1 needs a source)

## Why

**Request (verbatim, from the maintainer's session):** "re-vendor contracts 1.2.0 into the sdlc repo … Copy them byte-identical (cp); never edit the copy."

product-rebuild PR #4 (merged as aeff427) released contracts 1.2.0: C3's level 1 now needs a SUPPORTED verdict, and an `[inferred]` criterion never reaches it by audit. No field or format changes. rspec carries it from its PR #12; this keeps sdlc's copy in step, since every consumer vendors the same version.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| Copy the 9 changed files byte-identical from product-rebuild aeff427 into `scripts/contracts/v1/` | Editing the copy | The contracts are vendored byte-identical and verified by `vendor-check` (spec 01, Distribution) |
| No code change outside the copy | Updating callers | sdlc emits no contracts version and reads no C3 level rule; nothing outside the copy names 1.1.1 |

## Acceptance criteria

- **AC-001** Given the vendored contracts, when `contracts.py vendor-check` runs, then it prints "matches MANIFEST (contracts 1.2.0)".

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_contracts_vendor.py › test_vendored_version_is_1_2_0 | `python3 -m unittest discover -s tests -t tests -k test_vendored_version_is_1_2_0` |

## Must never break

- `scripts/contracts/v1/` stays byte-identical to product-rebuild's copy at aeff427, and every other test passes unchanged.

## Out of scope

- Re-vendoring into bug-hunter (its own change); a release of sdlc.

## Review

No review ran: no trigger fired. AC-001 red then green; full suite (unittest discover -s tests -t tests) passes on Python 3.10 and 3.15, 498 tests, 4 skipped; vendor-check matches 1.2.0 and scripts/contracts/v1 is byte-identical to product-rebuild aeff427.
