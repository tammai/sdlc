# 2026-11-22-s-control-files-no-env
Status: done
Process: 3
Track: S   (footprint: 3 files)
Risk: high
Top model: opus
Base: 79c98b7
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: 79c98b7 tree e550bdbdfeb05f48c807c0e3697ce3b872d6d8ec
Current: Stage 4 – Ship

## Tasks
1. **Watch finds seeded workbench without env** — AC-001
   - Files: `hooks/read_only_watch.py`, `tests/test_workbench.py`, `skills/setting-up-projects/references/workbench.md`

## Public Surface
- none

## Gate log
- 2026-11-22 Stage 1: pass
- 2026-11-22 Stage 2: pass — review deferred

## Deviations
- 2026-11-22 setup What: the repo isn't set up for sdlc. Why: the plugin's own repo. Effect: the full suite runs by hand on Python 3.10.

## Open questions
-
