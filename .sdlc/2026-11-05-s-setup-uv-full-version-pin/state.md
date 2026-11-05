# 2026-11-05-s-setup-uv-full-version-pin
Status: done
Process: 3
Track: S   (footprint: 3 files)
Risk: low
Top model: opus
Base: 1825a53
Owner: 
Tool: claude-code
Verified: 1825a53 tree 237458c22f8fe6a4f00cc4f84844aee383f1606c
Current: Stage 4 – Ship

## Tasks
1. **Pin setup-uv by full version** — AC-001
   - Files: `scripts/scaffold.py`, `tests/test_project_templates.py`, `CHANGELOG.md`

## Public Surface
- none

## Gate log
- 2026-11-05 Stage 1: pass
- 2026-11-05 Stage 2: pass — no review: low risk, no surface

## Deviations
- 2026-11-05 setup What: ran without sdlc setup and without asking. Why: unattended run, no one to ask; this plugin repo has no .sdlc/config.json. Effect: none on the change.
- 2026-11-05 tests What: full suite ran on Python 3.15, not 3.10. Why: the runner has only 3.15 (py -0). Effect: 425 tests, 6 failures in test_ralph_stop (jq not installed), the same 6 fail on the base commit; none touched by this change.

## Open questions
-
