# The verification record holds up: zero tests don't pass, the waiver covers only the baseline, M and L lock their tests

## Why

**Request:** "do P1, P2, P5 and P3" of issue #56 (Proposal: make the verification record hold up). Each AC's red-then-green record is sdlc's proof (Goal 5); three paths let it stand while the test proves nothing, and the PRD says the flow is unmeasured when evals are on record.
- P1: an AC whose Run command exits 0 after running no tests passes `verify.py` (only the red steps look for "no tests ran"; unittest's `Ran 0 tests` isn't recognised at all).
- P2: `ship.py --waive-baseline` waives any test-step failure once the baseline lists anything; it never compares the failures with the listed ones (seen in the 3.8.0 and 3.9.0 smoke tests).
- P3: the test lock (a test file's sha256 at its red run, so a test weakened afterwards fails verify) is on only in spec-backed repos, by 3.5.0's choice; the user now wants it on M and L everywhere.
- P5: PRD §8 says "Not yet measured" and §11 "The flow is instructed, not yet evaluated".

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| P1 checks an AC row's output for the runner's "no tests ran" text when its Run command exits 0, as the red step already does; `Ran 0 tests` (unittest) and `# tests 0` (node --test) join that list | checking the verify plan's own test step | the plan's step runs the whole suite; the issue's hole is the AC's own command |
| P2 names the failing tests from the test step's full output (pytest, unittest, jest, vitest, go test, node --test) and checks the count against the runner's own summary; any failure not in the baseline, or output it can't name, refuses the waiver and prints why | substring match on whole output lines; trusting the agent's check (today) | fail closed: a failure the parser can't see must not be waived |
| A failing test counts as listed when its name, or its last part (after `::`, ` › `, ` > `, `.`, or the Go parent before `/`), appears as a whole word in a baseline row's Test cell | exact cell match | the baseline's Test cell is free text (`file › name`) written by setup |
| `verify.py` keeps a failing test step's full output (its last 1 MB) in `verify.json`'s `last.test_output` | rerunning the suite in `ship.py` | one run; the record stays local in `.sdlc/.work/` |
| P3: the red step locks test files on track M and L in every repo; a spec-backed repo still locks every track; S, and a state file with no `Track:`, lock nothing. `verify.py` checks whatever lock the state file holds, and `red --at` runs wherever a lock is on | a migration | a feature already in flight has no `## Test lock`, so nothing changes for it |
| P5 lists the eval rounds on record (commit, size, runs, ratios) and what hasn't been measured | rerunning the eval | P4 (eval tasks) is out of scope |

## Acceptance criteria

- **AC-001** Given an AC whose Run command exits 0 but prints a runner's "no tests ran" (e.g. unittest's `Ran 0 tests`), when `verify.py` runs, then that AC fails as "did not run"; and `verify.py red` refuses the same row.
- **AC-002** Given the baseline lists a failing test and the test step fails with only that test, when `ship.py --waive-baseline` runs, then it ships and the Gate log line names the waived test.
- **AC-003** Given the test step fails with a listed test and one that isn't listed, when `ship.py --waive-baseline` runs, then it refuses, names the unlisted test, and moves nothing.
- **AC-004** Given a failing test step whose output names no failing test (or fewer than its summary counts), when `ship.py --waive-baseline` runs, then it refuses and says the failures couldn't be matched to the baseline.
- **AC-005** The failing tests are named from pytest, unittest, jest, vitest, go test and node --test output, each with its count.
- **AC-006** Given a repo that isn't spec-backed and a feature on track M (or L), when `verify.py red` runs, then each test file it ran is locked, and a later change to that file fails `verify.py` with the test-lock message.
- **AC-007** Given a repo that isn't spec-backed and a feature on track S (or with no `Track:`), when `verify.py red` runs, then nothing is locked and a changed test still passes `verify.py`.
- **AC-008** Given a locked test changed in a standalone M feature with a `test-change` deviation, when `verify.py red --at <Base>` runs and the test fails there, then `verify.py` passes again.
- **AC-009** PRD §8 and §11 list the eval rounds on record and what hasn't been measured.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_verify.py › VerifyTest.test_an_ac_that_runs_no_tests_did_not_run | `py -3.10 -m unittest discover -s tests -t tests -p test_verify.py -k test_an_ac_that_runs_no_tests_did_not_run` |
| AC-002 | tests/test_ship.py › ShipTest.test_a_baseline_listed_test_failure_ships_only_when_waived_and_is_logged | `py -3.10 -m unittest discover -s tests -t tests -p test_ship.py -k test_a_baseline_listed_test_failure_ships_only_when_waived_and_is_logged` |
| AC-003 | tests/test_ship.py › ShipTest.test_the_waiver_refuses_a_failure_the_baseline_doesnt_list | `py -3.10 -m unittest discover -s tests -t tests -p test_ship.py -k test_the_waiver_refuses_a_failure_the_baseline_doesnt_list` |
| AC-004 | tests/test_ship.py › ShipTest.test_the_waiver_refuses_failures_it_cannot_name | `py -3.10 -m unittest discover -s tests -t tests -p test_ship.py -k test_the_waiver_refuses_failures_it_cannot_name` |
| AC-005 | tests/test_ship.py › FailingTestsTest.test_names_and_counts_failures_per_runner | `py -3.10 -m unittest discover -s tests -t tests -p test_ship.py -k test_names_and_counts_failures_per_runner` |
| AC-006  | tests/test_test_lock.py › StandaloneLockTest.test_m_and_l_lock_s_and_no_track_do_not | `py -3.10 -m unittest discover -s tests -t tests -p test_test_lock.py -k test_m_and_l_lock_s_and_no_track_do_not` |
| AC-007  | tests/test_test_lock.py › StandaloneLockTest.test_m_and_l_lock_s_and_no_track_do_not | `py -3.10 -m unittest discover -s tests -t tests -p test_test_lock.py -k test_m_and_l_lock_s_and_no_track_do_not` |
| AC-008 | tests/test_test_lock.py › StandaloneLockTest.test_m_re_red_at_base_passes | `py -3.10 -m unittest discover -s tests -t tests -p test_test_lock.py -k test_m_re_red_at_base_passes` |
| AC-009 | manual | docs only: read PRD §8 and §11 against the CHANGELOG and ADR 0016's eval numbers |

## Must never break

- A spec-backed repo's test lock, `red --at` and recorded acceptance tests behave as before.
- A workbench app repo's failure (`<repo>: … test: exit`) is never waived by the workbench's baseline.
- An S change records no lock and needs no deviation to fix its test.
- A feature in flight (red recorded before this change, no `## Test lock`) still verifies.
- The plugin stays Python stdlib only.

## Out of scope

- #56's P4 (seeded-defect eval tasks), P6 (lock hashes in CI), P7 (doctor row for required checks) and P8 (splitting `flow.md`): not asked.
- Build's gate with only a baselined failure (`state.py advance 3 --verified` refuses; 3.9.0 known issue): a separate fix.

## Review

No review ran: low risk, no trigger fired (no Public Surface: the new script helpers are internal, recorded as deviations; 3 source files, under 300 added lines); every AC with a test red then green (verify.py). AC-009 (manual): PRD §8 and §11 checked against CHANGELOG (83de649, 1817fc0, 7c9b385, rc.5) and the recorded eval rounds (c925268, f06c56c). Full suite: 621 tests pass on Python 3.10.
