# 2026-11-23-l-team-mode
Status: done
Process: 3
Change: .sdlc/2026-11-23-l-team-mode/change.md   (this feature's record for people)
Track: L   (sized up because: —; footprint: 14 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-23
Base: 87f2095
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: 87f2095 tree 9e45f8e2579db37d51cc95576659d7893f0f6438
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [x] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline, one part

## Handoff
- Role guard pattern: hooks/role_guard.py problem() (REVIEWERS, qa-tester); model router ALWAYS_TOP in hooks/model_router.py

## Tasks
1. **team switch and status** — AC-001
   - Files: `scripts/scaffold.py`, `hooks/session_status.py`, `tests/test_team_mode.py`
2. **Role guard and router** — AC-002 AC-003 AC-004 AC-005
   - Files: `hooks/role_guard.py`, `hooks/model_router.py`
3. **Agents and flow text** — AC-006
   - Files: `agents/analyst.md`, `agents/builder.md`, `agents/releaser.md`, `skills/orchestrator/SKILL.md`, `commands/start.md`, `skills/orchestrator/references/flow.md`, `skills/setting-up-projects/references/advisory.md`, `commands/setup.md`
4. **Docs** — AC-006
   - Files: `docs/wiki/Configuration.md`, `CHANGELOG.md`, `.sdlc/todo.md`, `CONTRIBUTING.md`, `docs/wiki/Hooks.md`

## Public Surface
- command `team` — AC-001
- config `team` — AC-001

## Test lock
- `tests/test_team_mode.py` sha256:f6de6fbb923ff11f34eaae2ae89b04f9193d9c0143891045ccddc08d6f299d37

## Gate log
- 2026-11-23 Stage 1: pass — plan approved by the user (approach A, as written)
- 2026-11-23 Stage 2: pass
- 2026-11-23 review: ran code (L, Public Surface), self-chosen: L
- 2026-11-23 Stage 2: pass
- 2026-11-23 review r1: FAIL (H1-H3, M1-M5); fixed test first; L1 handoffs, L2, L4, F1-F5 fixed in passing; L3 (builder may write reviewer reports and the state file by hand) left as a ticket
- 2026-11-23 Stage 2: pass
- 2026-11-23 review r2: FAIL (N1, N2); user chose one more fix round; N1-N4, L1, L4, F1-F4 fixed test first; L2 (ship.py advances to 4 itself) and L3 (workbench app repo Learn paths) noted, not changed
- 2026-11-23 Stage 2: pass
- 2026-11-23 review r3: FAIL (H1); user chose one more fix round; H1, M1, L1-L3 fixed test first; F1 (AC-002 narrowed by review) goes in ## Review
- 2026-11-23 Stage 3: pass — review: 4 rounds, round 4 PASS; lows ticketed

## Deviations
- 2026-11-23 test-change tests/test_team_mode.py What: the analyst test sets docs_dir (its docs-folder change file isn't in the docs folder otherwise). Why: the test asserted a path the role guard can't know without it. Files: docs/wiki/Skills-and-agents.md, hosts copies of the agents; cmd_team.
- 2026-11-23 cmd_team What: the team command's function. Why: the declared command team. Effect: none beyond the declared surface.
- 2026-11-23 review r1 fixes: tests added to tests/test_team_mode.py for H1-H3, M2, M3, M5, L2 (more paths for AC-002/003/004, no-state router case, status negatives)
- 2026-11-23 test-change tests/test_team_mode.py What: more paths for AC-002/003/004 (config, baseline, findings, constitution, other spellings, Learn's places), a no-state router case for AC-005, status negatives and advisory dropping team for AC-001, builder/setup text checks for AC-006. Why: code review r1 (H1-H3, M1-M3, M5, L2).
- 2026-11-23 What: role_guard.team_place() and shipping(), helpers for the analyst/builder/releaser rules. Why: review r1 H1-H3 and M2: path tests in canon() spelling, one predicate for the change file. Effect: the role rules deny config, findings and shared docs to the analyst, any spelling of a change file to the builder, and allow the releaser Learn's places.
- 2026-11-23 test-change tests/test_team_mode.py What: AC-002 rows for scaffold folders under .sdlc/ (ci), the hooks' .work records, Windows short names and streams; AC-003 row for a short name of .sdlc itself; AC-005 fable with no state. Why: code review r2 (N1-N4, L1).
- 2026-11-23 What: team_place() narrowed (feature-name folders only, an existing old-layout folder only with a state file, no .sdlc/.work/, 'odd' for short names and streams), shipping() folds case only where canon() does, objects path from config dropped, router denies fable for a no-state analyst. Why: review r2 N1-N4, L1, L4, F4. Effect: the analyst can't write scaffold folders, hook records or odd spellings; the builder is denied any short-name or stream path.
- 2026-11-23 test-change tests/test_team_mode.py What: AC-002 rows for an old-layout folder holding only change.md, a config-named objects path, reserved .sdlc names and new folders with docs_dir set; AC-003 rows for product paths with ~1 and :; AC-004 hookify rows. Why: code review r3 (H1, M1, L1-L3).
- 2026-11-23 What: role_guard odd() (short names and streams only where they could reach the record), RESERVED .sdlc names, 'stray' place, objects_files() reading config through sdlc_scopes, an old-layout folder holding change.md counts. Why: review r3 H1, M1, L1-L3. Effect: the analyst can re-edit a drafted change file before state.py new and write a config-named objects file; the builder's product paths with ~1 or : go through.

## Open questions
-
