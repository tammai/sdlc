# 2026-11-15-m-config-merge-and-containment
Status: done
Process: 3
Change: .sdlc/2026-11-15-m-config-merge-and-containment/change.md   (this feature's record for people)
Track: M   (sized up because: scaffold.py, tests and two docs; footprint: 4 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-15
Base: 09cefca
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: 09cefca tree cf51b2fa97af00376d7c39bde2c1c0805cb87478
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [x] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline

## Handoff
- Project.save and merged_lock scripts/scaffold.py:276; merge_into :196 (LOCK_RECORDS); write_json :76; _temp_copy :1571; file_state :304; cmd_render :691; upgrade-plan loop :2322; eject_plan containment; cmd_conventions containment :824

## Tasks
1. **Config merge, object lists whole, save temps in .sdlc/.work, inside_repo helper in file_state, upgrade-plan, render, eject, conventions** — AC-001 AC-002 AC-003
   - Files: `scripts/scaffold.py`, `tests/test_stack_blueprints.py`
2. **Docs** — AC-001
   - Files: `CHANGELOG.md`, `docs/specs/01-setup-upgrade-eject.md`

## Public Surface
- none

## Gate log
- 2026-11-15 Stage 1: pass — plan not stopped for approval: low-risk M
- 2026-11-15 Stage 2: pass — verify PASS; suite 607 OK
- 2026-11-15 review: ran code (failure modes: concurrent use, crash mid-write, untrusted paths), not asked: low risk
- 2026-11-15 Stage 2: pass — r1 fixes; suite 607 OK
- 2026-11-15 Stage 2: pass — r2 mediums fixed; suite 607 OK (a first run hung once after test_autopilot; not reproduced)
- 2026-11-15 Stage 3: pass — r2 PASS; Review recorded

## Deviations
- 2026-11-15 scripts/scaffold.py inside_repo SCRATCH write_json _write_atomic _temp_copy What: the shared containment helper (file_state, render, upgrade-plan, eject_plan and conventions use it, replacing two copies), the scratch-folder temp parameter threaded through the write helpers. Why: AC-002, AC-003. Effect: none outside scaffold.py.
- 2026-11-15 CHANGELOG.md docs/specs/01-setup-upgrade-eject.md What: config merge, scratch temps and the outside state described. Why: the stale-docs audit. Effect: docs only.
- 2026-11-15 review r1 fix scripts/scaffold.py swap_ui_guardrail cmd_record agents convention_updates save write_json _sweep_temps cmd_upgrade_plan, tests/test_stack_blueprints.py, skills/setting-up-projects/references/upgrade.md, CHANGELOG.md, docs/specs/01-setup-upgrade-eject.md What: a guardrail reached through a link out is kept, never deleted (CC-01); record, the AGENTS mirror removal and convention_updates use inside_repo (CC-02); a config removed or broken meanwhile stops the save before either file is written (CC-04, CC-05); old .sdlc-tmp-* beside the lock and config are swept (CC-06); a scratch folder on another device falls back to a temp beside the file (CC-08); upgrade-plan always has outside, and upgrade.md has an Outside step, renumbered (CC-09, CC-16); a new lock is written in the checked shape; spec evidence and changelog notes (CC-15, CC-03, CC-11); test closes its files (CC-17); redundant scratch condition dropped (CC-14). Why: Review round 1. Effect: tests extended.
- 2026-11-15 review r2 fix scripts/scaffold.py cmd_upgrade_plan agents_state write_mirror save write_json merge_into _temp_copy, tests/test_stack_blueprints.py, docs/runbook.md, docs/specs/01-setup-upgrade-eject.md What: upgrade-plan checks outside before template_gone and for new files in add (CC2-01, CC2-03); agents_state never reads the mirror through a link (CC2-02); a read-only config refuses before the lock is written (CC2-04); an unusable scratch folder falls back to a temp beside the file (CC2-05, CC2-15); an outside mirror keeps its lock entry (CC2-09); a whole list or record replaced by the other command lands in the object this command holds (CC2-11); runbook, SET-FR-020 and a docstring (CC2-10, CC2-13). Why: Review round 2 mediums, fixed without another round. Effect: closed by verify.

## Open questions
-
