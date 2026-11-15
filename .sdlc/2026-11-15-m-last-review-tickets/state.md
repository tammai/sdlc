# 2026-11-15-m-last-review-tickets
Status: done
Process: 3
Change: .sdlc/2026-11-15-m-last-review-tickets/change.md   (this feature's record for people)
Track: M   (sized up because: four tickets across eject, upgrade-plan and the write helpers; footprint: 3 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-15
Base: 8d8d374
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: 8d8d374 tree 6067b5f312c804e956382dbd3ded91bdd14ff553
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [ ] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline

## Handoff
- cmd_eject unmerge scripts/scaffold.py:2493; convention_updates :965; _write_atomic and write_json's retry loop

## Tasks
1. **Eject report copies, malformed convention entry reported, _write_atomic keeps mode and links, retry only the rename** — AC-001 AC-002 AC-003 AC-004
   - Files: `scripts/scaffold.py`, `tests/test_stack_blueprints.py`, `CHANGELOG.md`

## Public Surface
- none

## Gate log
- 2026-11-15 Stage 1: pass — plan not stopped for approval: low-risk M
- 2026-11-15 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-15 test-change tests/test_stack_blueprints.py test_lock_root_is_checked_on_read What: expects one error item for the entry instead of an empty list. Why: AC-002 (R2-05): a malformed entry is reported, not skipped. Effect: still never read or offered as a diff.
- 2026-11-15 scripts/scaffold.py _write_atomic What: during_replace marks the rename's permission error; the write resolves links and keeps the mode by default. Why: AC-003, AC-004. Effect: write_json, which already passed its own mode and target, is unchanged.

## Open questions
-
