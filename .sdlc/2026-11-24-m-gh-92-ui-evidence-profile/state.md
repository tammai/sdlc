# 2026-11-24-m-gh-92-ui-evidence-profile
Status: done
Process: 3
Change: .sdlc/2026-11-24-m-gh-92-ui-evidence-profile/change.md   (this feature's record for people)
Track: M   (sized up because: —; footprint: 14 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-24
Base: a75171f
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: a75171f tree 4ab350bcf8985c3160aacbd3b5b0e8109107dfbe
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [x] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline: this session builds it, one part

## Handoff
-

## Tasks
1. **UI evidence at Ship** — AC-001 AC-002
   - Files: `scripts/ship.py`, `hooks/sdlc_scopes.py`, `tests/test_ui_evidence.py`
2. **Profile** — AC-003
   - Files: `scripts/scaffold.py`, `hooks/session_status.py`, `commands/setup.md`, `hosts/skills/setup/SKILL.md`, `skills/setting-up-projects/SKILL.md`, `skills/setting-up-projects/references/advisory.md`
3. **Flow and docs** — AC-001
   - Files: `skills/orchestrator/references/ui-work.md`, `skills/orchestrator/references/flow.md`, `docs/adr/0032-opt-in-guards.md`, `docs/adr/README.md`, `docs/wiki/Configuration.md`, `docs/specs/10-ui-design-system.md`, `CHANGELOG.md`

## Public Surface
- config `guards.ui_evidence` — AC-001
- command `scaffold.py profile` — AC-003

## Test lock
- `tests/test_ui_evidence.py` sha256:6e74b1dc53c3751ea62864560dd8a1cd0cde433dde29e38dd05e4b854af160d0

## Gate log
- 2026-11-24 Stage 1: pass — plan not stopped for approval: low-risk M
- 2026-11-24 Stage 2: pass — full suite 903: one size failure fixed by trimming (test_plugin_files passes)
- 2026-11-24 Stage 3: fail — code review r1 FAIL (H1, M1-M4); fixing test first, profile renamed to checks (M5)
- 2026-11-24 Stage 2: pass — r1 fixes in; full suite 904 OK
- 2026-11-24 Stage 3: pass — code review r2 PASS; its N1 fixed test first, N2-N5 ticketed
- 2026-11-24 Stage 2: pass — r2 follow-ups fixed; full suite 905 OK
- 2026-11-24 Stage 3: pass — code review on opus: r1 FAIL (fixed), r2 PASS (follow-ups fixed)

## Deviations
- 2026-11-24 internal helpers What: IMAGES, ui_evidence (scripts/ship.py), PROFILES, cmd_profile (scripts/scaffold.py). Why: the UI evidence check and the profile command. Effect: module-internal; the public surface is the config key and the command.
- 2026-11-24 test-change tests/test_ui_evidence.py What: AC-001's test adds a config that empties or breaks areas.ui; AC-003's test uses the renamed command and checks shared keeps approval always; a test for the manual reason is added beside AC-002's. Why: code review r1 H1, M1, M3, M4, M5. Effect: the tests pin each.
- 2026-11-24 code review r1 fixes What: areas.ui is the plugin's globs plus config's (H1); any error in the check refuses as ui_evidence_not_checked and git failing refuses (M1); a workbench's branched repos are checked against the workbench's areas.ui (M2, no test); checks shared never lowers approval (M3); scaffold.py profile renamed checks, setup's advisory.md relates it to the monorepo's profile (M5); flow.md's screenshot line (M6); changed files filtered as Ship commits them (L1); guard list from GUARDS (L3); effective values reported (L4); a linked ui folder refused (L5, no test); docs/wiki/Project-setup.md. Why: code review r1. Effect: M2 and L5 have no test of their own.
- 2026-11-24 internal helpers r2 What: ui_globs, changed_since, _ui_evidence, commits (scripts/ship.py), cmd_checks replacing cmd_profile (scripts/scaffold.py). Why: code review r1. Effect: module-internal; the surface is the config key and scaffold.py checks.
- 2026-11-24 test-change tests/test_ui_evidence.py What: a workbench test (an app repo's UI change without evidence is refused), the screenshot test renamed test_screenshots_ship_and_are_listed, ProfileTest renamed ChecksTest. Why: code review r2 N1, F1, F4. Effect: the workbench test was written after the M2 fix; taking that fix out makes it fail.
- 2026-11-24 skills/setting-up-projects/SKILL.md, .sdlc/todo.md What: SKILL.md planned but left as it was (its 20,000-character limit; advisory.md holds the question); todo.md gains the review's tickets. Why: tests/test_plugin_files.py and code review r2. Effect: none.

## Open questions
-
