# 2026-11-23-s-objects-avoid-none
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: low
Top model: opus
Base: 5627186
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: 5627186 tree 1845fb1954e5596b25f4763e195af413abe5a9b5
Current: Stage 4 – Ship

## Tasks
1. **None under Avoid means nothing to avoid** — AC-001
   - Files: `scripts/objects.py`, `tests/test_objects.py`

## Public Surface
- none

## Gate log
- 2026-11-23 Stage 1: pass
- 2026-11-23 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-23 Task 1 What: the fix was written before the record; red ran against HEAD's scripts/objects.py. Why: found by the 3.15.0 smoke test and fixed test first in the session. Effect: AC-001 red recorded on the old code.

## Open questions
-
