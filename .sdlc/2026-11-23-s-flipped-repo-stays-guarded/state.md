# 2026-11-23-s-flipped-repo-stays-guarded
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: high
Top model: opus
Base: 11f24db
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: 11f24db tree b016d74b266d07068ad6ff3cbc6db53c7a4375e1
Current: Stage 4 – Ship

## Tasks
1. **The guard reads the watch's read-only record** — AC-001
   - Files: `hooks/role_guard.py`, `tests/test_workbench.py`

## Public Surface
- none

## Gate log
- 2026-11-23 Stage 1: pass
- 2026-11-23 Stage 2: pass — security r1 FAIL fixed, r2 PASS

## Deviations
- 2026-11-23 Task 1 What: the fix was written before the record; red ran against HEAD's role_guard. Why: found live in the smoke test, fixed test first in the session. Effect: AC-001 red recorded on the old code.

## Open questions
-
