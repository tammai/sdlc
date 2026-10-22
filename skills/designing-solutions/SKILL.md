---
name: designing-solutions
description: Use after the spec is approved and before planning tasks, to explore the existing codebase, choose an architecture, and write design.md plus research, data model and interface contracts for the feature.
---

# Designing Solutions

Structure adapted from GitHub Spec Kit's `plan` command (MIT); exploration and architecture use the `code-explorer` and `code-architect` agents from Anthropic's feature-dev plugin (Apache-2.0). See NOTICE.md.

## Inputs

- `.sdlc/<feature>/spec.md` (approved), `.sdlc/<feature>/brainstorm.md` if any
- `.sdlc/constitution.md` if present
- Template: `${CLAUDE_PLUGIN_ROOT}/templates/design-template.md`

## Steps

0. **Check team knowledge.** If `knowledge/index.md` exists, open the decisions, conventions and gotchas that touch the areas this feature changes. Treat recorded decisions as constraints unless the user agrees to revisit one (then plan a new decision doc that supersedes it).
1. **Explore the codebase.** Dispatch 2–3 `sdlc:code-explorer` agents in parallel, each on a different angle (similar existing features, the layers this feature touches, testing and conventions). Ask each for the 5–10 files most worth reading; read those files yourself.
2. **Technical context.** Copy the template to `.sdlc/<feature>/design.md`. Fill Technical Context from what the repo actually uses. Mark real unknowns `NEEDS CLARIFICATION`. Performance, scale and constraints cite an SC id or say `n/a`: never design for numbers the spec doesn't contain.
3. **Constitution check.** List each MUST principle and whether the design complies. An unjustified violation is a stop; a justified one goes in Complexity Tracking.
4. **Phase 0 – research** → `.sdlc/<feature>/research.md`. For every `NEEDS CLARIFICATION` and every new dependency: Decision / Rationale / Alternatives considered. Use current docs for library APIs rather than memory.
5. **Phase 1 – architecture.**
   - Dispatch 2–3 `sdlc:code-architect` agents with different priorities: **minimal change** (reuse what exists, fewest new files); **minimal + one extension**, only if a specific FR/SC strains the minimal one (name it in the brief); **pragmatic balance**. Every brief includes the spec's Non-Goals.
   - Compare them in a short table: files touched, *new* modules/abstractions/dependencies, risk, effort, fit with conventions.
   - **Recommend the minimal approach** unless you can name the FR/SC it fails. "Cleaner", "more extensible" or "future-proof" is not a reason; a requirement is.
   - **The user picks.** Record the chosen approach and at least one rejected alternative with the reason.
6. **Phase 1 – artifacts** (only those that apply):
   - `data-model.md`: entities, fields, relationships, validation rules, state transitions (from the spec's entities)
   - `contracts/`: interfaces the feature exposes — API endpoints, events, CLI, public module types
   - `quickstart.md`: how to run and manually verify the feature end to end
7. **Complexity Tracking** (always, not only on constitution violations): one row for every new module/package, layer, abstraction (interface, base class, factory, registry, plugin point, generic helper), dependency, service/process, config key or env var, and data store/table. Each row names the FR/SC that needs it and why the simpler alternative was rejected. A row with no requirement means the addition comes out of the design. Anything listed in the spec's Non-Goals must not appear.
8. **Re-check the constitution** against the final design. Fill the Project Structure section with the real directories (delete the unused template options).

## Gate

- Every functional requirement and success criterion in the spec maps to part of the design.
- Every Complexity Tracking row cites a requirement; nothing from Non-Goals is designed in.
- Every risk has a mitigation.
- No `NEEDS CLARIFICATION` left in design.md.
- **The user approves the design** before planning starts.

Next step: `sdlc:writing-plans` (save to `.sdlc/<feature>/plan.md`), then `sdlc:analyzing-consistency`.
