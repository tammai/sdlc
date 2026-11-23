# 2026-11-23-s-team-workbench-learn
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: low
Top model: opus
Base: 0463268
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: 0463268 tree eec3964dcd97cc191a5ebf81f4e1c135dda34485
Current: Stage 4 – Ship

## Tasks
1. **shipping() judges a writable workbench repo's path from its folder** — AC-001
   - Files: `hooks/role_guard.py`, `tests/test_team_mode.py`

## Public Surface
- none

## Gate log
- 2026-11-23 Stage 1: pass
- 2026-11-23 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-23 hooks/role_guard.py What: new helper app_shipping() for AC-001. Why: judge a writable workbench repo's path from its own folder. Effect: the releaser files lessons there.

## Open questions
-
