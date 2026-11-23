# 2026-11-23-s-team-guard-followups
Status: done
Process: 3
Track: S   (footprint: 3 files)
Risk: low
Top model: opus
Base: ac79fa1
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: ac79fa1 tree 54f170f2ded542a3ecb49abb3694ca4f7b9bcef0
Current: Stage 4 – Ship

## Tasks
1. **Builder denied findings and state; objects link judged where it leads; team_place only for team agents** — AC-001 AC-002
   - Files: `hooks/role_guard.py`, `tests/test_team_mode.py`, `docs/specs/03-scope-and-review.md`

## Public Surface
- none

## Gate log
- 2026-11-23 Stage 1: pass
- 2026-11-23 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-23 hooks/role_guard.py What: new helper builder_off_limits() for AC-001. Why: one canon()-spelling predicate for the reviewers' reports and the state file. Effect: the builder's writes there are denied.

## Open questions
-
