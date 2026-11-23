# 2026-11-23-s-runbook-nested-sdlc-folders
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: high
Top model: opus
Base: f7a6201
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: f7a6201 tree 681bc3a19e10fd9120e3d19d93115c2988a71e38
Current: Stage 4 – Ship

## Tasks
1. **Bar .claude and .sdlc at any depth** — AC-001
   - Files: `scripts/scaffold.py`, `tests/test_sdlc_layout.py`

## Public Surface
- none

## Gate log
- 2026-11-23 Stage 1: pass
- 2026-11-23 Stage 2: pass — security review r1+r2 PASS

## Deviations
- 2026-11-23 hooks/sdlc_scopes.py, scripts/objects.py What: AC-002 added (instruction files, odd names) with a shared odd_name check. Why: security review L-2, L-3 found them in the same function. Effect: runbook_path refuses CLAUDE.md, CLAUDE.local.md, AGENTS.md and control/format characters.

## Open questions
-
