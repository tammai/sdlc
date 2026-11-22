# Folders named `..something` count as inside the project

## Why

From `.sdlc/todo.md`: "`hooks/gitutil.py` (path list) and `hooks/verify_freshness.py` (`is_code_file`) also test `rel.startswith("..")`, so a project path like `..hidden/` reads as outside the project; use the segment check role_guard now uses — left out of the role_guard fix (2026-11-05)".

Proof: in Review, an edit to `..hidden/x.ts` inside the project doesn't make the test results stale (the freshness hook treats it as outside the project), and the turn's security-review diff drops `..hidden/x.py` from its path list. Root cause: both places test the relative path's text for a `..` prefix instead of its first segment being `..`.

## Decisions

- The segment check role_guard uses (`rel == ".."` or `rel` starting with `../`, after normalising separators to `/`). Ruled out: resolving with `os.path.commonpath`, which raises across Windows drives (a recurring defect) and changes more than the bug needs.

## Acceptance criteria

- **AC-001** In Review, after a passing test run, an edit to `..hidden/x.ts` inside the project makes the results stale, so the stop is blocked.
- **AC-002** The security review's diff path list keeps a file under `..hidden/` inside the repo, and still drops a file outside it.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_verify_freshness.py › VerifyFreshnessTest.test_a_folder_named_dotdot_something_is_inside_the_project | `python3.10 -m unittest discover -s tests -t tests -p test_verify_freshness.py -k test_a_folder_named_dotdot_something_is_inside_the_project` |
| AC-002 | tests/test_gitutil.py › DiffPathspecTest.test_a_folder_named_dotdot_something_stays_in_the_path_list | `python3.10 -m unittest discover -s tests -t tests -p test_gitutil.py -k test_a_folder_named_dotdot_something_stays_in_the_path_list` |

## Must never break

- An edit outside the project (`../elsewhere.ts`, another drive) still doesn't make results stale, and stays out of the diff's path list.
- A path list with only outside paths still gives an empty pathspec, never an unrestricted diff.

## Out of scope

- Other `startswith("..")` checks elsewhere: a grep of `hooks/` and `scripts/` finds only these two.

## Review

No review ran: no trigger fired (low risk, no Public Surface, no sensitive path).
