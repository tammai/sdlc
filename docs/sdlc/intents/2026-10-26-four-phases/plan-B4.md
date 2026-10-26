# Plan B4: docs on four phases, stale-docs audit

Spec: [spec.md](spec.md) · FR-12 · AC 9 · docs only, no tests

1. README (tracks, gates, phases table, always-on hooks, `/sdlc:deploy`), CONTRIBUTING (layout tree, phase-rule link), runbook, prd, NOTICE, guidebook, playbook, `docs/specs` 01–11 and README, ADR 0010 and the ADR index, CHANGELOG (Unreleased, plus the cycle's earlier notes reworded to phases).
2. Diagrams: `sdlc_full_flow`, `sdlc_tracks_full_stage_tree`, `sdlc_orchestrator_decision_tree`, `sdlc_plugin_layers` relabelled and rendered (light and dark).
3. Wording that names stages in agents (verifier, ui-reviewer, mirrored to Cursor), `/sdlc:status` (reports the phase), project templates (rules, baseline, hookify rule, CI invariants message, spec/design/checklist templates), script and hook messages, plugin manifests (regenerated for every host).
4. Stale-docs audit over: Stage 2/3/6/7/9/10/11, Discover, Implement, PR / CI, Operate, execution method, 11 stages, `stage-N-*.md`, `lite-flow.md`. Left on purpose: dated CHANGELOG entries, ADRs, the prd's dated live-check notes, notes on the internal stage numbers, the old-Lite Stage 6 freshness case, and the vendored `writing-plans` handoff text.

## Public Surface
- none (docs and wording)
