# A decided departure can set a recorded acceptance test aside, with a builder test proving the AC

## Why

**Request:** "do #68" (verify.py: no supported path for an AC whose recorded test a decided departure says cannot pass). In a spec-backed lane, `lane_plan.py` fills an AC's Test cell with its open recorded test. When a decided departure (contracts C5, `docs/departures.yaml`) explains why that test can't pass against the rebuild (it drives the reference's GraphQL API; the rebuild serves a locked REST contract), the AC can never go green. The S2 run pointed the Test cell at a builder test instead, with the orchestrator's OK: it works, but it's off the record and `verify.py` never sees the departure.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| A departure is its own row: `\| AC-003 \| departure D-004 \| acceptance/http/F-ISS-01.AC2.yaml \|`, the Run cell naming the recorded test it sets aside; the AC's builder test is a second row with the same AC | a second column; folding the departure into the builder row's cells | the table's shape stays three columns, and each row says one thing |
| `verify.py` accepts the departure row only when `docs/departures.yaml` is valid (contracts C5, read with the vendored contracts' parser), holds the ID, it isn't `status: proposed`, has `decided_by`, and its `criteria` include the recorded test's criterion (its manifest entry) | trusting the ID alone | the departure must be decided and be about this test |
| An AC with a departure row and no builder row fails, in `red` and in the full run | letting the departure stand alone | the issue: the AC still needs a test that proves the behaviour |
| `docs/departures.yaml` at the repo root (the workbench, where the record and verify run) | a config key naming the path | product-rebuild's README and PLAYBOOK name `docs/departures.yaml`; a path from repo config is untrusted (knowledge gotcha) |

## Acceptance criteria

- **AC-001** Given an AC with a row `departure D-004` naming its recorded test, and a builder test row, with D-004 decided in `docs/departures.yaml` and covering the recorded test's criterion, when `verify.py red` and then `verify.py` run, then red records the builder test failing and the full run passes without running the recorded test.
- **AC-002** Given such a departure row, when `docs/departures.yaml` is missing, the departure isn't in it, it has no `decided_by`, it is `status: proposed`, it doesn't cover the recorded test's criterion, or the Run cell isn't a recorded test in the manifest, then `verify.py` fails, saying which.
- **AC-003** Given an AC with a departure row and no builder test row, then `verify.py red` and `verify.py` fail, saying it needs a builder test row.
- **AC-004** `flow.md`, the Verification wiki and spec 04 describe the departure row.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_recorded_tests.py › DepartureTest.test_a_decided_departure_sets_the_recorded_test_aside | `py -3.10 -m unittest discover -s tests -t tests -p test_recorded_tests.py -k test_a_decided_departure_sets_the_recorded_test_aside` |
| AC-002 | tests/test_recorded_tests.py › DepartureTest.test_a_departure_that_does_not_hold_fails | `py -3.10 -m unittest discover -s tests -t tests -p test_recorded_tests.py -k test_a_departure_that_does_not_hold_fails` |
| AC-003 | tests/test_recorded_tests.py › DepartureTest.test_a_departure_needs_a_builder_test | `py -3.10 -m unittest discover -s tests -t tests -p test_recorded_tests.py -k test_a_departure_needs_a_builder_test` |
| AC-004 | manual | docs only: read flow.md's Build step 1, the Verification wiki and spec 04 against the code |

## Must never break

- A row whose Test is an open recorded test still runs it against the build `verify.py` starts.
- The drift check, the test lock and `red --at` never treat a departure row as a test file.
- A repo that isn't spec-backed behaves as before (a departure row there still needs the manifest and `docs/departures.yaml`, so it fails rather than passing unchecked).

## Out of scope

- product-rebuild's `lane_plan.py` writing departure rows (another repo; noted on the issue).
- #56 P6 (CI checks the lock hashes): the next change.

## Review

No review ran: low risk, no trigger fired (no Public Surface: the new verify.py helpers are internal, recorded as deviations; one source file, under 300 added lines); every AC with a test red then green (verify.py); the test file's change after red was recorded and re-red at Base. AC-004 (manual): flow.md Build step 1, the Verification wiki and the rebuild-upgrade sdlc spec read against verify.py's departure_check. Full suite: 624 tests pass on Python 3.10.
