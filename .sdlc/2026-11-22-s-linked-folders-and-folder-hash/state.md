# 2026-11-22-s-linked-folders-and-folder-hash
Status: done
Process: 3
Track: S   (footprint: 4 files)
Risk: high
Top model: opus
Base: 1a4dfc0
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: 1a4dfc0 tree cd5f4a0f4e8542ab8101001b7d1ba6fe2b3a2aab
Current: Stage 4 – Ship

## Tasks
1. **Linked rules/hookify folders named, folder hash as edited** — AC-001 AC-002
   - Files: `scripts/doctor.py`, `scripts/scaffold.py`, `tests/test_doctor.py`, `tests/test_scaffold.py`

## Public Surface
- none

## Gate log
- 2026-11-22 Stage 1: pass
- 2026-11-22 Stage 2: pass — review deferred to the end-of-push pass

## Deviations
- 2026-11-22 setup What: the repo isn't set up for sdlc. Why: the plugin's own repo. Effect: the full suite runs by hand on Python 3.10.
- 2026-11-22 scripts/doctor.py repo_glob What: helper. Why: AC-001. Effect: internal.

## Open questions
-
