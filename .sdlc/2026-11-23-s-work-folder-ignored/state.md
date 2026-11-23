# 2026-11-23-s-work-folder-ignored
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: low
Top model: opus
Base: 9e151cd
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: 9e151cd tree 69afff12586075bc1a7292fe7c7bd8cbf6fa5552
Current: Stage 4 – Ship

## Tasks
1. **init makes .sdlc/.work ignore itself** — AC-001
   - Files: `scripts/scaffold.py`, `tests/test_scaffold.py`

## Public Surface
- none

## Gate log
- 2026-11-23 Stage 1: pass
- 2026-11-23 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-23 Task 1 What: the fix was written before the record; red ran against HEAD's scaffold.py. Why: found by the 3.15.0 smoke test and fixed test first in the session. Effect: AC-001 red recorded on the old code.

## Open questions
-
