# 2026-11-05-s-ship-origin-head-feature-branch
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: low
Top model: opus
Base: 58a2c04
Owner: 
Tool: claude-code
Verified: 58a2c04 tree 55494dfa2261de73ff1731a2a7b224737949689e
Current: Stage 4 – Ship

## Tasks
1. **Stage on the feature branch, settle the branch before the state moves** — AC-001 AC-002
   - Files: `scripts/ship.py`, `tests/test_ship.py`

## Public Surface
- none

## Gate log
- 2026-11-05 Stage 1: pass
- 2026-11-05 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-05 Setup and suite. What: worked with sdlc setup none (no .sdlc/config.json, so verify ran only the AC tests) and ran the full suite on Python 3.15, not 3.10; 6 test_ralph_stop failures are jq missing on this machine. Why: unattended run, nobody to ask about setup; py -3.10 exits 103 (no 3.10 installed); jq is not installed. Effect: test_ship.py 9/9 pass; full suite 404 run, only the 6 jq-dependent tests fail, unrelated to ship.py.

## Open questions
-
