# 2026-11-26-s-drift-base-not-ancestor
Status: done
Process: 3
Track: S   (footprint: 3 files)
Risk: low
Top model: opus
Base: 81d0a97
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: 81d0a97 tree cd4f445b7b13ae326a3537bec6e3907b6362d718
Current: Stage 4 – Ship

## Tasks
1. **Drift refuses a Base not behind HEAD** — AC-001 AC-002
   - Files: `scripts/verify.py`, `tests/test_verify.py`, `tests/test_workbench.py`

## Public Surface
- export `behind_head` — AC-001
- export `shallow` — AC-001
- export `unresolved` (now through `_git_check`) — AC-001
- export `_git_check` — AC-001

## Gate log
- 2026-11-26 Stage 1: pass
- 2026-11-26 Stage 2: pass — code review 2 rounds, PASS

## Deviations
- 2026-11-26 Task 1 What: the fix was written before the record; red ran with HEAD's scripts/verify.py swapped in. Why: proven test first in the session. Effect: red recorded on the old code.
- 2026-11-26 Tests What: run on Python 3.9.6, not 3.10. Why: no Python 3.10 on this machine; 3.9 is the floor. Effect: none expected.

## Open questions
-
