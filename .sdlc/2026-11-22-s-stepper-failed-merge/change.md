# sdlc-stepper doesn't mark a failed merge done

## Why

A 3.14.0 known issue, from `.sdlc/todo.md`: "sdlc-stepper marks a ship done when a `gh pr merge` command runs, from its text, so a merge that fails still shows `Ship · done` until the next prompt — 3.14.0 known issue; `plugins/sdlc-stepper/hooks/register.tsx` (2026-11-22)".

Proof: the 3.14.0 smoke test ran a stand-in `gh pr merge` and the bar read `Ship · done` whatever the command's outcome. Root cause: the `tool.call` hook sets the step from the command text and skips only a denied call; it never reads the result's `isError`, which the engine sets when a tool reports an error, a non-zero Bash exit included.

## Decisions

- Skip only the `done` step on an errored call. A failed run of any other step, such as a failing `verify.py`, is still that step. Ruled out: skipping every step on an error, which would hide the verify step exactly when it matters.

## Acceptance criteria

- **AC-001** A `gh pr merge` that exits non-zero leaves the bar at Ship (`✓─✓─✓─●`), and a successful one still checks all four stages.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | plugins/sdlc-stepper/tests/stepper.test.tsx › a merge that failed leaves the feature at Ship | `claude plugin test plugins/sdlc-stepper` |

## Must never break

- A successful merge still shows `Ship · done` and clears at the next prompt (`merging the PR marks the shipped feature done, and the next prompt clears it`).

## Out of scope

- A PR merged outside the session, on GitHub, which the stepper still doesn't see.

## Review

No review ran: no trigger fired (low risk, no Public Surface, no sensitive path).
