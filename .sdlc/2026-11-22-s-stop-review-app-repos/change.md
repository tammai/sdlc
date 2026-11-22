# The turn-end security review covers a workbench app repo's uncommitted change

## Why

From `.sdlc/todo.md`: "The Stop security review can't see uncommitted changes in a workbench's gitignored app repos (app-repo commits are reviewed at commit time since the workbench fix); make the Stop review take branched repos' diffs — whole-plugin review H4 remainder".

Proof: the Stop hook resolves its repo from the turn's touched paths, so an edit in `api/` lands it in `api`. There, `sdlc_review_gate.review_wanted(api)` looks for an active feature in `api` itself, finds none (the feature lives in the workbench) and the review is skipped (skip 51), Risk high or not. AC-001's test fails.

## Decisions

- `review_wanted` asks `_workbench_feature` for a workbench's app repo, as `decide` does for its commits. No owner means no review (unless `SDLC_SECURITY_REVIEW=always`); an unsure owner means review. Otherwise the owner's Risk, or a security area touched since the repo's own base (`## Repos`: `base`), uncommitted and untracked files included.
- Left open in the todo: a turn that edits two app repos still resolves to one of them, so only one is reviewed at turn end. Their commits are still reviewed at commit time.

## Acceptance criteria

- **AC-001** In a workbench, for `api` branched by the active feature: an uncommitted change is reviewed at turn end when Risk is high or a security area (`auth/`) is touched, not when Risk is low and none is touched, and not once the feature no longer owns the repo.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_workbench.py › PluginReviewWorkbench.test_the_turn_end_review_sees_an_app_repos_uncommitted_change | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_the_turn_end_review_sees_an_app_repos_uncommitted_change` |

## Must never break

- test_sdlc_review_gate (a single repo's Stop review), the rest of PluginReviewWorkbench.

## Out of scope

- Several app repos in one turn: the new todo.

## Review

Security review fires (Risk: high); deferred by the user to one review over all of the 2026-11-22 todo fixes at the end of the push.
