# 2026-11-26-s-ship-baseline-config-path
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: low
Top model: opus
Base: 13e2a6b
Owner: 
Tool: claude-code
Verified: 13e2a6b tree 6000e8986fb032260b93545532675676d81b5e00
Current: Stage 4 – Ship

## Tasks
1. **Ship reads config's baseline path** — AC-001 AC-002 AC-003 AC-004 AC-005 AC-006 AC-007 AC-008 AC-009 AC-010 AC-011
   - Files: `scripts/ship.py`, `tests/test_ship.py`

## Public Surface
- export `baseline_path` — AC-001
- export `baseline_failures` — AC-001
- export `baseline_match` — AC-001
- export `baseline_rows` — AC-001
- export `configured_baseline` (takes `root`) — AC-008
- export `in_repo` — AC-008
- export `verified` (adds optional `base`) — AC-003

## Gate log
- 2026-11-26 Stage 1: pass
- 2026-11-26 Stage 2: pass — code review 3 rounds, PASS

## Deviations
- 2026-11-26 Task 1 What: the fix was written before the record; AC-001's red ran with HEAD's scripts/ship.py swapped in. Why: the bug was proven test first in the session before the record. Effect: AC-001 red recorded on the old code.
- 2026-11-26 AC-002 What: red also ran with HEAD's scripts/ship.py swapped in. Why: as Task 1. Effect: AC-002 red recorded on the old code.
- 2026-11-26 Tests What: run on Python 3.9.6, not 3.10. Why: no Python 3.10 on this machine; 3.9 is the floor and older still. Effect: none expected.

## Open questions
-
