# 2026-11-23-s-doctor-root-scope
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: low
Top model: opus
Base: 37bb365
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: 37bb365 tree ff135c89fe6d92dfccfd3f9502ba314772be7b84
Current: Stage 4 – Ship

## Tasks
1. **cmd_contract adds the root pseudo-scope** — AC-001
   - Files: `scripts/scaffold.py`, `tests/test_doctor.py`

## Public Surface
- none

## Gate log
- 2026-11-23 Stage 1: pass
- 2026-11-23 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-23 scripts/doctor.py What: the commands line counts packages without the root pseudo-scope. Why: the contract now lists it, so "defined for N packages" would count it. Effect: same count as before.

## Open questions
-
