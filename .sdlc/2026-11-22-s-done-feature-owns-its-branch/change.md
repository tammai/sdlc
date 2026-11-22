# A done workbench feature owns an app repo's commits while the repo is on its branch

## Why

From `.sdlc/todo.md`: "A fake `state.py pr <feature> <repo> <url>` during Ship turns an app repo's commit review off (only the URL's shape is checked); a done feature whose PR is never recorded owns that repo's commits forever (security-r7 SR7-M4, SR7-L2)".

Proof: in a workbench, with the feature done and `api` on its feature branch, `state.py pr feat api https://example.com/api/pull/1` makes `sdlc_review_gate.decide` return `off` for an `api` commit (AC-001's test fails). The other half: with no PR recorded, the done feature keeps owning `api` whatever branch it's on. Root cause: `_workbench_feature` ends a done feature's ownership on a recorded PR. Anyone can write that record, and it says nothing about where the commit lands.

## Decisions

- **A done feature owns a branched repo's commits while that repo is on the branch the feature made for it** (`## Repos`: `branch <name>`). That covers Ship's commits and a CI fix after the PR. A recorded PR no longer matters to ownership.
- Off that branch (merged, the next task), the done feature doesn't own the repo. With nothing else owning it, the gate is off as before, outside any feature.
- Ruled out: checking the recorded PR with `gh`. A hook doesn't call the network, and the branch already answers the question.

## Acceptance criteria

- **AC-001** A recorded PR doesn't turn off the review of the done feature's app repo commits while the repo is on the feature's branch.
- **AC-002** Off that branch, the done feature no longer owns the repo's commits.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_workbench.py › PluginReviewWorkbench.test_app_repo_commits_are_reviewed_for_the_workbench_feature | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_app_repo_commits_are_reviewed_for_the_workbench_feature` |
| AC-002 | tests/test_workbench.py › PluginReviewWorkbench.test_app_repo_commits_are_reviewed_for_the_workbench_feature | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_app_repo_commits_are_reviewed_for_the_workbench_feature` |

## Must never break

- An active feature owns its repos as before; the rest of PluginReviewWorkbench and the review-gate tests.

## Out of scope

- None.

## Review

Security review fires (Risk: high); deferred by the user to one review over all of the 2026-11-22 todo fixes at the end of the push.

- **End-of-push review (one pass over all of the 2026-11-22 todo fixes, by area):** scripts and hooks security reviews r1 FAIL, fixed in ddd2c43 and a1552fc; r2 FAIL past the cap, and the user chose to fix the rest (4a0e8f8) and park the read-only guard's lexer as a documented limitation (docs/wiki/Limitations.md). UI review r1 FAIL, fixed in b43026e. What is left is in `.sdlc/todo.md`.
