# 2026-11-22-s-lexer-denies-unreadable
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: high
Top model: opus
Base: 41ff30c
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: 41ff30c tree 357889dbcca54439b48a85bf683ae138552d0f1c
Current: Stage 4 – Ship

## Tasks
1. **Lexer denies unreadable syntax** — AC-001
   - Files: `hooks/role_guard.py`, `tests/test_workbench.py`

## Public Surface
- none

## Gate log
- 2026-11-22 Stage 1: pass
- 2026-11-22 Stage 2: pass — review deferred

## Deviations
- 2026-11-22 setup What: the repo isn't set up for sdlc. Why: the plugin's own repo. Effect: the full suite runs by hand on Python 3.10.
- 2026-11-22 hooks/role_guard.py Unreadable What: exception class, a kind of TooDeep. Why: AC-001. Effect: internal to role_guard.

## Open questions
-
