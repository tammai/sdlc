# Opt-in test lock on S (config `guards.s_tests`)

## Why

**Request:** GitHub issue #92, part 2 of 4: "S has no test lock (spec-backed repos aside). S is the most common track and usually gets no review, so a test can be weakened after the red step unnoticed." The user chose an opt-in lock, not the issue's "always on", so a repo's defaults stay as in 3.15.

## Decisions

| Decision | Chosen | Ruled out | Why |
|---|---|---|---|
| Switch | `"guards": {"s_tests": true}`, set by `scaffold.py guard s-tests on|off` (`/sdlc:setup guard …`) | a top-level key | parts 3 adds `guards.dependencies` and `guards.lint_config` beside it |
| Turning a guard off | a trust-anchor notice; honoured once the user accepts, like `mode`, `skip` and `approval`; turning one on applies at once | reading config directly | the key is agent-editable config |
| The lock itself | the M/L lock as it is: `verify.py red` hashes the test files, a changed one fails `$V` until a `test-change` deviation and `red --at <Base>` | a lighter S-only lock | one mechanism, already proven |

## Acceptance criteria

- **AC-001** With `guards.s_tests` on, an S feature's red step locks its test files, and a test changed after it fails `verify.py`.
- **AC-002** Turning `guards.s_tests` off raises a trust-anchor notice and isn't honoured until the user accepts it; turning it on is honoured at once.
- **AC-003** `scaffold.py guard s-tests on` writes `guards.s_tests: true` and refuses an unknown guard; the session status line shows `guards s-tests`.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_test_lock.py › GuardedSLockTest.test_s_locks_its_tests_with_the_guard_on | `py -3.10 -m unittest discover -s tests -t tests -p test_test_lock.py -k test_s_locks_its_tests_with_the_guard_on` |
| AC-002 | tests/test_guards.py › GuardsTest.test_turning_a_guard_off_waits_for_the_trust_anchor | `py -3.10 -m unittest discover -s tests -t tests -p test_guards.py -k test_turning_a_guard_off_waits_for_the_trust_anchor` |
| AC-003 | tests/test_guards.py › GuardsTest.test_scaffold_sets_a_guard_and_the_status_line_shows_it | `py -3.10 -m unittest discover -s tests -t tests -p test_guards.py -k test_scaffold_sets_a_guard_and_the_status_line_shows_it` |

## Must never break

- Without the guard, S locks nothing (`test_m_and_l_lock_s_and_no_track_do_not`).
- `mode`, `skip` and `approval` acceptance work as before; a trust-anchor record without `guards` stays valid.

## Review

- **Fired:** code review, because `## Public Surface` lists `guards.s_tests` and `scaffold.py guard`. Security and UI review didn't fire.
- **Round 1:** the built-in `code-review` at `high --max-findings all`. FAIL.
  - CR1 (high): a lock written under the guard couldn't be re-red once the guard was off.
  - CR2 (medium): the dialog approval read the asked questions at the gate root.
  - CR3–CR6 (low): typed-approve matching, unknown guard names counted as damage, stale docs, and hooks run with a bare `python3` in tests.
  - All fixed test first, except CR2, which has no workbench test (ticketed).
- **Round 2:** `sdlc:code-reviewer` on opus, closing check. PASS. Its follow-ups were fixed test first without another round:
  - R2-1(b): a test for an unknown guard name in the record.
  - R2-2: unknown guards are kept in the record for the version that knows them.
  - R2-4: an exact typed name matches first.
  - R2-5: four docs and comments that said S never locks.
- **Tickets:** R2-1(a) and R2-3 (a dialog approval in a workbench session started in an app repo) are in `.sdlc/todo.md`.
- **Lessons filed:** None
