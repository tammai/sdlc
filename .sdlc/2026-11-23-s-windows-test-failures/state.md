# 2026-11-23-s-windows-test-failures
Status: done
Process: 3
Track: S   (footprint: 6 files)
Risk: low
Top model: opus
Base: c8fc4b5
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: c8fc4b5 tree 74a317187781cd9d2bb31707a2d8cdcdb830e815
Current: Stage 4 – Ship

## Tasks
1. **Background SDK install outside the project; Windows-safe tests** — AC-001
   - Files: `hooks/security_reminder_hook.py`, `tests/test_security_reminder.py`, `tests/helpers.py`, `tests/test_workbench.py`, `tests/test_scaffold.py`, `tests/test_modes.py`

## Public Surface
- none

## Gate log
- 2026-11-23 Stage 1: pass
- 2026-11-23 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-23 Task 1 What: the fix was written before the record; the red step ran against HEAD's hook. Why: the cause was found by running the failing tests. Effect: AC-001 red recorded on the old code.

## Open questions
-
