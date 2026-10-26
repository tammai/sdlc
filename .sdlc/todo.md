# Todo

## Open

- [ ] Let a project configure which sdlc stages run, e.g. skip the security review or the PR/CI step — not built yet; stage gates are fixed today in the orchestrator (2026-10-25)
- [ ] Add a Definition of Done to the setup step so the agent knows when a job is done — not built yet (2026-10-25)
- [ ] Add a team mode to the orchestrator: when active, role-based agents drive the sdlc stages — not built yet (2026-10-25)
- [ ] Add an advisory-only use case: the sdlc skills and agents as aids, with no hooks, gates or guardrails, for projects that already have a workflow that would conflict; setup asks which mode to use — not built yet; related to the configurable-stages item above (2026-10-26)

## Done

- [x] Update the Discover stage to always write down the complete intent and the brainstorming, in a form both a human and a machine can review easily — done: the spec's `## Intent` section (four-phases feature, Define) (2026-10-26)
