# Slice B2 plan: orchestrator split, state.py, Build

Spec FR-01, FR-02, FR-10, AC 3, 4, 9 · Backlog B2. Instructed only (skill text); checks: `claude plugin validate .`, `hosts.py check`, the suite.

## Tasks

1. `skills/orchestrator/SKILL.md` becomes the core (~1,000 words): stage loading and resume, tracks and tiers, `Build:`, `state.py` usage, what several stages share (blocking questions, stage header, verified tree, diff facts, reviewer brief, round cap), rules and hard stops. (FR-02)
2. `skills/orchestrator/references/`: `start.md` (with the state template), `stage-1-discover.md` … `stage-8-ship.md`, `stage-9-11.md`, `lite-flow.md`, `backlog-slices.md`, `ui-work.md`, `review-brief.md`; every state change through `state.py`. (FR-02)
3. `Build: native | subagent` in the template, the core, Stage 3, Lite and slices. (FR-01)
4. `state.py deviation` (the invariants CI check reads `## Deviations`) and `slice block` (autopilot) — test `test_a_deviation_goes_under_deviations`.
5. Docs: spec 02 (citations note, ORC-FR-013, 027–029), runbook, CONTRIBUTING, guidebook, CHANGELOG. (FR-10: no hook changes; hosts copies `skills/` whole.)

## Public Surface

- state field `Build:` — FR-01
- skill reference files under `skills/orchestrator/references/` — FR-02
