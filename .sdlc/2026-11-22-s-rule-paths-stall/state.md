# 2026-11-22-s-rule-paths-stall
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: low
Top model: opus
Base: 61e901a
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: 61e901a tree 9a7eab9468e93e08b25937902d380b855c470d15
Current: Stage 4 – Ship

## Tasks
1. **Rule paths judged with one regex** — AC-001
   - Files: `scripts/doctor.py`, `tests/test_doctor.py`

## Public Surface
- none

## Gate log
- 2026-11-22 Stage 1: pass
- 2026-11-22 Stage 2: pass — no review fired

## Deviations
- 2026-11-22 setup What: the repo isn't set up for sdlc. Why: the plugin's own repo. Effect: the full suite runs by hand on Python 3.10.
- 2026-11-22 scripts/doctor.py glob_regex GLOB_LIMITS What: helper and constant replacing expand_braces. Why: AC-001. Effect: internal; objects.py's glob_matches call keeps its signature.

## Open questions
-
