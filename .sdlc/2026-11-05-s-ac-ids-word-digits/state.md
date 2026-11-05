# 2026-11-05-s-ac-ids-word-digits
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: low
Top model: opus
Base: f951499
Owner: 
Tool: claude-code
Verified: f951499 tree 7fcb812a510a6e8236fb33f0182643c8dc3edd63
Current: Stage 4 – Ship

## Tasks
1. **Bound AC_SPAN so digits inside words are not AC numbers** — AC-001 AC-002
   - Files: `scripts/backlog.py`, `tests/test_backlog.py`

## Public Surface
- none

## Gate log
- 2026-11-05 Stage 1: pass
- 2026-11-05 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-05 Tests What: AC runs and the suite use python3 (3.15), not py -3.10 as CLAUDE.md asks. Why: no Python 3.10 is installed on this runner (py launcher exit 103), and sdlc setup is none here. Effect: cp1252 crashes that only 3.10 shows would not be caught; the change adds no output or encoding code.
- 2026-11-05 Suite What: 6 tests in tests/test_ralph_stop.py fail; the other 400 pass (5 skipped). Why: jq is not installed on this runner, so plugins/sdlc-extras/hooks/stop-hook.sh exits 127. Effect: none on this change, which touches only backlog.py's AC regex.

## Open questions
-
