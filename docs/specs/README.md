# Specs

What the plugin does, one capability per file, extracted from the code, skills, agents and tests at v1.3.0. The product view is the [PRD](../prd.md); why things are built this way is in the [ADRs](../adr/README.md).

Numbered in the order you meet them: setup first, then the lifecycle and its stages, then what runs across all of them.

| # | Spec | Capability | When |
|---|---|---|---|
| 01 | [Setup, upgrade and eject](01-setup-upgrade-eject.md) | Project setup, commands per package, generated CI, upgrades, eject | Once per repo, then per plugin release |
| 02 | [Orchestration](02-orchestration.md) | Tracks, stages, gates, hard stops, state and resume | Every piece of work |
| 03 | [Scope tracing and review](03-scope-and-review.md) | Scope traced from spec to diff; review facts and severity | Stages 1–3, 6 |
| 04 | [Verification](04-verification.md) | Verifier rounds with red-green, the on-demand QA tester, the freshness hook, the baseline | Stage 5 |
| 05 | [Security](05-security.md) | Security-guidance hooks and the Stage 7 pass | Always on; Stage 7 |
| 06 | [Guardrails and conventions](06-guardrails-and-conventions.md) | Policy rules, hookify engine and guardrails, lint snippets | Always on |
| 07 | [Knowledge](07-knowledge.md) | Three-tier knowledge, promotion, audit | Stages 1 and 11 |
| 08 | [Health and status](08-health-and-status.md) | `/sdlc:doctor` and `/sdlc:status` | Any time |
| 09 | [Autonomous loop](09-autonomous-loop.md) | `/sdlc:ralph-loop` | Optional, Stage 4 |
| 10 | [UI and the design system](10-ui-design-system.md) | Design system recorded at setup; UI rule, guardrail and reviewer | Setup; Stages 1, 2, 6 for UI work |

Requirement IDs (`SET-FR-001`, `ORC-FR-001`, …) are stable: they don't change if a spec is renumbered.

## How to read a requirement

Each requirement says how it's guaranteed:

| Tag | Meaning |
|---|---|
| `[enforced]` | Code or a hook does it, and a test in `tests/` proves it (cited as `file › test`) |
| `[instructed]` | A skill, agent or command prompt tells Claude to do it; nothing checks it mechanically (cited as the file) |
| `[vendored]` | Upstream behavior of bundled code, not covered by this repo's tests |

When changing behavior, update the spec and, for `[enforced]` items, the cited test.
