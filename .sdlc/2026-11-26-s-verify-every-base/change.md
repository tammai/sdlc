# Verify reports every Base: it can't use

## Why

**Request (verbatim):** "merge then continue", taking the next todo item: "Verify reports only the first `Base:` it can't resolve (the feature's or an app repo's) and skips the root's drift meanwhile, so several missing bases take one run each."

**Proof:** `drift()` raises on the first repo whose base is missing or no longer behind HEAD, so a workbench with the root's `Base:` and two app repos' bases all broken reports one, and fixing them takes three runs (`test_every_base_drift_cant_use_is_reported_in_one_run` fails: `DriftUnchecked` has no `problems`).

**Root cause:** the base checks in `drift()` raise inside the loop over repos, and `DriftUnchecked` carries one problem.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| `drift()` checks every repo's base, then raises one `DriftUnchecked` holding each problem (`problems`; `problem` stays the first) | raising on the first | each fix needs a run otherwise |
| A git error in one repo's check (`drift_unchecked`) is collected like a base problem | stopping on it | one repo's git failing says nothing about the others' bases |
| The root's drift still waits while any base is broken | diffing the repos that resolve | verify fails either way; a partial drift list would change once the bases are fixed, and collect scans every branched repo together |

## Acceptance criteria

- **AC-001** `drift()` reports the root's `Base:` and each app repo's base it can't use, missing or no longer behind HEAD, in one run.
- **AC-002** `full()` records each of those problems as a failure.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_workbench.py › PluginReviewWorkbench.test_every_base_drift_cant_use_is_reported_in_one_run | `python3 -m unittest discover -s tests -t tests -p test_workbench.py -k test_every_base_drift_cant_use_is_reported_in_one_run` |
| AC-002 | tests/test_workbench.py › PluginReviewWorkbench.test_verify_lists_every_base_problem_as_a_failure | `python3 -m unittest discover -s tests -t tests -p test_workbench.py -k test_verify_lists_every_base_problem_as_a_failure` |

## Must never break

- A single missing or rewritten `Base:` still fails as `base_missing` or `base_not_ancestor` with its fix (`tests/test_verify.py`, `test_an_app_repos_base_missing_from_its_clone_fails_drift`, `test_an_app_repos_base_no_longer_behind_its_head_fails_drift`).

## Out of scope

- Counting the root's drift while an app repo's base is broken (see Decisions).

## Review

No review ran: no trigger fired.
