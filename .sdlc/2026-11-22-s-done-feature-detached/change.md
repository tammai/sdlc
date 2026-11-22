# A done workbench feature keeps an app repo until its PR is recorded, on any branch

## Why

A regression of 2026-11-22-s-done-feature-owns-its-branch (319092a), found while checking it before the end-of-push review. It ended a done feature's ownership as soon as the app repo left the feature's branch.

Proof: feature done, no PR recorded, `api` on a detached HEAD, a commit there: `sdlc_review_gate.decide` returns `off`, so the commit gets no security review. Before 319092a it was reviewed. AC-001's test fails on 319092a.

## Decisions

- A done feature owns a branched repo's commits while the repo is on the feature's branch, **or while no PR is recorded for it**. A recorded PR still doesn't end ownership on the branch (the SR7-M4 fix stands). Off the branch with a PR recorded, it ends.
- SR7-L2 (a PR never recorded keeps ownership on any branch) goes back to `.sdlc/todo.md`: closing it needs another signal than the branch name.

## Acceptance criteria

- **AC-001** With the feature done, no PR recorded, and `api` on a detached HEAD, an `api` commit is still reviewed.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_workbench.py › PluginReviewWorkbench.test_a_done_feature_keeps_a_detached_repo_until_its_pr_is_recorded | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_a_done_feature_keeps_a_detached_repo_until_its_pr_is_recorded` |

## Must never break

- `test_app_repo_commits_are_reviewed_for_the_workbench_feature` (a recorded PR doesn't end it on the branch).

## Out of scope

- SR7-L2, reopened as a todo.

## Review

Security review fires (Risk: high); deferred by the user to one review over all of the 2026-11-22 todo fixes at the end of the push.

- **End-of-push review (one pass over all of the 2026-11-22 todo fixes, by area):** scripts and hooks security reviews r1 FAIL, fixed in ddd2c43 and a1552fc; r2 FAIL past the cap, and the user chose to fix the rest (4a0e8f8) and park the read-only guard's lexer as a documented limitation (docs/wiki/Limitations.md). UI review r1 FAIL, fixed in b43026e. What is left is in `.sdlc/todo.md`.
