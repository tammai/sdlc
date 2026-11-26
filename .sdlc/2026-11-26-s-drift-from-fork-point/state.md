# 2026-11-26-s-drift-from-fork-point
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: low
Top model: opus
Base: daa80ef
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: daa80ef tree a45c574e3bc3ded46a6c78073933c3a5033ac12f
Current: Stage 4 – Ship

## Tasks
1. **Base fixes that fit their cause** — AC-001 AC-002 AC-003 AC-004 AC-005
   - Files: `scripts/verify.py`, `scripts/diff_stats.py`, `tests/test_verify.py`, `tests/test_workbench.py`

## Public Surface
- export `scan_errors` — AC-004
- export `_git_check` — AC-005

## Gate log
- 2026-11-26 Stage 1: pass
- 2026-11-26 Stage 2: pass — code review 5 rounds; round 5 waived by removal

## Deviations
- 2026-11-26 Task 1 What: the fix was written before the record; AC-001's red ran with HEAD's scripts/verify.py swapped in. Why: proven test first in the session. Effect: red recorded on the old code.
- 2026-11-26 AC-002 What: dropped as a criterion; its test stays as a Must-never-break guard. Why: it guards behaviour the old code already had, so no red step can record it. Effect: the full suite runs it.
- 2026-11-26 Tests What: run on Python 3.9.6, not 3.10. Why: no Python 3.10 on this machine; 3.9 is the floor. Effect: none expected.
- 2026-11-26 Scope What: the fork-point detection was dropped after four review rounds; the change keeps the base-check fixes those rounds found and Troubleshooting R16a. Why: every ref it reads is the agent's to move; the user chose to drop it at the round cap. Effect: ACs renumbered to AC-001 to AC-005; red re-recorded against #153's code.
- 2026-11-26 waived round 5 What: R5-1 (Base: resolved to its full sha in part) was closed by removing that part, as the user chose at the round cap; no round 6. Why: the change only shrank (the partial resolution removed, AC-005 narrowed to the C locale). Effect: the C locale and the base-check fixes ship; a commit/blob-ambiguous short id fails closed.

## Open questions
-
