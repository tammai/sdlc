# Doctor checks a monorepo's root commands

## Why

**Request (verbatim):** from `.sdlc/todo.md`: "Doctor never checks root-scope commands in a monorepo (root `commands.test`, now also `commands.storybook`): their tool on PATH and \"commands run\" aren't reported; include the root pseudo-scope in the contract check and the never-run list"

**Proof:** `tests/test_doctor.py` › `test_a_monorepos_root_commands_are_checked_and_reported` fails: a root `commands.test` whose tool isn't on PATH raises no "command tools" warning.

**Root cause:** `scaffold.cmd_contract()` walks only `scopes()`, which in a monorepo lists the packages. The root pseudo-scope that `verify_plan()` runs (`test`, `storybook`) is never checked, so doctor never sees it either.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| `cmd_contract()` adds the root pseudo-scope when `verify_plan()` runs root steps: its tools are checked, but it has no required commands | a separate doctor check | doctor and `scaffold.py contract` stay one source; required commands belong to the packages |

## Acceptance criteria

- **AC-001** In a monorepo with a root `commands.test`, doctor warns when that command's tool isn't on PATH, lists the root's `test` under "commands run" until it has run, and stops once `run-commands` runs it.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_doctor.py › DoctorTest.test_a_monorepos_root_commands_are_checked_and_reported | `python3.10 -m unittest discover -s tests -t tests -p test_doctor.py -k test_a_monorepos_root_commands_are_checked_and_reported` |

## Must never break

- A single-project repo's contract (its root project is already a scope).
- A monorepo without root commands reports as before.

## Out of scope

- Root commands other than `test` and `storybook`, which verify doesn't run.

## Review

No review ran: no trigger fired.
