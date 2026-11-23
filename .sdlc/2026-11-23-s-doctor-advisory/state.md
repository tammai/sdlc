# 2026-11-23-s-doctor-advisory
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: low
Top model: opus
Base: 978bd88
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: 978bd88 tree 3a0d3c15626270598084e378663b312a3f0b2320
Current: Stage 4 – Ship

## Tasks
1. **Doctor names the mode and expects nothing advisory skips** — AC-001
   - Files: `scripts/doctor.py`, `tests/test_doctor.py`, `docs/wiki/Health-check.md`

## Public Surface
- none

## Gate log
- 2026-11-23 Stage 1: pass
- 2026-11-23 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-23 Task 1 What: the fix was written before the record; red ran against HEAD's scripts/doctor.py. Why: found by the 3.15.0 smoke test and fixed test first in the session. Effect: AC-001 red recorded on the old code.

## Open questions
-
