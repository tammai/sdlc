# 2026-11-05-s-doctor-gitignore-check-ignore
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: low
Top model: opus
Base: f951499
Owner: 
Tool: claude-code
Verified: f951499 tree 3830d746e52423ec1c088d316c90ba02ddca71a8
Current: Stage 4 – Ship

## Tasks
1. **Ask git whether .sdlc/.work/ and the contract files are ignored** — AC-001 AC-002 AC-003
   - Files: `scripts/doctor.py`, `tests/test_doctor.py`

## Public Surface
- none

## Gate log
- 2026-11-05 Stage 1: pass
- 2026-11-05 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-05 scripts/doctor.py What: added private helper not_ignored(root, patterns). Why: check_repo asks git check-ignore per pattern, with a .gitignore-lines fallback outside git. Effect: internal to doctor.py, no caller outside it.
- 2026-11-05 tests What: suite and AC commands run on python3 (3.15), not py -3.10; the red step recorded exit 103 (no 3.10 installed). Why: this runner has no Python 3.10. Effect: real red seen by hand (3 assertion failures before the fix); cp1252 crashes below 3.15 not exercised here.
- 2026-11-05 setup What: brief.py and the scaffold setup prompt skipped (session status: setup none). Why: unattended run, brief.py needed approval and no one could answer the setup question. Effect: read doctor.py and its tests directly instead.

## Open questions
-
