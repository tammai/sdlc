# Part plan: 2026-11-13-l-workbench B2

**Record:** the feature's change file (`scaffold.py paths 2026-11-13-l-workbench` → `change`) · **Backlog:** [backlog.md](backlog.md)

## Tasks

1. **Detection and scopes** — AC-004
   - Files: `hooks/sdlc_scopes.py`
   - Test first: `test_workbench_scopes_and_detection`
   - Then: `is_workbench` (config `"workbench": true` and `workbench.json`), `manifest` (validated entries, named
     `not run:` errors), `workbench_scopes` (one per writable repo from its own config, then the workbench).
2. **Add and remove** — AC-005
   - Files: `scripts/scaffold.py`
   - Test first: `test_workbench_add_and_remove`
   - Then: `scaffold.py workbench list|add|remove`; add validates the entry before cloning with `git clone -- <url>`,
     then writes the gitignore line and the manifest atomically; remove keeps the folder.
3. **Doctor** — AC-006
   - Files: `scripts/doctor.py`
   - Test first: `test_doctor_reports_workbench_drift`
   - Then: `check_workbench` rows: not cloned, unlisted nested repos, not gitignored, app without its own config.

## Public Surface

- command `scaffold.py workbench` — AC-005
- config `workbench` — AC-004
