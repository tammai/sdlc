# 2026-11-22-s-hfs-dotgit
Status: done
Process: 3
Track: S   (footprint: 4 files)
Risk: high
Top model: opus
Base: b3c4493
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: b3c4493 tree e109feb6548e0b6dde6c1df53f5c62b8a18ebcb4
Current: Stage 4 – Ship

## Tasks
1. **HFS+ ignorables and case in .git checks** — AC-001 AC-002
   - Files: `scripts/scaffold.py`, `hooks/sdlc_scopes.py`, `tests/test_scaffold.py`, `tests/test_sdlc_layout.py`

## Public Surface
- none

## Gate log
- 2026-11-22 Stage 1: pass
- 2026-11-22 Stage 2: pass — review deferred to the end-of-push pass

## Deviations
- 2026-11-22 setup What: the repo isn't set up for sdlc. Why: the plugin's own repo. Effect: the full suite runs by hand on Python 3.10.
- 2026-11-22 scripts/scaffold.py HFS_IGNORED What: constant. Why: AC-001. Effect: internal.
- 2026-11-22 tests/test_stack_blueprints.py What: test_rules_folder_on_another_drive_is_refused builds Project before mocking commonpath. Why: since 1a4dfc0 Project checks the config with commonpath, so the all-paths mock refused it; that commit's module pick missed this test. Effect: the test checks the rules folder only, as meant.

## Open questions
-
