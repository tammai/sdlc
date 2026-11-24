# 2026-11-24-m-gh-92-guarded-changes
Status: done
Process: 3
Change: .sdlc/2026-11-24-m-gh-92-guarded-changes/change.md   (this feature's record for people)
Track: M   (sized up because: —; footprint: 14 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-24
Base: d35c13e
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: d35c13e tree 30f7b8ac9f4911a5aa68eb3ccf266b9ba98fc5aa
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
1. **Guarded items, the allow record and verify's check** — AC-001 AC-002 AC-003
   - Files: `hooks/guarded_changes.py`, `hooks/sdlc_scopes.py`, `hooks/hooks.json`, `hosts/hook.py`, `scripts/verify.py`, `tests/test_guarded_changes.py`
2. **Ship log and setup** — AC-002
   - Files: `scripts/ship.py`, `scripts/scaffold.py`, `hooks/session_status.py`, `commands/setup.md`, `hosts/skills/setup/SKILL.md`
3. **Flow and docs** — AC-001
   - Files: `skills/orchestrator/SKILL.md`, `commands/start.md`, `hosts/skills/start/SKILL.md`, `skills/orchestrator/references/flow.md`, `skills/orchestrator/references/s-track.md`, `docs/adr/0032-opt-in-guards.md`, `docs/adr/README.md`, `docs/wiki/Configuration.md`, `docs/wiki/Hooks.md`, `docs/wiki/Limitations.md`, `docs/specs/04-verification.md`, `CHANGELOG.md`

## Public Surface
- config `guards.dependencies` — AC-001
- config `guards.lint_config` — AC-003

## Test lock
- `tests/test_guarded_changes.py` sha256:10cfcb9267be5ed49456ff478fc17a91775481492753f307c8e44bbb5fbf3684

## Gate log
- 2026-11-24 Stage 1: pass — plan not stopped for approval: low-risk M
- 2026-11-24 Stage 2: pass — code review r1 ran in Build (FAIL, fixed); full suite 900 OK
- 2026-11-24 Stage 3: fail — code review r2 FAIL (R2-H1, R2-H2); user chose one more fix round
- 2026-11-24 Stage 2: pass — round-3 fixes in; full suite 900 OK
- 2026-11-24 Stage 3: pass — code review r3 PASS; its R3-M1, R3-M2 fixed test first
- 2026-11-24 Stage 2: pass — r3 follow-ups fixed; full suite 900 OK
- 2026-11-24 Stage 3: pass — code review on opus: r1 FAIL, r2 FAIL (user granted r3), r3 PASS; all fixed test first

## Deviations
- 2026-11-24 internal helpers What: hooks/guarded_changes.py (git, changed_files, at_base, now, _json_names, _req_name, _toml_names, _pubspec_names, _gomod_names, _gemfile_names, dependency_names, _sections, short, items, load, unallowed, allowed_labels, main), guarded_failures in scripts/verify.py, guarded_allowed in scripts/ship.py. Why: the detection, the allow record and the two callers. Effect: module-internal; the public surface is the two config keys.
- 2026-11-24 test-change tests/test_guarded_changes.py What: AC-001's test adds an extras entry before a new pyproject dependency, a 4-space pubspec, a BOM package.json and a key that isn't a name; AC-002's adds one call with two questions, another feature's verify between, and Ship's Gate log; AC-003's adds taking back one of two allowed suppressions and a lint section header with a comment. Why: code review r1 H1, H2, H3, M2, M3, M5, M6. Effect: the tests pin each fixed case.
- 2026-11-24 code review r1 fixes without a test of their own What: M1 (a git timeout or failure is caught; ship reads the allowed items before anything moves), M4 (a workbench feature's branched repos are checked), M7 (files read only when their name matched; suppressions from one diff), M8 (diff --relative, show base:./path), M9 (rename detection in the suppression diff), L1-L4, H4 (the must-never-break line restated: the guards lookup is the one read). Why: each needs a git failure, a workbench or a large diff to reproduce. Effect: covered by reading; ticketed where a test would add value.
- 2026-11-24 internal helpers r2 What: NotChecked, Unreadable, decode, clean, _toml_lines, is_requirements, suppression_counts, is_allowed in hooks/guarded_changes.py. Why: code review r1. Effect: module-internal.
- 2026-11-24 test-change tests/test_guarded_changes.py What: AC-003's test adds another feature asking again for the same suppressions, a form-feed line with diff.noprefix set, and a setup.cfg [mypy-x.*] section; FILES gains setup.cfg and src/b.py. Why: code review r2 R2-H1, R2-H2, R2-M1, R2-M2 (the user chose one more fix round). Effect: the tests pin each.
- 2026-11-24 code review r2 fixes What: allows scoped per feature (R2-H1); INI section headers any column-0 bracket line (R2-H2); the suppression diff splits on newlines only, fixes its prefixes and quoting, and counts a file it didn't name from both versions (R2-M1, R2-M2); verify and ship catch any error as guarded_not_checked; a typed allow prefers the active feature (R2-M3, no test); changed_files returns the untracked set (L1); wider control-character filter (L5); _count helper. Why: code review r2. Effect: R2-M3 and L5 have no test of their own.
- 2026-11-24 test-change tests/test_guarded_changes.py What: AC-003's test adds an added line starting '++ ' before a suppression, and a file moved with git mv; FILES gains src/c.ts. Why: code review r3 R3-M1, R3-M2. Effect: the move case was written with the header fix, so it wasn't seen failing on its own (the '++ ' case was).

## Open questions
-
