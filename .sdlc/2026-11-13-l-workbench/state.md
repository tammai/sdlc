# 2026-11-13-l-workbench
Status: active
Process: 3
Change: .sdlc/2026-11-13-l-workbench/change.md   (this feature's record for people)
Track: L   (sized up because: several distinct parts across setup, hooks, verify, ship and CI; footprint: 30 files)
Risk: high   (untrusted input: a committed workbench.yaml names folders and clone URLs that reach git and file paths)
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-13
Base: 58acb2e
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: 96a939c tree 6739fccd96deefa5f1596d72f17c2acdfa2cbd9a
Slice: B3   Slice base: 96a939c   Slice gates: none
Current: Stage 2 – Build

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [ ] 2 Build
- [ ] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
parts in fresh sessions, because seven parts across the core won't fit one context (backlog.md)

## Handoff
- Approved design and user answers: change.md Why/Decisions; product-rebuild's repos.yaml is kept apart (detect by config key workbench: true)
- Two scope parsers today: scripts/scaffold.py:555 scopes() and hooks/verify_freshness.py:141 load_scopes(); root commands.test is dropped by the first, honoured by the second
- Nested-repo routing: hooks/sdlc_layout.py:43 target_repo returns None whenever the session root has .sdlc/ (line 51); _sdlc_repo_inside at :72; tests in tests/test_session_above_repo.py
- hooks/reporesolve.py already scans nested repos for commit review (SCAN_MAX_DEPTH 3)
- This repo has no .sdlc/config.json: verify.py runs only AC tests; run the full suite by hand: python3.10 -m unittest discover -s tests -t tests

## Tasks
1. **B1 One scope parser; root test beside packages; brownfield doc** — AC-001 AC-002 AC-003
   - Files: `hooks/sdlc_scopes.py`, `scripts/scaffold.py`, `hooks/verify_freshness.py`, `skills/setting-up-projects/references/brownfield.md`, `tests/test_workbench.py`
2. **B2 Workbench manifest, detection, add/remove, doctor** — AC-004 AC-005 AC-006
   - Files: `hooks/sdlc_scopes.py`, `scripts/scaffold.py`, `scripts/doctor.py`, `tests/test_workbench.py`
3. **B3 Routing, read-only guard, no features in app repos** — AC-007 AC-008 AC-009
   - Files: `hooks/sdlc_layout.py`, `hooks/role_guard.py`, `hooks/pretooluse.py`, `scripts/state.py`, `tests/test_workbench.py`
4. **B4 One feature across repos** — AC-010 AC-011 AC-012
   - Files: `scripts/state.py`, `scripts/verify.py`, `hooks/verify_freshness.py`, `scripts/diff_stats.py`, `tests/test_workbench.py`
5. **B5 Ship across repos** — AC-013 AC-014
   - Files: `scripts/ship.py`, `tests/test_workbench.py`
6. **B6 App CI and contract check** — AC-015
   - Files: `scripts/scaffold.py`, `tests/test_workbench.py`
7. **B7 Setup reference, ADR, wiki, changelog** — AC-016
   - Files: `skills/setting-up-projects/references/workbench.md`, `skills/setting-up-projects/SKILL.md`, `skills/setting-up-projects/references/greenfield.md`, `docs/adr/0025-workbench-for-multi-app-projects.md`, `docs/adr/README.md`, `docs/wiki/Project-setup.md`, `docs/wiki/Configuration.md`, `docs/wiki/Where-things-live.md`, `CHANGELOG.md`, `tests/test_workbench.py`

## Public Surface
- command `scaffold.py workbench add|remove` — AC-005
- config `workbench` — AC-004
- config `workbench.yaml` — AC-004
- command `ship.py --status` — AC-014

## Gate log
- 2026-11-13 Stage 1: pass — plan self-approved (L): (1) each design goal maps to AC-001–016 and each AC to the design; (2) no open questions; (3) every decision is the user's answer or a call listed in the approved design; (4) no unasked proposal, nothing irreversible
- 2026-11-13 scope added by the user during B1: preferred stacks as part B8 (AC-017); Go stack chosen: Gin + oapi-codegen + pgx/v5 + sqlc + golang-migrate
- 2026-11-13 tests: per part, only the affected test modules on Python 3.10; the full suite once before Review (user's choice)
- 2026-11-13 handoff B2: hooks/sdlc_scopes.py has is_workbench/manifest/workbench_scopes (WORKBENCH_SCOPE '(workbench)'); B3 routes guards via them; scaffold.scopes() doesn't yet return workbench scopes (B4 wires verify/freshness)
- 2026-11-13 handoff B3: sdlc_layout.target_repo routes from a workbench root; role_guard.read_only_problem (via pretooluse) guards write:false repos; sdlc_scopes.workbench_of marks an app repo and state.py new refuses there. B4 next: per-repo branch/base in state.py, verify per touched repo, freshness per app scope (scaffold.scopes still doesn't return workbench scopes)

## Deviations
- 2026-11-13 setup What: went on with setup none (no .sdlc/config.json). Why: the plugin's own repo has always run sdlc without setup (e.g. 2026-11-08-l-spec-backed-mode). Effect: verify.py runs the AC tests; the full suite is run by hand with python3.10 -m unittest discover -s tests -t tests.
- 2026-11-13 tests/test_scaffold.py What: an unnamed package's contract entry is keyed by its path, not '?'. Why: AC-001 names a package without a name after its path in the one shared parser. Effect: test_contract_monorepo_packages expects the 'nowhere' key.
- 2026-11-13 hooks/sdlc_scopes.py exports norm, packages, root_commands, scopes What: the shared parser's functions, used by scaffold.py and verify_freshness.py. Why: AC-001's one parser for scripts and hooks; packages raises ValueError on malformed config instead of crashing later. Effect: internal API only, no user-facing surface.
- 2026-11-13 docs/wiki/Configuration.md What: the packages row says root commands beside packages run in verify and CI. Why: AC-002 changed that behaviour. Effect: docs only.
- 2026-11-13 B8 What: new part B8, preferred stacks (skills/setting-up-projects/references/stacks.md, greenfield.md, workbench.md, tests/test_workbench.py), AC-017. Why: the user asked for it mid-build and chose to add it here. Effect: one more part after B7.
- 2026-11-13 skills/setting-up-projects/references/greenfield.md What: the root commands.test line says it runs in verify and CI. Why: AC-002 changed that behaviour. Effect: docs only.
- 2026-11-13 workbench.json What: the manifest is workbench.json, not workbench.yaml. Why: the plugin is stdlib-only Python with no YAML parser, and a hand-rolled YAML subset would be a parser over untrusted input. Effect: same fields and location; change.md and backlog.md now say workbench.json.
- 2026-11-13 B2 internal functions What: sdlc_scopes.is_workbench, check_name, manifest, workbench_scopes; scaffold.cmd_workbench (behind the planned scaffold.py workbench command, which also gained 'list'); doctor.check_workbench. Why: AC-004–006; is_workbench needs the manifest too (need_manifest=False only for the command writing the first entry) so a config key alone never switches modes. Effect: internal API; the user-facing surface is the planned workbench command and config key.
- 2026-11-13 B3 docs/specs/06-guardrails-and-conventions.md, docs/specs/03-scope-and-review.md, docs/wiki/Hooks.md What: GRD-FR-016 and SCO-FR-026 route from a workbench too; new GRD-FR-033 for the read-only guard; the wiki's hookify and role-guard rows say both. Why: they restated the routing rule B3 changed (AC-007, AC-008). Effect: docs only.
- 2026-11-13 B3 hooks/sdlc_scopes.py workbench_of; role_guard.written, read_only_problem, hits/shell_write folders mode What: internal helpers behind AC-008 and AC-009; sdlc_scopes.py is the one file B3 adds to its plan. Why: state.py and the guard read an app repo's back-reference and the manifest through the shared parser. Effect: internal API only.
- 2026-11-13 B3 hooks/role_guard.py bundle_problem What: its tool dispatch moved into written(), which read_only_problem shares; behaviour unchanged. Why: one write check for recorded tests and read-only repos (AC-008). Effect: internal only; test_recorded_tests passes unchanged.

## Open questions
-
