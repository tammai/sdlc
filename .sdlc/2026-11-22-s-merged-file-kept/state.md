# 2026-11-22-s-merged-file-kept
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: low
Top model: opus
Base: 4d076b9
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: 4d076b9 tree 9d85df57d6dcf95fcec8d5135aa20bf335a6d930
Current: Stage 4 – Ship

## Tasks
1. **Keep merged files in upgrade, eject and render** — AC-001 AC-002 AC-003
   - Files: `scripts/scaffold.py`, `tests/test_scaffold.py`

## Public Surface
- none

## Gate log
- 2026-11-22 Stage 1: pass
- 2026-11-22 full suite: OK on Python 3.10
- 2026-11-22 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-22 setup What: the repo isn't set up for sdlc (the plugin's own repo). Why: as earlier features here. Effect: the full suite runs by hand on Python 3.10.
- 2026-11-22 test-change tests/test_scaffold.py What: AC-003 expects exit 1, not 2. Why: a damaged lock exits 1 with its message in this script (Refused is 2). Effect: same AC.

## Open questions
-
