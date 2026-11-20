# 2026-11-20-s-stepper-ship-stage
Status: done
Process: 3
Track: S   (footprint: 3 files)
Risk: low
Top model: opus
Base: c48fb03
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: 715a497 tree 16f8b7c9bac36310c95edfc2e76f4d3312953423
Current: Stage 4 – Ship

## Tasks
1. **Keep a done feature at Ship on the bar while it is the one shown; let the next start replace it** — AC-001
   - Files: `plugins/sdlc-stepper/hooks/sdlc.ts`, `plugins/sdlc-stepper/hooks/register.tsx`, `plugins/sdlc-stepper/types/index.d.ts`, `plugins/sdlc-stepper/tests/stepper.test.tsx`, `plugins/sdlc-stepper/README.md`, `CHANGELOG.md`

## Public Surface
- none

## Gate log
- 2026-11-20 Stage 1: pass
- 2026-11-20 Stage 2: pass — UI review: round 1 FAIL fixed, round 2 PASS; UI-H1 ticketed

## Deviations
- 2026-11-20 parseState What: returns a done feature at Ship too, marked shipped: true. Why: ship.py marks the record done as Ship starts, so the caller has to see it to keep it on the bar. Effect: its one caller, load() in register.tsx, keeps a shipped feature only when it is the view already shown.
- 2026-11-20 makeView What: takes an optional shipped flag (default false) and sets View.shipped. Why: beginDraft and noteUpdate need to know that the shown feature is a shipped one, so the next start can replace it. Effect: existing callers are unchanged.

## Open questions
-
