# 2026-11-23-s-mode-tickets
Status: done
Process: 3
Track: S   (footprint: 5 files)
Risk: high
Top model: opus
Base: c4ce416
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: c4ce416 tree ff82f4a0b23b861780eab065fd5f0e305a370544
Current: Stage 4 – Ship

## Tasks
1. **Mode tickets** — AC-001 AC-002
   - Files: `hooks/sdlc_scopes.py`, `hooks/trust_anchor.py`, `tests/test_modes.py`, `docs/specs/02-orchestration.md`, `.sdlc/todo.md`

## Public Surface
- none

## Gate log
- 2026-11-23 Stage 1: pass
- 2026-11-23 Stage 2: pass — security review r1+r2 over both changes

## Deviations
- 2026-11-23 hooks/security_reminder_hook.py, tests/test_workbench.py, NOTICE.md, CHANGELOG.md, open_regular What: the first two belong to 2026-11-23-s-rewake-unchanged-finding on the same branch; open_regular is this change's new helper. Why: the two changes share branch 2026-11-23-todo-mode-tickets so one security review covers them. Effect: none.

## Open questions
-
