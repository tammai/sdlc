# Brownfield CI passes when only baselined tests fail

## Why

**Request:** "work on open issues", the todo "Brownfield: the generated `sdlc-verify.yml` fails every PR while `.sdlc/baseline.md` lists a failing test", from the 3.15.0 smoke test G and a known issue in 3.15.0 and 3.16.0.

Locally, `ship.py --waive-baseline` lets a test run through when every failure it names is in the baseline. CI runs the plain test command, so a brownfield repo's PRs are red from the first one, and a red check stops meaning anything.

## Decisions

| Decision | Chosen | Ruled out | Why |
|---|---|---|---|
| Where CI decides | The generated test step tees its output to a log. When the command fails, `python3 .sdlc/ci/invariants.py --baseline-tests <log>` decides, with the same rule as `ship.py --waive-baseline`: every failing test the runner names is listed, and the names match the runner's own count. | Runner-specific deselect flags (`--deselect`, `-skip`); `continue-on-error` | Deselect flags differ per runner and per package. `continue-on-error` would hide new failures. invariants.py is already the repo's stdlib-only CI script. |
| When the step is wrapped | When `.sdlc/baseline.md` lists at least one failing test at generation time; only the `test` step | Every repo | A repo with no baselined test keeps its plain step. A baseline that empties later leaves a wrapper that still fails on any failure. |
| A missing invariants.py or Python | The step fails with the test command's own exit code | Passing | Fails closed. |

## Acceptance criteria

- **AC-001** `invariants.py --baseline-tests <log>` exits 0 when every failing test the log names is in `.sdlc/baseline.md`. It exits 1, naming what's wrong, when a failing test isn't listed or the names don't match the runner's count.
- **AC-002** In a repo whose baseline lists a failing test, the generated workflow's test step passes when only that test fails, and fails when another one does. The step's script is run in bash, as the runner runs it.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_ci_baseline.py › CiBaselineTest.test_the_log_check_passes_only_listed_failures | `py -3.10 -m unittest discover -s tests -t tests -p test_ci_baseline.py -k test_the_log_check_passes_only_listed_failures` |
| AC-002 | tests/test_ci_baseline.py › CiBaselineTest.test_the_generated_test_step_waives_listed_failures | `py -3.10 -m unittest discover -s tests -t tests -p test_ci_baseline.py -k test_the_generated_test_step_waives_listed_failures` |

## Must never break

- A repo whose baseline lists no failing test gets the plain test step, as before (tests/test_ci_baseline.py › test_without_a_baselined_test_the_step_is_plain), so the existing CI template tests pass untouched.
- invariants.py's other checks and its `--json` output are unchanged.
- A failing test the baseline doesn't list still fails CI.

## Review

- **Fired:** code review. The diff adds a `--baseline-tests` flag to the generated `invariants.py` and a generated CI shell step; self-chosen at low risk.
- **Ran:** the built-in `code-review` (high, all findings), four rounds. Round 2 was the default cap. The user chose a further round after rounds 2 and 3, and to ship after round 4.
- **Round 1, FAIL:** 5 high.
  - R1-1, R1-2: `set -e` was off in the command's subshell, and a trailing comment broke the step.
  - R1-3: names were matched by leaf only.
  - R1-5: the Python pick could land on the Windows Store stub.
  - R1-6: colour codes broke matching.
  - Fixed test first, along with R1-7 to R1-9. R1-4 (fail-fast runs) is documented.
- **Round 2, FAIL:** 4 high. Three came from the stricter matcher R1-3 added. The user chose ship.py's exact rule for CI, and R2-4 (a non-UTF-8 log) was fixed.
- **Round 3, FAIL:** 2 high. R3-1: a repeated go name wasn't deduplicated as ship.py does. R3-2: a non-UTF-8 baseline crashed generation. Fixed.
- **Round 4:** the code fixes held. One high in the docs (R4-1: the regenerate command lacked `--class seeded`) was fixed with R4-3 and the nits. Waived by the user's choice to ship without another round (`waived round 4` in the state file's Deviations).
- **Tickets** (`.sdlc/todo.md`): ship.py reads only `.sdlc/baseline.md`; the waiver's shared limits (loose short names, non-test failures, fail-fast runs).
- **Drift:** in the state file's Deviations: AC-003 moved to Must never break, each test change, and Base moved twice as #142 and #143 merged.
- **Manual checks:** the Python pick on a Windows runner (R1-5) has no automated test; read against `hooks/sg-python.sh`'s approach.
- **Lessons filed:** None. [knowledge/gotchas/text-guards-dont-converge.md](../../knowledge/gotchas/text-guards-dont-converge.md) already covers what happened here: a stricter rule than the one shipped, added in a fix round, didn't converge.
