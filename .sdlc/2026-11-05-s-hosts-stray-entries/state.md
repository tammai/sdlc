# 2026-11-05-s-hosts-stray-entries
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: low
Top model: opus
Base: f951499
Owner: 
Tool: claude-code
Verified: f951499 tree 0d5ac9bd10ed0187953f263d55db7a144979270a
Current: Stage 4 – Ship

## Tasks
1. **Ignore stray entries in hosts/skills and hosts/cursor/agents** — AC-001 AC-002 AC-003
   - Files: `scripts/hosts.py`, `tests/test_hosts.py`

## Public Surface
- none

## Gate log
- 2026-11-05 Stage 1: pass
- 2026-11-05 Stage 2: pass — no review: low risk, no surface

## Deviations
- 2026-11-05 tests What: suite run on Python 3.15, not 3.10 as CLAUDE.md asks. Why: only 3.15 is installed on this runner (py -0). Effect: cp1252 crashes below 3.15 aren't exercised here; CI covers other versions.
- 2026-11-05 setup What: no .sdlc/config.json; went on without /sdlc:setup. Why: unattended run, nobody to ask. Effect: verify uses detected commands.
- 2026-11-05 suite What: full suite 408 run, 6 test_ralph_stop failures. Why: jq is not installed on this runner; the same 6 fail on the base commit. Effect: none from this change; also added a CHANGELOG Fixed entry (footprint 3 files).

## Open questions
-
