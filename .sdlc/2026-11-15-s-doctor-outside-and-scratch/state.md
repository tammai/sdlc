# 2026-11-15-s-doctor-outside-and-scratch
Status: done
Process: 3
Track: S   (footprint: 4 files)
Risk: low
Top model: opus
Base: 0f4abc8
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: 0f4abc8 tree d7a2cb11b5da6d9d365340ab76b1edd0cc894dbd
Current: Stage 4 – Ship

## Tasks
1. **Doctor outside warning, scratch only when it exists, cached root and sweep** — AC-001 AC-002
   - Files: `scripts/doctor.py`, `scripts/scaffold.py`, `tests/test_doctor.py`, `tests/test_stack_blueprints.py`, `CHANGELOG.md`

## Public Surface
- none

## Gate log
- 2026-11-15 Stage 1: pass
- 2026-11-15 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-15 scripts/scaffold.py _real_root _sweep_temps What: the root's real path is cached per process; the sweep still runs on every save, not once per process. Why: a once-per-process sweep misses a leftover that appears while the process runs, and a folder glob is cheap. Effect: Decisions row 3 holds for the root only.
- 2026-11-15 test-change tests/test_stack_blueprints.py test_save_temp_stays_in_scratch What: makes .sdlc/.work first. Why: AC-002: scratch is used only once it exists. Effect: same guarantee.

## Open questions
-
