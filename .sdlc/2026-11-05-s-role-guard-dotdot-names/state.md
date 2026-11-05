# 2026-11-05-s-role-guard-dotdot-names
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: low
Top model: opus
Base: b7e0a69
Owner: 
Tool: claude-code
Verified: b7e0a69 tree 3a6ec1f93d66a441e8d844370696268fc90160e5
Current: Stage 4 – Ship

## Tasks
1. **Treat only .. and ../ as outside the project in role_guard** — AC-001
   - Files: `hooks/role_guard.py`, `tests/test_role_guard.py`

## Public Surface
- none

## Gate log
- 2026-11-05 Stage 1: pass
- 2026-11-05 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-05 Setup What: went on with sdlc setup none (no .sdlc/config.json). Why: unattended run, nobody to ask; this repo is the plugin itself. Effect: verify.py has no suite command, so the suite was run by hand.
- 2026-11-05 Tests What: the suite ran on python3 (3.15), not py -3.10. Why: no Python 3.10 on this runner. Effect: 407 pass, 5 skipped, 6 fail in tests/test_ralph_stop.py because jq is missing; the change adds no output or encoding code.
- 2026-11-05 AC-002 What: dropped as an AC, its test kept under Must never break. Why: a regression guard passes before the fix, so verify.py red refuses it. Effect: none on coverage.

## Open questions
-
