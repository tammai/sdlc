# Re-vendor contracts 1.3.0 (check_lock rejects an [inferred] criterion at level 1)

## Why

**Request (verbatim, from the maintainer's session):** "copy contracts 1.3.0 into the sdlc repo … Copy byte-identical."

product-rebuild PR #6 (merged as f4ac06e) released contracts 1.3.0: `check_lock` now reports an error for a criterion tagged `inferred` at level 1, making C3's 1.2.0 rule mechanical, with a new invalid fixture `fixtures/lock/invalid/inferred-at-level-1.json`. This keeps sdlc's copy in step with every other consumer.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| Copy the 9 changed files and the new fixture byte-identical from product-rebuild f4ac06e into `scripts/contracts/v1/` | Editing the copy | The contracts are vendored byte-identical and verified by `vendor-check` (spec 01, Distribution) |
| No code change outside the copy | Guarding sdlc's lock handling | sdlc never writes a criteria lock or a level: `spec_lock.py`, `verify.py` and `scaffold.py` only read or detect `criteria.lock.json`, and nothing outside the copy mentions `inferred` or levels |

## Acceptance criteria

- **AC-001** Given the vendored contracts, when `contracts.py vendor-check` runs, then it prints "matches MANIFEST (contracts 1.3.0)".

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_contracts_vendor.py › test_vendored_version_is_1_3_0 | `python3 -m unittest discover -s tests -t tests -k test_vendored_version_is_1_3_0` |

## Must never break

- `scripts/contracts/v1/` stays byte-identical to product-rebuild's copy at f4ac06e, and every other test passes unchanged.

## Out of scope

- Re-vendoring into rspec and bug-hunter (their own changes); a release of sdlc.

## Review

No review ran: no trigger fired. AC-001 red then green; full suite (unittest discover -s tests -t tests) OK, 4 skipped; vendor-check matches 1.3.0 and scripts/contracts/v1 is byte-identical to product-rebuild f4ac06e.
