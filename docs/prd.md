# PRD: sdlc, a Claude Code plugin for the whole software lifecycle

- **Status:** describes the plugin as it is (the version in `.claude-plugin/plugin.json` plus the "Unreleased" section of the [changelog](../CHANGELOG.md)), last checked 2026-10-28 for 2.0. Not a wish list; gaps are listed as such.
- **Owner:** Tâm Mai
- **Specs:** [docs/specs/](specs/README.md) · **Decisions:** [docs/adr/](adr/README.md)

## 1. Problem

AI coding agents are fast but unreliable in predictable ways. They skip specs and jump to code; they claim tests pass without running them, or on stale results; they add scope nobody asked for (abstractions with one implementation, options, dependencies, long narrating comments); their review is done by the same context that wrote the code; and what they learn in one session is lost, or piled into an ever-growing `CLAUDE.md` that costs every future session.

Teams that try to fix this assemble several plugins and conventions by hand, each with its own namespace, assumptions and gaps, and nothing ties them into one flow with gates. And process has a price in agent time, tokens and the user's attention.

## 2. Users

| User | Needs |
|---|---|
| **Developer using an AI coding agent** (primary; solo or in a team) | Take a request from idea to merged code with the right amount of process, decide at the moments that matter, and trust that "tests pass" is true |
| **Tech lead / AI-driven-development lead** | Roll out one consistent workflow to a team: shared guardrails and conventions, versioned upgrades, no per-person setup |
| **Teammates joining a set-up repo**, in the same or another agent | Install one plugin and get the repo's commands, rules and knowledge without re-explaining |
| **The executing agent** (later, role-based agents; a runner or control app) | Clear phase instructions, the right skill or agent at each step, what the next step needs on file, machine feedback (hooks) when it drifts, and machine-readable state |

## 3. Goals

1. **One install, whole lifecycle:** four phases (Define, Build, Review, Ship with Learn) plus on-request `/sdlc:deploy`, with no other plugin needed.
2. **Process sized to the work:** S, M or L, the smallest that fits. Sized by footprint, not risk words: a change confined to 1–2 files is S unless it's risky, and is never split into parts. Work with several distinct parts that won't fit one session runs as a backlog of parts, optionally unattended (autopilot).
3. **The same record at every size:** before any code, Define writes the change file for people (why, and what must be true, each criterion with its test) and the state file's plan sections for the agent (how: tasks, files, Public Surface); Review adds the change file's `## Review`. S writes them in a few lines each. Both files are kept for good.
4. **Few human decisions:** on M and L, one approval of the change file and the plan before the build and the choice of reviews after it; added scope, a reviewer and the builder disagreeing on a high finding, CI still red after one fix, merge, production deploy, migrations, anything irreversible. S has no stop before the build. The agent asks a question only when what, why or how isn't clear, one at a time.
5. **Truthful verification:** Build proves each acceptance criterion with `verify.py` (its test recorded failing before its code, passing now), and a bug is proven with a failing test before its fix. After the build the agent recommends reviews (security; code at default or high depth; UI whenever the diff touches `areas.ui`; the advisor where there is one; or none); S runs a fixed trigger list (none unless high risk, a sensitive, migration or UI path, or a declared public surface), M and L choose. Each chosen review runs once, fresh, on `opus`; high findings go back to Build, each fixed test first. Nothing merges unless the suite is green locally and on CI; no stale test results, and old failures don't block new work.
6. **Scope discipline:** every addition traced from request to diff; over-engineering and unrequested behaviour caught while writing and at review.
7. **Learning that sticks and stays small:** Learn on every feature adds fixed defects to `recurring-defects.md`, which Define and every reviewer read; knowledge in three loading tiers.
8. **Process that costs little more than the plain run:** in time and tokens against plain Claude on the same task, at most 1.2x on S, 1.5x on M and 2x on L, with hidden-test results held level. The builder works like plain Claude, with no review agents during the build; the cheap model tier is `sonnet` (never `haiku`), and the advisor runs only when it is a chosen review (§8).
9. **Quality at close to plain cost:** hidden-test and blind-review results held level while agent time, tokens and human touches fall (§8).
10. **Safe adoption in any supported agent:** setup for new and existing repos (polyglot monorepos too) in Claude Code, Codex, Cursor or Antigravity; upgrades that never overwrite the team's edits; clean removal.
11. **Machine-readable state:** one call per state change, and a control contract a runner or control app can follow.

## 4. Non-goals

- Replacing the project's build, test or deploy tooling: sdlc runs the commands the repo already has.
- Bundling outside services (GitHub MCP, Linear, Sentry, Vercel, Playwright, …); phases point to them.
- Deep vulnerability scanning (Anthropic's `claude-security` is not bundled for licensing reasons).
- Operating production: deploy is on request only; there is no operate phase.
- Generating CI for systems other than GitHub Actions.
- Telemetry or usage metrics.
- Claude Code on Windows without Git Bash.

## 5. Capabilities

| # | Capability | Spec | Commands / entry points |
|---|---|---|---|
| 01 | Project setup, upgrade, eject; commands per package; generated CI | [01-setup-upgrade-eject](specs/01-setup-upgrade-eject.md) | `/sdlc:setup`, `/sdlc:upgrade`, `/sdlc:eject` |
| 02 | Orchestrated lifecycle: tracks, four phases with the same record at every size, intent before code, how the build runs (inline, parts or parallel), hard stops, backlog parts, autopilot, trust anchor, resume, on-request deploy; a 1.x feature is refused with how to finish it | [02-orchestration](specs/02-orchestration.md) | `/sdlc:start`, `/sdlc:status`, `/sdlc:deploy`, `scripts/backlog.py`, `scripts/autopilot.py`, `hooks/model_router.py`, `hooks/trust_anchor.py` |
| 03 | Scope tracing, the review recommendation and review facts | [03-scope-and-review](specs/03-scope-and-review.md) | Define, Review; `/sdlc:review-pr`, `/sdlc:code-review`, `scripts/diff_stats.py` |
| 04 | Verification: `verify.py` in Build (each criterion's test from the change file recorded red, the verify plan, drift against the state file's plan), reused in Review; Review's 120 s command limit (a hook), freshness hook, baseline; green locally and on CI before merge; the black-box QA tester on request | [04-verification](specs/04-verification.md) | Build, Review, `hooks/verify_freshness.py` |
| 05 | Security: always-on guidance, commit review once per review-ready diff and only on a security-touched change, the security review recommended after the build on a security-touched change | [05-security](specs/05-security.md) | always-on hooks, `hooks/sdlc_review_gate.py`, Review |
| 06 | Guardrails and conventions: policy rules, hookify, lint snippets | [06-guardrails-and-conventions](specs/06-guardrails-and-conventions.md) | `/sdlc:hookify`, setup (`sdlc-extras`: `hookify-list`, `-configure`, `-help`) |
| 07 | Three-tier knowledge; Learn on every feature, recurring defects | [07-knowledge](specs/07-knowledge.md) | `/sdlc:revise-claude-md`, `/sdlc:knowledge-audit`, Define (reads), Learn in Ship (writes) |
| 08 | Health check, status, cleanup and context diet | [08-health-and-status](specs/08-health-and-status.md) | `/sdlc:doctor`, `/sdlc:status`, `/sdlc:prune`, `/sdlc:context-diet` |
| 09 | Autonomous loop for one well-specified task | [09-autonomous-loop](specs/09-autonomous-loop.md) | `/sdlc-extras:ralph-loop`, `/sdlc-extras:cancel-ralph` (the optional `sdlc-extras` plugin) |
| 10 | UI follows the project's design system, without AI slop | [10-ui-design-system](specs/10-ui-design-system.md) | setup, the UI review after the build (`ui-reviewer`), `/sdlc:review-pr ui` |
| 11 | Runs in Claude Code, Codex, Cursor and Antigravity; a second agent joins a set-up repo | [11-multi-agent](specs/11-multi-agent.md) | setup (detects the agent), `scripts/scaffold.py host`/`add-host`/`agents`, `scripts/hosts.py`, `hosts/` |
| 12 | State changes in one call; control contract v2 (`state.json` with `phase`, `events.jsonl`) | [12-control-contract](specs/12-control-contract.md) | `scripts/state.py` |

## 6. Key journeys

1. **Adopt in an existing repo:** install → `/sdlc:doctor` → `/sdlc:setup` (commands recorded, baseline, audit approved in batches, PR) → `/sdlc:start` a small fix.
2. **New project:** `/sdlc:setup <what you're building>` → approve the stack → skeleton, commands and CI pass on day one → first feature.
3. **Feature (M):** `/sdlc:start <request>` → questions one at a time, only where what, why or how isn't clear → the change file and the plan, the change file read and approved once → Build, each criterion's test recorded red, `verify.py` at the end → Review: the agent recommends reviews, the user picks, each runs once and high findings are fixed in Build test first → Ship: Learn, commit, push, PR, CI watched (one fix, then ask) → stop at the PR; merge on the user's word.
4. **Fix (S):** the bug proven with a failing test, then its root cause → the change file and the plan in a few lines each, no stop → test-first fix, `verify.py` → the reviews a fixed trigger list names (none by default) run without stopping → Ship: Learn, PR, CI → stop at the PR.
5. **Bigger than one session:** the change file, the plan and `backlog.md` approved once → parts built and committed in turn, each resumable after `/clear` (or under autopilot) → one Review over the whole branch → one Ship, stopping at the PR.
6. **Plugin update:** `/sdlc:status` shows drift → `/sdlc:upgrade --dry-run` → `/sdlc:upgrade` on a branch → PR.
7. **Something feels off:** `/sdlc:doctor` → [runbook](runbook.md) procedure.

## 7. Requirements across capabilities

| ID | Requirement |
|---|---|
| PRD-1 | Everything a core phase needs ships in one plugin under the `sdlc:` namespace. Niche parts (the Ralph loop, hookify's list, configure and help commands, four extra review agents) are in the optional `sdlc-extras` plugin, which no core phase needs. |
| PRD-2 | Hooks and scripts are Python 3.9+ standard library only, and never fail the user's session on their own error. |
| PRD-3 | The plugin never merges, deploys to production, runs migrations or installs tools without the user's explicit go-ahead. It pushes a feature branch and opens a PR only at the end of Ship. |
| PRD-4 | Files the plugin writes into a project are tracked by ownership class; a user's edits are never overwritten without asking. |
| PRD-5 | Vendored material keeps its license and attribution (`NOTICE.md`, `licenses/`). |
| PRD-6 | Always-loaded context stays small: phase text is read only when that phase starts (the orchestrator core is about 1,000 words), each job has one entry point (duplicates are reference files), and `CLAUDE.md` is never written by the plugin. |
| PRD-7 | Works on macOS, Linux and Windows, and in single-package repos and polyglot monorepos. |
| PRD-8 | What the next step needs is on file: after Define, the build works from the change file and the state file's plan sections at every size, so a later session, a reviewer or a teammate needs nothing from the conversation. Each commit names the record's path. |

## 8. Success measures

The plugin collects no metrics. The primary measures come from the eval harness, which runs the same task with the plugin and with plain Claude:

| Measure | Target (plugin vs plain, same task) |
|---|---|
| Agent time, to local green and the PR (waiting on CI not counted) | at most 1.2x on S, 1.5x on M, 2x on L |
| Tokens | the same limits |
| Hidden acceptance and regression tests | held level |
| The user's time reading and approving | not counted |

The 1.x flows matched plain Claude's quality at 10–18x the time and tokens (the heavy flow), or were cheaper but failed a crash-safety hidden test that plain Claude passed (the light flows). 2.0 keeps the record and the guards and drops the extra agents and rounds ([ADR 0020](adr/0020-sdlc-2-slim-process-core.md)). Not yet measured: the eval of 2.0 against plain Claude is a separate step after the release candidate.

For a team rollout, from repo artifacts: reviews chosen and their findings (the change file's `## Review`), deviations per feature, `CLAUDE.md` under 60 lines, a shrinking baseline, and repos on the current scaffold (`/sdlc:status`).

## 9. Constraints and dependencies

- **Runtime:** Claude Code, Codex, Cursor or Antigravity with plugin support; `git`; Python 3.9+; `gh` for PR and code-review commands; Node for the brainstorm companion; Git Bash for Claude Code on Windows.
- **Model calls:** the security reviewer uses the Claude API (API key or Claude Code's OAuth token); without credentials those reviews are skipped.
- **Licensing:** MIT plugin; bundled Superpowers (MIT), GitHub Spec Kit (MIT), Anthropic Claude Code plugins (Apache-2.0).

## 10. Release scope

The [changelog](../CHANGELOG.md) is the per-release record. Releases through 1.8.1 brought setup, upgrade and eject, doctor and status, scope tracing, UI design-system enforcement, the model router, and Codex, Cursor and Antigravity as hosts with hooks and the `sdlc-invariants` CI check. 2.0 is the slim process core ([ADR 0020](adr/0020-sdlc-2-slim-process-core.md)): four phases (Define, Build, Review, Ship), the same record at every size, intent before code, the build like plain Claude with `verify.py`'s red-first evidence, reviews recommended after the build, Learn before the final commit, green locally and on CI, and a stop at the PR. It removes Prove and its rounds, the Lite and full flows, the verifier, ac-checker and code-architect agents, the relay, and the skills only the old flow used. Every typed command keeps its name. A feature started on 1.x is finished on 1.8.1 before the upgrade.

## 11. Known gaps and open questions

Current:

- **2.0 is instructed, not yet evaluated.** Whether it meets the §8 limits is open. Review's per-command cap is enforced (ADR 0012); a probe hidden behind a project command (`npm test; node probe.js`) escapes it. Build's `verify.py` evidence (ADR 0013) is tamper-evident, not tamper-proof ([spec 04](specs/04-verification.md#known-gaps)).
- **Prompt-only guarantees:** apart from the model router, phase and hard-stop rules rest on instructions plus the user's approval. Mechanical are `verify.py`'s red records and drift check, freshness, Review's 120 s command limit, guardrails, the surface check, file ownership, the model router, the role guard's file-tool limits, the commit review gate and the trust anchor (a passing full run of the current code to leave Review, a review's `VERDICT: FAIL` unless waived), which makes a change visible rather than preventing it. The review recommendation, one question at a time, the one CI fix and the stop at the PR are instructions; nothing enforces them. Each spec marks which is which; their Known gaps sections list the rest.
- **Reviewers and the qa-tester keep Bash,** so a shell edit, a reviewer's own script or reading source is only instructed against ([specs 03](specs/03-scope-and-review.md), [04](specs/04-verification.md)).
- **Security-guidance hooks** are vendored and untested here; the review gate's limits live in a repo the agent can write ([spec 05](specs/05-security.md)).
- **Outside Claude Code:** no role guard, model router, security review, `sdlc-extras` (Ralph loop), autopilot or context diet; Codex and Antigravity record `last_result: unknown` ([spec 11](specs/11-multi-agent.md)).
- **Control contract:** a hand edit to `state.md` leaves `state.json` behind; `spend` is always null ([spec 12](specs/12-control-contract.md)).
- **Generated CI** hasn't run on GitHub (YAML and local toolchains only; no `actionlint`), and setup → start → upgrade hasn't run as one continuous project.

History:

- **Live checks after 1.5.0 (2026-10-23, headless on Windows, about $3):** an M feature in the brownfield monorepo through Stage 8 (subagent-driven, red-green with `install`, dispatches logged per stage, simplifier before the opus review, `Verified:` tree checked); then probes of a failing full run (`last_result: fail`), a reviewer Edit denied by the role guard, a Risk change reaching the user, and the model router holding a reviewer to opus on high risk.
- **Release smoke test (1.5.0, 2026-10-23, headless on Windows):** every must item passed again; the S fix ran the simplifier before the reviewer and recorded `Verified:`. Known issues are under 1.5.0 in the changelog.
- **Release smoke test (1.4.0, 2026-10-22, headless sessions on Windows):** install, doctor, greenfield and brownfield setup (including resume after an interrupt), guardrails, an S fix through Verify, upgrade and eject all passed; hook warnings and block reasons reach Claude, and the model router named a tier for every dispatch. It found and fixed CRLF hashing and a freshness filter bug. Known issues are listed under 1.4.0 in the changelog.
- **Multi-agent smoke tests (2026-10-24 and 2026-10-25):** see [spec 11](specs/11-multi-agent.md#known-gaps).
