# 2026-11-22-s-fixed-writers-refuse-links
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: high
Top model: opus
Base: f00bb43
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: f00bb43 tree 277b2bd3a58d58ebb9a7f8f0b5b9f8e3fdc31099
Current: Stage 4 – Ship

## Tasks
1. **Fixed-name writers refuse links out of the repo or into .git** — AC-001 AC-002
   - Files: `scripts/scaffold.py`, `tests/test_scaffold.py`

## Public Surface
- none

## Gate log
- 2026-11-22 Stage 1: pass
- 2026-11-22 full suite: OK, 5 skipped (python3.10); verify PASS; security review r1 FAIL, r2 PASS
- 2026-11-22 Stage 2: pass — security review: r1 FAIL fixed, r2 PASS

## Deviations
- 2026-11-22 setup What: the repo isn't set up for sdlc (the plugin's own repo). Why: as earlier features here. Effect: the full suite runs by hand on Python 3.10.
- 2026-11-22 scripts/doctor.py scripts/context_diet.py tests/test_scaffold.py What: the readers of the fixed files (settings, .gitignore, CLAUDE.md and rules for the AGENTS block) are checked too; AC-003 and AC-004 added, AC-002 widened. Why: security review r1 H-1, H-2, M-1, M-2 (same class). Effect: a linked file reads as absent everywhere sdlc opens it.
- 2026-11-22 scripts/scaffold.py link_problem fixed_problem fixed_target read_fixed_json FIXED_FILES; scripts/context_diet.py linked_out What: module helpers behind the one containment check on fixed-name files. Why: AC-001 to AC-004 and review r1 H-2 (one reader for every open). Effect: internal to the scripts (doctor and context_diet call them); no public surface.
- 2026-11-22 order AC-003 AC-004 What: their red step ran after the code, with scripts/ stashed back to Base. Why: they came from review r1 and were first seen failing by hand. Effect: same proof.

## Open questions
-
