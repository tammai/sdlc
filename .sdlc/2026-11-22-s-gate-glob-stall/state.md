# 2026-11-22-s-gate-glob-stall
Status: done
Process: 3
Track: S   (footprint: 4 files)
Risk: high
Top model: opus
Base: d7f4979
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: d7f4979 tree 6995d77c73a0831c88882f25dcc5173a788b66b5
Current: Stage 4 – Ship

## Tasks
1. **Bounded glob matching** — AC-001
   - Files: `hooks/globmatch.py`, `hooks/sdlc_review_gate.py`, `scripts/doctor.py`, `tests/test_globmatch.py`

## Public Surface
- export `glob_match` — AC-001

## Gate log
- 2026-11-22 Stage 1: pass
- 2026-11-22 Stage 2: pass — review deferred to the end-of-push pass

## Deviations
- 2026-11-22 setup What: the repo isn't set up for sdlc. Why: the plugin's own repo. Effect: the full suite runs by hand on Python 3.10.
- 2026-11-22 hooks/globmatch.py expand_braces judgeable Glob What: helpers of the new module. Why: AC-001. Effect: internal to the hooks and doctor.

## Open questions
-
