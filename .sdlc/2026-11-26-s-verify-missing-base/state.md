# 2026-11-26-s-verify-missing-base
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: low
Top model: opus
Base: 13e2a6b
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: 13e2a6b tree 7eceb233c33862bc370147455a9d0211173c2847
Current: Stage 4 – Ship

## Tasks
1. **Verify fails cleanly on a missing Base** — AC-001 AC-002 AC-003
   - Files: `scripts/verify.py`, `tests/test_verify.py`, `tests/test_workbench.py`

## Public Surface
- export `DriftUnchecked` — AC-001
- export `unresolved` — AC-002

## Gate log
- 2026-11-26 Stage 1: pass
- 2026-11-26 Stage 2: pass — code review 2 rounds, PASS

## Deviations
- 2026-11-26 Task 1 What: the fix was written before the record; AC-001's red ran with HEAD's scripts/verify.py swapped in. Why: the bug was proven test first in the session. Effect: AC-001 red recorded on the old code.
- 2026-11-26 Tests What: run on Python 3.9.6, not 3.10. Why: no Python 3.10 on this machine; 3.9 is the floor. Effect: none expected.
- 2026-11-26 tests/test_workbench.py What: AC-002's test is in the workbench tests. Why: it needs their workbench fixture. Effect: none.

## Open questions
-
