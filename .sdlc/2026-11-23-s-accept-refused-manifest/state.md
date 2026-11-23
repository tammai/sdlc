# 2026-11-23-s-accept-refused-manifest
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: low
Top model: opus
Base: ce2c003
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: ce2c003 tree ce67c4f9dc37a6bf258f136c3cf520308f2dc3f8
Current: Stage 4 – Ship

## Tasks
1. **An accept says when sdlc's scripts refuse the manifest** — AC-001
   - Files: `hooks/read_only_watch.py`, `tests/test_workbench.py`

## Public Surface
- none

## Gate log
- 2026-11-23 Stage 1: pass
- 2026-11-23 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-23 Task 1 What: the fix was written before the record; red ran against HEAD's hooks/read_only_watch.py. Why: found by the 3.15.0 smoke test and fixed test first in the session. Effect: AC-001 red recorded on the old code.

## Open questions
-
