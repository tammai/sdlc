# ADR 0004: UI follows the project's design system

- **Status:** Accepted, 2026-10-22.
- **Deciders:** Tâm Mai.

## Context

The lifecycle covered spec, code and tests, but nothing about how UI looks or behaves. Left alone, agents produce the same generic screen everywhere: gradients, glassmorphism, emoji icons, a centered hero with three feature cards, filler copy, raw hex values and hand-rolled buttons next to the project's own components. Most UI work arrives as S or M track, which skip Stage 2, so a design-stage-only fix would miss it.

## Decision

Record the design system once, then act at the same points as [ADR 0003](0003-guard-against-over-engineering.md): while writing, automatically, and in review.

| Where | Mechanism |
|---|---|
| Setup | `design-system` step for projects with UI: `.sdlc/design-system.md` points at the existing system (library, tokens, components, icons, patterns). With none, propose one mainstream library and a minimal token set. User-owned, approved by the user. |
| While writing | Generated rule `sdlc-ui.md`, scoped by the new `areas.ui`: tokens only, reuse components, a named AI-slop list, states, accessibility. |
| Automatic | Seeded guardrail `sdlc-ui-hardcoded-values` **warns** on raw colors, arbitrary Tailwind values and inline styles in UI files. |
| Stages 1–2 | The spec names states and copy; the design maps screens to the system, and a new component or token is a Complexity Tracking row. |
| Stage 6 | New `sdlc:ui-reviewer` on every track when the diff touches `areas.ui`; off-system values, slop, missing states and accessibility blockers are High. |
| Health | `/sdlc:doctor` warns when a set-up repo has UI files and no design system. |

Rejected: **blocking** hard-coded values on write. Blocks in this plugin are kept for destructive actions and secrets; token files, SVGs and third-party CSS would produce false blocks, and the Stage 6 gate already stops off-system UI from shipping. Rejected: **automatic screenshots** in Stage 5. The plugin can't assume a browser tool or a runnable dev server, so the visual check runs only when the user asks and the tools are there.

## Consequences

- **Good:** the agent sees the design system and the slop list while writing UI, and every UI diff gets a design-system review, including S-track fixes.
- **Costs:** one more setup step and approval for UI projects; one more reviewer in Stage 6 for UI diffs; regex warnings will sometimes fire on legitimate values (they warn, they don't block).
- **Limits:** taste is judged by an agent against a written system, not by a designer. The guardrail only knows web syntax; native UI relies on the rule and the reviewer.
