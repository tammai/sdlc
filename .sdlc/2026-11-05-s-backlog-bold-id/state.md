# 2026-11-05-s-backlog-bold-id
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: low
Top model: opus
Base: f951499
Owner: 
Tool: claude-code
Verified: f951499 tree aacefa9542100915a29e603c51d246691ffa0d81
Current: Stage 4 – Ship

## Tasks
1. **Read a bold backlog ID as its plain B<n>** — AC-001 AC-002
   - Files: `scripts/backlog.py`, `tests/test_backlog.py`

## Public Surface
- none

## Gate log
- 2026-11-05 Stage 1: pass
- 2026-11-05 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-05 scripts/backlog.py What: ID read only when the cell is a bare B<n> in emphasis/code marks, not re.search(B\d+). Why: search read 'B1 & calc' as B1 and broke autopilot's command-line guard (test_autopilot). Effect: same fix for bold IDs, guard kept.
- 2026-11-05 tests What: suite run on python3 3.15, not 3.10. Why: no Python 3.10 on this runner. Effect: 400 pass; 6 test_ralph_stop fail before and after the change because jq isn't installed here.

## Open questions
-
