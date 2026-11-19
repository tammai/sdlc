# 2026-11-19-m-stuck-turn-nudge
Status: done
Process: 3
Change: .sdlc/2026-11-19-m-stuck-turn-nudge/change.md   (this feature's record for people)
Track: M   (sized up because: —; footprint: 6 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-19
Base: 594334a
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: 594334a tree 105d9345e212b8bf7ef835e01065ab78ad2b329b
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [ ] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline: this session builds it, one part

## Handoff
- turn = between UserPromptSubmit events; state .sdlc/.work/stuck-turn.json keyed by session_id
- review cap check: review_rounds.capped(root, review_rounds.load(root)); Build: Current: Stage 2 via sdlc_layout.active

## Tasks
1. **The hook and its registration** — AC-001 AC-002 AC-003
   - Files: `hooks/stuck_turn.py`, `hooks/hooks.json`
2. **Tests** — AC-001 AC-002 AC-003
   - Files: `tests/test_stuck_turn.py`
3. **Docs** — AC-001
   - Files: `docs/wiki/Hooks.md`, `CHANGELOG.md`

## Public Surface
- none

## Test lock
- `tests/test_stuck_turn.py` sha256:b2d1d844c55a4faa6c3942909e2fdbe858045024c2b652f68fa34f39753ac2b1

## Gate log
- 2026-11-19 Stage 1: pass — plan not stopped for approval: low-risk M
- 2026-11-19 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-19 setup What: the repo isn't set up for sdlc (the plugin's own repo). Why: as earlier features here. Effect: the full suite runs by hand on Python 3.10.
- 2026-11-19 CONTRIBUTING.md What: the layout tree and the original-files list name stuck_turn.py. Why: the stale-docs audit lists both. Effect: one more docs file.
- 2026-11-19 hooks/stuck_turn.py signature, in_build, capped, main What: module-level helpers of the new hook. Why: they back AC-001 to AC-003. Effect: internal to a hook script nothing imports; no public surface.

## Open questions
-
