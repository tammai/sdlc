# 2026-11-23-s-waiver-refusal-names-tests
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: low
Top model: opus
Base: a8eb0fa
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: a8eb0fa tree c03e3018ccf7b3c9d1c809e32e2e006b68a6af75
Current: Stage 4 – Ship

## Tasks
1. **The refusal names what the waiver can't cover** — AC-001
   - Files: `scripts/ship.py`, `tests/test_ship.py`

## Public Surface
- none

## Gate log
- 2026-11-23 Stage 1: pass
- 2026-11-23 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-23 Task 1 What: the fix was written before the record; red ran against HEAD's ship.py. Why: found by the 3.15.0 smoke test and fixed test first in the session. Effect: AC-001 red recorded on the old code.

## Open questions
-
