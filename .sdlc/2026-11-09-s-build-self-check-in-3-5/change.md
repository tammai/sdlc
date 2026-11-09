# sdlc 3.5.0-rc.7: Build writes against what Review checks

## Why

**Request (verbatim, from the Orca coordinator):** Add the user's own branch feat/build-self-check (4a0e657, 1552886: "Build writes against what Review checks") to the 3.5.0 release, as approved after an audit: 1. Merge feat/build-self-check into the release branch (a merge commit, keeping its two commits). The only conflict is CHANGELOG.md: move its 'Unreleased' entry under the 3.5.0 section. 2. One wording change in skills/orchestrator/references/flow.md's new Build bullet: replace "Each hit gets a test, like an AC." with "A hit that the spec's failure modes or must-never-break lines cover gets a test; the rest are fixed in passing." (the user's minimal-testing rule). 3. The 3.5.0 CHANGELOG says plainly: no standalone behaviour change except this one (the builder sees the recurring-defects list and the Build checklist on every track; small token cost per run; effect on review findings not measured yet). 4. Run the full suite and confirm 3.4.0's test files are still untouched apart from test_brief.py's added assertion. Version 3.5.0-rc.7 in all manifests, local annotated tag sdlc--v3.5.0-rc.7, nothing pushed.

The 3.5 parts' round-1 review findings were mostly classes the plugin's recurring-defects list already names; the builder never saw that list. The branch puts it in the brief and in Build's checklist. The wording change keeps the user's minimal-testing rule: not every hit earns its own test.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| A merge commit (979361f) of the two branch commits, then one commit for the wording, the CHANGELOG note and the version | squashing or cherry-picking | the request keeps the two commits |
| The Unreleased entry becomes `### Changed (every repo)` in the rc.7 section, and the intro says "no standalone behaviour change except one" | a separate 3.5.0 heading | there is one 3.5.0 section; the release notes stay in one place |
| Committed on the release branch, not through `ship.py`'s branch, push and PR | `ship.py` | the request: nothing pushed, the work lands on the release branch |

**Proposals not asked for:** None

## Acceptance criteria

- **AC-001** Given a repo, when `brief.py` runs, then its output holds the plugin's recurring-defects list under `===== plugin recurring defects =====`.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_brief.py › test_prints_defines_inputs_and_cuts_long_files | `py -3.10 -m unittest discover -s tests -t tests -p test_brief.py` |

## Must never break

- 3.4.0's test files stay untouched apart from the one assertion added to `tests/test_brief.py`; the full suite passes on Python 3.10.

## Out of scope

- Measuring the effect on review findings; pushing, the PR and the release.

## Review

- Fired: none (risk low; no sensitive, migration or UI path; Public Surface none), so no review ran and the 2-round cap was not reached. The branch itself was audited and approved before this change.
- Verified: full suite on Python 3.10, 484 tests OK (4 skipped); `git diff --name-status sdlc--v3.4.0 HEAD -- tests`: only `tests/test_brief.py` modified (the one added assertion), the rest added files.
- Fixed: nothing. Lessons filed: none.
