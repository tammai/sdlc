# 2026-11-25-m-ui-evidence-leftovers
Status: done
Process: 3
Change: .sdlc/2026-11-25-m-ui-evidence-leftovers/change.md   (this feature's record for people)
Track: M   (sized up because: —; footprint: 5 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-25
Base: fe5326d
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: fe5326d tree 32cf37820af3663114035c40736dc31bf114cb99
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [ ] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline: this session builds it, one part

## Handoff
- ship.ui_evidence/_ui_evidence/ui_globs: scripts/ship.py:311-375

## Tasks
1. **Git failure as not checked; app repo globs** — AC-001 AC-002
   - Files: `scripts/ship.py`
2. **Docs: ADR 0032 deletions and app repo globs, setup profile wording** — AC-002
   - Files: `docs/adr/0032-opt-in-guards.md`, `skills/setting-up-projects/references/advisory.md`, `CHANGELOG.md`, `.sdlc/todo.md`
3. **Tests** — AC-001 AC-002
   - Files: `tests/test_ui_evidence.py`

## Public Surface
- none

## Test lock
- `tests/test_ui_evidence.py` sha256:71bb7edd128d82b497baaf7e697c7ecf3d1714f6473e18dfb1a8325b4254449e

## Gate log
- 2026-11-25 Stage 1: pass — plan not stopped for approval: low-risk M
- 2026-11-25 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-25 Base What: moved from 644b83b to fe5326d. Why: PR #144 merged into main under this feature's uncommitted work. Effect: drift compares against the merge; #144 touched none of this change's files.

## Open questions
-
