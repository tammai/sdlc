# Team mode in a workbench: the releaser files lessons in an app repo

## Why

**Request (verbatim):** from `.sdlc/todo.md`: "Team mode in a workbench: an app repo without its own config can't take the releaser's Learn files (`.claude/rules/`, `knowledge/`)"

**Proof:** `tests/test_team_mode.py` › `test_the_releaser_files_lessons_in_a_workbench_app_repo` fails: the releaser is denied `api/.claude/rules/api.md` in a workbench whose app repo `api` has no `.sdlc/config.json`.

**Root cause:** with no config in the app repo, the role guard judges the path against the workbench root. There `shipping()` sees `api/.claude/rules/…`, which doesn't start with `.claude/rules/`.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| In a workbench, a path inside a writable repo the manifest lists is judged by `shipping()` from that repo's folder | `.claude/rules/` at any depth | only a real app repo's own lesson files; a read-only repo or an unlisted folder stays denied |

## Acceptance criteria

- **AC-001** In a workbench, the releaser may write Learn's files (`.claude/rules/`, `knowledge/`, hookify rules, CLAUDE.md) inside a writable app repo, and is still denied product code there, any read-only repo's files and unlisted folders.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_team_mode.py › TeamModeTest.test_the_releaser_files_lessons_in_a_workbench_app_repo | `python3.10 -m unittest discover -s tests -t tests -p test_team_mode.py -k test_the_releaser_files_lessons_in_a_workbench_app_repo` |

## Must never break

- The releaser's limits outside a workbench.

## Out of scope

- The other role agents in a workbench.

## Review

No review ran: no trigger fired.
