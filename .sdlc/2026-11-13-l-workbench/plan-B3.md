# Part plan: 2026-11-13-l-workbench B3

**Record:** the feature's change file (`scaffold.py paths 2026-11-13-l-workbench` → `change`) · **Backlog:** [backlog.md](backlog.md)

## Tasks

1. **Routing from a workbench** — AC-007
   - Files: `hooks/sdlc_layout.py`
   - Test first: `test_guards_route_into_an_app_repo_from_a_workbench`
   - Then: `target_repo` keeps resolving the nested repo when the session root is a workbench
     (`sdlc_scopes.is_workbench`: config key and manifest); any other root with `.sdlc/` returns None as before.
     hookify (`pretooluse.py`) and the role guard already route through it.
2. **Read-only guard** — AC-008
   - Files: `hooks/role_guard.py`, `hooks/pretooluse.py`
   - Test first: `test_writes_into_a_read_only_repo_are_denied`
   - Then: `hits`/`shell_write` gain a folder mode (a path at or under a protected folder, links resolved, touch/mkdir
     and repo-writing git verbs too); `read_only_problem` denies Edit/Write/shell writes into a `write: false`
     repo, naming it and its owner; `pretooluse.py` runs it against the session's workbench root.
3. **No features in app repos** — AC-009
   - Files: `hooks/sdlc_scopes.py`, `scripts/state.py`
   - Test first: `test_no_feature_starts_in_an_app_repo`
   - Then: `sdlc_scopes.workbench_of` (an app's `"workbench": "<name>"`); `state.py new` refuses there, first,
     naming the workbench and writing nothing.

## Public Surface

- none beyond the plan (internal functions only)
