# role_guard treats project paths starting with .. (like ..hidden/) as outside the project

## Why

Request (verbatim): "role_guard treats project paths starting with .. (like ..hidden/) as outside the project. `hooks/role_guard.py` treats a project path whose first part starts with two dots (a folder `..hidden/` or a file `..env`) as outside the project, so it doesn't apply the role rules there: a code-reviewer can edit `..hidden/app.py`, and the qa-tester can read it. Expected: both edits are denied. A path is outside the project only when its relative form is `..` or starts with `../` (or `..\` on Windows). Root cause: `rel_path()` in `hooks/role_guard.py` tests `rel.startswith("..")`, which matches any name beginning with two dots. `scaffold.rel()` already uses the segment check."

Proof: `tests/test_role_guard.py › test_names_starting_with_two_dots_are_inside_the_project` fails before the fix (the code-reviewer's Edit of `..hidden/app.py` gets no decision).

Root cause: `rel_path()` checks `rel.startswith("..")` on the relative path, a string-prefix test rather than a path-segment test, so `..hidden/app.py` and `..env` read as outside the project.

## Decisions

- Use the segment check `scaffold.rel()` uses: outside only when the relative path (already `/`-separated) is `..` or starts with `../`. Ruled out: importing `scaffold.rel()` into the hook, which raises instead of returning None and would pull a script module into a hook.

## Acceptance criteria

- AC-001: a code-reviewer's Edit of `..hidden/app.py` and Write of `..env` are denied, and the qa-tester's Read of `..hidden/app.py` is denied.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_role_guard.py › test_names_starting_with_two_dots_are_inside_the_project | `python3 -m unittest discover -s tests -t tests -p test_role_guard.py -k test_names_starting_with_two_dots_are_inside_the_project` |

## Must never break

- A path really outside the project (`../elsewhere/app.py`) is still left alone: `tests/test_role_guard.py › test_paths_outside_the_project_are_left_alone`, which passes before and after the fix.
- Every existing role rule in `hooks/role_guard.py` (reviewers write only their findings file, qa-tester reads the spec but not the code).

## Out of scope

- The same `startswith("..")` prefix test in `hooks/gitutil.py` and `hooks/verify_freshness.py`: filed as a todo.

## Review

No review ran: no trigger fired.
