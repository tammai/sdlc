# 2026-11-22-s-workbench-control-files
Status: done
Process: 3
Track: S   (footprint: 5 files)
Risk: high
Top model: opus
Base: 319092a
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: 319092a tree 07ea53030c4a36792952b32acb7e0eb7ba3d0edc
Current: Stage 4 – Ship

## Tasks
1. **Control files can't unguard** — AC-001 AC-002
   - Files: `hooks/sdlc_scopes.py`, `hooks/read_only_watch.py`, `tests/test_workbench.py`, `docs/specs/06-guardrails-and-conventions.md`, `docs/wiki/Hooks.md`

## Public Surface
- export `SEEDED_MARKER` — AC-002

## Gate log
- 2026-11-22 Stage 1: pass
- 2026-11-22 Stage 2: pass — review deferred to the end-of-push pass

## Deviations
- 2026-11-22 setup What: the repo isn't set up for sdlc. Why: the plugin's own repo. Effect: the full suite runs by hand on Python 3.10.

## Open questions
-
