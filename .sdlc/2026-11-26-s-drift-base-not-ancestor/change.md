# Verify refuses a Base: no longer behind HEAD

## Why

**Request (verbatim):** "continue", after the todo item: "Drift after a local rebase: a `Base:` still in the clone but no longer an ancestor of HEAD passes verify's base check, and drift is diffed against the old commit (`git merge-base --is-ancestor` would catch it). Code review r1 of 2026-11-26-s-verify-missing-base, pre-existing".

**Proof:** `tests/test_verify.py` › `test_a_base_no_longer_behind_head_fails_drift` fails: with `Base:` set to a commit on another branch, verify passes and checks drift over the wrong range.

**Root cause:** `verify.drift` checked only that `Base:` resolves (since #152), not that HEAD descends from it. The red-step lock already makes that check (`lock_failures`); drift didn't.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| A `Base:` that isn't an ancestor of HEAD fails verify with `base_not_ancestor` and a fix naming the line to correct; the same check runs for each workbench app repo's base | a warning | drift over the wrong range can hide real drift or blame upstream files |
| git failing to compare fails as `drift_unchecked` | treating it as not behind | fail closed, with its own message |
| Stacked on #152's branch | branching from main | it changes the code #152 adds |

## Acceptance criteria

- **AC-001** With `Base:` not an ancestor of HEAD, verify fails with `base_not_ancestor`, naming a branch switch as a cause, and a fix that says to switch back first and names the feature.
- **AC-002** A workbench app repo's base not behind its HEAD fails drift with `base_not_ancestor`, and the fix says to switch that repo back and names its `## Repos` line.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_verify.py › VerifyTest.test_a_base_no_longer_behind_head_fails_drift | `python3 -m unittest discover -s tests -t tests -p test_verify.py -k test_a_base_no_longer_behind_head_fails_drift` |
| AC-002 | tests/test_workbench.py › PluginReviewWorkbench.test_an_app_repos_base_no_longer_behind_its_head_fails_drift | `python3 -m unittest discover -s tests -t tests -p test_workbench.py -k test_an_app_repos_base_no_longer_behind_its_head_fails_drift` |

## Must never break

- A feature whose `Base:` is behind HEAD (every normal one, `Base:` equal to HEAD included) checks drift as before.

## Out of scope

- Several missing bases reported one per run (todo).
- A rebase onto a newer main, which keeps the old `Base:` an ancestor (todo).

## Review

- Fired: code review (the Public Surface changed). Built-in `code-review` at high, all findings.
- Round 1: FAIL. Low bug F2: the fix said to rewrite `Base:` when another branch was simply checked out. Fixed test first in AC-001 and AC-002: the message names a branch switch and the fix says to switch back first. Also: git's reason shown, the spec lists the workbench test, an assertion that couldn't fail dropped, and the docs narrowed (a rebase onto a newer main isn't caught; parked in the todo).
- Round 2: PASS (no high). Its bugs were fixed test first in AC-001 and AC-002: a shallow clone cut above `Base:` is `base_missing` with the fetch, not `base_not_ancestor`; `base_missing` no longer gives rebase advice; an app repo's fix names its recorded branch; one shared git helper. The merge-main case joined the todo's rebase line.
- Lessons: none filed.
