# Part plan: 2026-11-13-l-workbench B1

**Record:** the feature's change file (`scaffold.py paths 2026-11-13-l-workbench` → `change`) · **Backlog:** [backlog.md](backlog.md)

## Tasks

1. **One scope parser** — AC-001
   - Files: `hooks/sdlc_scopes.py`, `scripts/scaffold.py`, `hooks/verify_freshness.py`, `tests/test_scaffold.py`
   - Test first: `test_one_scope_parser_for_scripts_and_hooks`
   - Then: `scaffold.scopes()` and `verify_freshness.load_scopes()` both read packages through `sdlc_scopes`; an
     unnamed package is named after its normalised path; malformed `packages` raises a named ValueError.
2. **Root commands beside packages run** — AC-002
   - Files: `scripts/scaffold.py`
   - Test first: `test_root_test_beside_packages_runs_and_covers_every_package`
   - Then: `verify_plan` puts a root install first and the root's other steps after every package's; per-package CI
     leaves them out.
3. **Brownfield doc and the docs restating the rule** — AC-003
   - Files: `skills/setting-up-projects/references/brownfield.md`, `skills/setting-up-projects/references/greenfield.md`, `docs/wiki/Configuration.md`
   - Test first: `test_brownfield_reference_records_top_level_packages`
   - Then: name the top-level `packages` key; say root commands run in verify and CI.

## Public Surface

- none (internal module `hooks/sdlc_scopes.py`, recorded as a deviation)
