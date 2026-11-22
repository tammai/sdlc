# 2026-11-22-s-json-loaders-refuse-links
Status: done
Process: 3
Track: S   (footprint: 6 files)
Risk: high
Top model: opus
Base: eaf6ad1
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: eaf6ad1 tree c037832a7702269dd4d31d8507bb522097c45c71
Current: Stage 4 – Ship

## Tasks
1. **Config, lock and manifest readers refuse a link out of the repo** — AC-001 AC-002
   - Files: `scripts/scaffold.py`, `hooks/sdlc_scopes.py`, `hooks/sdlc_layout.py`, `scripts/objects.py`, `tests/test_scaffold.py`, `tests/test_sdlc_layout.py`

## Public Surface
- export `read_repo_json` — AC-002

## Gate log
- 2026-11-22 Stage 1: pass
- 2026-11-22 Stage 2: pass — review deferred to the end-of-push pass

## Deviations
- 2026-11-22 setup What: the repo isn't set up for sdlc. Why: the plugin's own repo. Effect: the full suite runs by hand on Python 3.10.
- 2026-11-22 track What: S with a 6-file footprint (one reader, four call sites). Why: the user's one-day fixes-only push; one intent. Effect: no M plan or approval stop; review deferred by the user to the end-of-push pass.
- 2026-11-22 hooks/sdlc_scopes.py _inside What: helper behind read_repo_json. Why: AC-002. Effect: internal.
- 2026-11-22 order AC-001 AC-002 What: red step ran after the code, with the four source files put back to HEAD. Why: speed in the one-day push. Effect: same proof.

## Open questions
-
