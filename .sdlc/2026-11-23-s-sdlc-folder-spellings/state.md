# 2026-11-23-s-sdlc-folder-spellings
Status: done
Process: 3
Track: S   (footprint: 4 files)
Risk: high
Top model: opus
Base: b13caca
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: b13caca tree d1b7864d2c6b11abf3ea9433edf09ade4ec75f1e
Current: Stage 4 – Ship

## Tasks
1. **One dot-folder spelling rule** — AC-001, AC-002, AC-003
   - Files: `hooks/sdlc_scopes.py`, `scripts/scaffold.py`, `scripts/objects.py`, `tests/test_sdlc_layout.py`

## Public Surface
- export `dot_segment` — AC-001

## Gate log
- 2026-11-23 Stage 1: pass
- 2026-11-23 Stage 2: pass — security review r1+r2 PASS over both changes

## Deviations
- 2026-11-23 scripts/scaffold.py (impeccable_hook_off), tests/test_scaffold.py What: changed by 2026-11-23-s-impeccable-local-link, not this change. Why: both changes share branch 2026-11-23-todo-fixes so one security review covers them. Effect: none on this change; that record owns them.

## Open questions
-
