# PRD: sdlc, a Claude Code plugin for the whole software lifecycle

- **Status:** extracted from the codebase at v1.3.0, 2026-10-22. Describes what the plugin does, not a wish list; gaps are listed as such.
- **Owner:** Tâm Mai
- **Specs:** [docs/specs/](specs/README.md) · **Decisions:** [docs/adr/](adr/README.md)

## 1. Problem

AI coding agents are fast but unreliable in predictable ways. They skip specs and jump to code; they claim tests pass without running them, or on stale results; they add scope nobody asked for (abstractions with one implementation, options, dependencies, long narrating comments); their review is done by the same context that wrote the code; and what they learn in one session is lost, or piled into an ever-growing `CLAUDE.md` that costs every future session.

Teams that try to fix this assemble several plugins and conventions by hand, each with its own namespace, assumptions and gaps, and nothing ties them into one flow with gates.

## 2. Users

| User | Needs |
|---|---|
| **Developer using Claude Code** (primary; solo or in a team) | Take a request from idea to merged code with the right amount of process, decide at the moments that matter, and trust that "tests pass" is true |
| **Tech lead / AI-driven-development lead** | Roll out one consistent workflow to a team: shared guardrails and conventions, versioned upgrades, no per-person setup |
| **Teammates joining a set-up repo** | Install one plugin and get the repo's commands, rules and knowledge without re-explaining |
| **Claude, as the executing agent** | Clear stage instructions, the right skill or agent at each step, and machine feedback (hooks) when it drifts |

## 3. Goals

1. **One install, whole lifecycle:** spec, design, plan, implement, verify, review, security, ship, deploy, operate, learn, with no dependency on other plugins.
2. **Process sized to the work:** S, M or L tracks; the smallest track that fits by default.
3. **Gates with human decisions at the right points:** spec, design, execution method, merge, production deploy, migrations.
4. **Truthful verification:** an independent verifier per round, test results that can't go stale unnoticed, and old failures that don't block new work.
5. **Scope discipline:** every addition traced to a request from spec to diff; comment noise and over-engineering caught while writing and at review.
6. **Small, findable knowledge:** three loading tiers; lessons promoted, repeated corrections turned into rules.
7. **Safe adoption and evolution:** one-time setup for new and existing repos (including polyglot monorepos), versioned upgrades that never overwrite the team's edits, clean removal.

## 4. Non-goals

- Replacing the project's build, test or deploy tooling: sdlc runs the commands the repo already has.
- Bundling outside services (GitHub MCP, Linear, Sentry, Vercel, Playwright, …); stages point to them.
- Deep vulnerability scanning (Anthropic's `claude-security` is not bundled for licensing reasons).
- Generating CI for systems other than GitHub Actions.
- Telemetry or usage metrics.
- Supporting Windows without Git Bash.

## 5. Capabilities

| # | Capability | Spec | Commands / entry points |
|---|---|---|---|
| 01 | Project setup, upgrade, eject; commands per package; generated CI | [01-setup-upgrade-eject](specs/01-setup-upgrade-eject.md) | `/sdlc:setup`, `/sdlc:upgrade`, `/sdlc:eject` |
| 02 | Orchestrated lifecycle: tracks, 11 stages, gates, state, resume | [02-orchestration](specs/02-orchestration.md) | `/sdlc:start`, `/sdlc:status` |
| 03 | Scope tracing and review facts | [03-scope-and-review](specs/03-scope-and-review.md) | Stages 1–3, 6; `/sdlc:review-pr`, `scripts/diff_stats.py` |
| 04 | Verification: fresh verifier rounds, freshness hook, baseline | [04-verification](specs/04-verification.md) | Stage 5, `hooks/verify_freshness.py` |
| 05 | Security guidance | [05-security](specs/05-security.md) | always-on hooks, Stage 7 |
| 06 | Guardrails and conventions: policy rules, hookify, lint snippets | [06-guardrails-and-conventions](specs/06-guardrails-and-conventions.md) | `/sdlc:hookify*`, setup |
| 07 | Three-tier knowledge | [07-knowledge](specs/07-knowledge.md) | `/sdlc:revise-claude-md`, `/sdlc:knowledge-audit`, Stage 11 |
| 08 | Health check and status | [08-health-and-status](specs/08-health-and-status.md) | `/sdlc:doctor`, `/sdlc:status` |
| 09 | Autonomous loop for one well-specified task | [09-autonomous-loop](specs/09-autonomous-loop.md) | `/sdlc:ralph-loop` |

## 6. Key journeys

1. **Adopt in an existing repo:** install → `/sdlc:doctor` → `/sdlc:setup` (commands recorded, baseline, audit approved in batches, PR) → `/sdlc:start` a small fix.
2. **New project:** `/sdlc:setup <what you're building>` → approve the stack → skeleton, commands and CI pass on day one → first feature.
3. **Feature (M):** `/sdlc:start <request>` → spec with the `[inferred]` triage → plan with Public Surface → implement with TDD → verify rounds → review with diff facts → PR → merge on the user's word.
4. **Fix (S):** repro test → fix → verify → light review → PR.
5. **Plugin update:** `/sdlc:status` shows drift → `/sdlc:upgrade --dry-run` → `/sdlc:upgrade` on a branch → PR.
6. **Something feels off:** `/sdlc:doctor` → runbook procedure.

## 7. Requirements across capabilities

| ID | Requirement |
|---|---|
| PRD-1 | Everything ships in one plugin under the `sdlc:` namespace; no other plugin is needed for a core stage. |
| PRD-2 | Hooks and scripts are Python 3.9+ standard library only, and never fail the user's session on their own error. |
| PRD-3 | The plugin never merges, deploys to production, runs migrations, pushes or installs tools without the user's explicit go-ahead. |
| PRD-4 | Files the plugin writes into a project are tracked by ownership class; a user's edits are never overwritten without asking. |
| PRD-5 | Vendored material keeps its license and attribution (`NOTICE.md`, `licenses/`). |
| PRD-6 | Always-loaded context stays small: the plugin's always-on cost is about 4k tokens; `CLAUDE.md` is never written by the plugin. |
| PRD-7 | Works on macOS, Linux and Windows (Git Bash), and in single-package repos and polyglot monorepos. |

## 8. Success measures

The plugin collects no metrics; these are proposed for a team rollout and would be measured from repo artifacts.

| Measure | Source |
|---|---|
| Share of features whose final verify round passes on the first or second round | `## Verify rounds` in `state.md` |
| Deviations recorded per feature (skipped gates) | `## Deviations` in `state.md` |
| High-severity review findings for unrequested surface | `review.md`, `diff_stats.py` flags |
| `CLAUDE.md` line count over time (≤ 60) | repo history, `/sdlc:doctor` |
| Baseline size over time (should shrink) | `.sdlc/baseline.md` history |
| Repos on the current scaffold version | `/sdlc:status` drift per repo |

## 9. Constraints and dependencies

- **Runtime:** Claude Code with plugin support; `git`; Python 3.9+; `gh` for PR and code-review commands; Node for the brainstorm companion; Git Bash on Windows.
- **Model calls:** the security reviewer uses the Claude API (API key or Claude Code's OAuth token); without credentials those reviews are skipped.
- **Licensing:** MIT plugin; bundled Superpowers (MIT), GitHub Spec Kit (MIT), Anthropic Claude Code plugins (Apache-2.0).

## 10. Release scope (1.3.0)

Adds setup/upgrade/eject with per-package commands and generated CI, `/sdlc:doctor`, scope tracing, policy rules and guardrails, `diff_stats.py`, the baseline-aware verifier and per-package freshness, plus hookify, ralph and freshness fixes. See [CHANGELOG.md](../CHANGELOG.md).

## 11. Known gaps and open questions

- **Release smoke test (2026-10-22, headless sessions):** install, doctor, greenfield and brownfield setup, an S fix through Verify, guardrails, upgrade and eject all passed; hook warnings and block reasons do reach Claude. Not covered: Windows, and the model-based security review (no credentials reached the hooks in that environment).
- **Prompt-only guarantees:** most stage gates (spec checklist, design mapping, review severity) rely on skill instructions plus user approval; only freshness, guardrails, the surface check and file ownership are mechanical. Each spec marks which is which.
- **Security-guidance hooks** are vendored and not covered by this repo's tests.
- **Generated CI** has not run on GitHub yet (validated as YAML and against local toolchains only); `actionlint` not run.
