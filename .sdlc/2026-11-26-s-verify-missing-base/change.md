# Verify names a Base: missing from the clone

## Why

**Request (verbatim):** "verify.py Base crash" (the todo: "`verify.py` crashes with a traceback (`diff_stats.collect`: `fatal: bad object`) when the state file's `Base:` commit isn't in the clone (a shallow fetch, a rebase), instead of a refusal naming it").

**Proof:** `tests/test_verify.py` › `test_a_base_commit_missing_from_the_clone_fails_with_a_message_not_a_traceback` fails: verify exits with `RuntimeError: git diff … fatal: bad object …`. Ship crashes the same way, since it runs verify.

**Root cause:** `verify.drift` passes `Base:` straight to `diff_stats.collect`. Its `git` helper raises `RuntimeError` when git fails, and nothing on the way to `main` catches it.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| A missing `Base:` commit fails verify with `base_missing`, naming the commit and how to fetch it | a warning, like `drift_not_checked` for a missing `Base:` line | the feature has a Base; drift that can't be checked mustn't pass (fail closed) |
| Every base is checked, the feature's and each branched app repo's, with git's own reason (missing, ambiguous) in the message (code review r1) | `rev-parse --quiet`, the root only | collect only flagged an app repo it couldn't scan, so drift passed unchecked |
| Any other git failure in the drift diff, or git not running, fails with `drift_unchecked` | letting it crash | fail closed |

## Acceptance criteria

- **AC-001** With a `Base:` commit not in the clone, verify fails with a `base_missing` problem naming the commit and a fix naming the feature, never a traceback, and records the run as failed.
- **AC-002** A workbench app repo's base missing from its clone fails drift with `base_missing` naming the repo.
- **AC-003** A git failure in the drift diff, or git not running, fails drift with `drift_unchecked` and a fix.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_verify.py › VerifyTest.test_a_base_commit_missing_from_the_clone_fails_with_a_message_not_a_traceback | `python3 -m unittest discover -s tests -t tests -p test_verify.py -k test_a_base_commit_missing_from_the_clone_fails_with_a_message_not_a_traceback` |
| AC-002 | tests/test_workbench.py › PluginReviewWorkbench.test_an_app_repos_base_missing_from_its_clone_fails_drift | `python3 -m unittest discover -s tests -t tests -p test_workbench.py -k test_an_app_repos_base_missing_from_its_clone_fails_drift` |
| AC-003 | tests/test_verify.py › VerifyTest.test_a_git_failure_in_the_drift_diff_fails_as_drift_unchecked | `python3 -m unittest discover -s tests -t tests -p test_verify.py -k test_a_git_failure_in_the_drift_diff_fails_as_drift_unchecked` |

## Must never break

- A state file with no `Base:` line still gets the `drift_not_checked` warning, not a failure.
- Drift is checked as before when `Base:` is in the clone.

## Out of scope

- The todo line itself is ticked once #151 (which adds it) is merged.
- A `Base:` that is no longer an ancestor after a rebase (parked in the todo).

## Review

- Fired: code review (the Public Surface changed). Built-in `code-review` at high, all findings.
- Round 1: FAIL. Bugs: a workbench app repo's missing base still skipped silently (medium); an ambiguous short id reported as missing; a literal `<feature>` in the fix; git missing from PATH still a traceback. Fixed test first (AC-002, AC-003): every base checked, with git's own reason.
- Round 2: PASS (no high). Its bugs were fixed test first in AC-002 and AC-003: git not running is `drift_unchecked`; an app repo git can't diff fails; an app repo's fix names its `## Repos` line; only git's `error:`/`fatal:` lines are kept; rev-parse is bounded and never prompts. Parked in the todo: one missing base reported per run; a non-ancestor `Base:` after a rebase.
- Lessons: none filed.
