# PRD: sdlc, a Claude Code plugin for the whole software lifecycle

- **Status:** describes the plugin as it is (the version in `.claude-plugin/plugin.json` plus the "Unreleased" section of the [changelog](../CHANGELOG.md)), last checked 2026-10-27. Not a wish list; gaps are listed as such.
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

1. **One install, whole lifecycle:** four phases (Define, Build, Prove, Ship with Learn) plus on-request `/sdlc:deploy`, with no other plugin needed.
2. **Process sized to the work:** S, M or L, the smallest that fits. Sized by footprint, not risk words: a change confined to 1–2 files is M and one piece, never sliced. Low-risk M runs the Lite flow; work with several distinct parts that won't fit one session runs as a backlog of slices, optionally unattended (autopilot).
3. **Everything on file:** Define writes `intent.md` (why), `spec.md` (what) and `plan.md` (how) on M and L (S: the state file's `Intent:` and `Repro:` lines), so role-based agents can later hand work over through files.
4. **Few human decisions:** one approval in Define (none on S), added scope, the round cap, a requirement that fails in two rounds, merge, production deploy, migrations, anything irreversible. Passing checks and fixable failures don't stop.
5. **Truthful verification:** Build proves each acceptance criterion with `verify.py` (its test recorded failing before its code, passing now), and on M full and L Prove judges that evidence in one round on one commit (M full: one fresh code-reviewer that reads each test against its criterion and reviews with a one-pass brief; L: a separate ac-checker beside a top-tier code review; security only on a security-touched change; QA at a backlog's Feature close), findings fixed back in Build, one re-verification. S and M lite have no Prove: Build's passing `verify.py` goes to Ship, and on M full and L the user may skip Prove at Define's approval; no stale test results, and old failures don't block new work. What can't be proven within budget goes to the user, never counted as passed.
6. **Scope discipline:** every addition traced from request to diff; over-engineering and unrequested behaviour caught while writing and at review.
7. **Learning that sticks and stays small:** Learn on every feature adds fixed defects to `recurring-defects.md`, which Define and every reviewer read; knowledge in three loading tiers.
8. **Process that costs at most about twice the plain run:** at most 2x the time and 2.5x the tokens of plain Claude, with hidden-test results and blind-review defects held level. Checkers get time budgets and a probe cap, the cheap model tier is `sonnet` (never `haiku`), and the advisor is consulted once, before Ship's commit, only on a feature with no Prove (§8).
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
| 02 | Orchestrated lifecycle: tracks, Lite flow, four phases with the three Define files, Build method, hard stops, backlog slices, autopilot, the relay (a thin main session on L, the main session as maker on M, fresh checkers on both), trust anchor, resume, on-request deploy | [02-orchestration](specs/02-orchestration.md) | `/sdlc:start`, `/sdlc:status`, `/sdlc:deploy`, `scripts/backlog.py`, `scripts/autopilot.py`, `hooks/model_router.py`, `hooks/trust_anchor.py` |
| 03 | Scope tracing and review facts | [03-scope-and-review](specs/03-scope-and-review.md) | Define, Prove; `/sdlc:review-pr`, `/sdlc:code-review`, `scripts/diff_stats.py` |
| 04 | Verification: `verify.py` in Build (each criterion's test recorded red, the verify plan, plan drift), reused in Prove and judged by a fresh checker (M: the code-reviewer; L: an ac-checker; old plans: the fresh verifier with red-green), black-box QA tester at Feature close or on request, time and probe budgets (a hook kills commands at 120 s), freshness hook, baseline | [04-verification](specs/04-verification.md) | Prove, `hooks/verify_freshness.py` |
| 05 | Security: always-on guidance, commit review once per review-ready diff and only on a security-touched change, Prove's security checks on a security-touched change | [05-security](specs/05-security.md) | always-on hooks, `hooks/sdlc_review_gate.py`, Prove |
| 06 | Guardrails and conventions: policy rules, hookify, lint snippets | [06-guardrails-and-conventions](specs/06-guardrails-and-conventions.md) | `/sdlc:hookify`, setup (`sdlc-extras`: `hookify-list`, `-configure`, `-help`) |
| 07 | Three-tier knowledge; Learn on every feature, recurring defects | [07-knowledge](specs/07-knowledge.md) | `/sdlc:revise-claude-md`, `/sdlc:knowledge-audit`, Define (reads), Learn in Ship (writes) |
| 08 | Health check, status, cleanup and context diet | [08-health-and-status](specs/08-health-and-status.md) | `/sdlc:doctor`, `/sdlc:status`, `/sdlc:prune`, `/sdlc:context-diet` |
| 09 | Autonomous loop for one well-specified task | [09-autonomous-loop](specs/09-autonomous-loop.md) | `/sdlc-extras:ralph-loop`, `/sdlc-extras:cancel-ralph` (the optional `sdlc-extras` plugin) |
| 10 | UI follows the project's design system, without AI slop | [10-ui-design-system](specs/10-ui-design-system.md) | setup, Prove's `ui-reviewer`, `/sdlc:review-pr ui` |
| 11 | Runs in Claude Code, Codex, Cursor and Antigravity; a second agent joins a set-up repo | [11-multi-agent](specs/11-multi-agent.md) | setup (detects the agent), `scripts/scaffold.py host`/`add-host`/`agents`, `scripts/hosts.py`, `hosts/` |
| 12 | State changes in one call; control contract v2 (`state.json` with `phase`, `events.jsonl`) | [12-control-contract](specs/12-control-contract.md) | `scripts/state.py` |

## 6. Key journeys

1. **Adopt in an existing repo:** install → `/sdlc:doctor` → `/sdlc:setup` (commands recorded, baseline, audit approved in batches, PR) → `/sdlc:start` a small fix.
2. **New project:** `/sdlc:setup <what you're building>` → approve the stack → skeleton, commands and CI pass on day one → first feature.
3. **Feature (M):** `/sdlc:start <request>` → intent, spec (`[inferred]` guesses) and plan, approved once, with its questions and their recommended answers in the same message → Build from `plan.md`, each criterion's test recorded red, `verify.py` at the end → (full only, unless skipped at the approval) Prove: one fresh code review that also checks each AC's test, findings fixed in Build, re-verification → Ship: Learn, commit on a feature branch and report it (every track; merge or PR on the user's word).
4. **Fix (S):** no documents: `Intent:` and `Repro:` lines in the state file, no approval → test-first fix, built and verified in one place, no Prove → Ship: a commit on a feature branch, reported without asking.
5. **Bigger than one session:** spec and `backlog.md` approved once → slices built and committed in turn, no Prove per slice (or under autopilot) → feature close: one Prove round (unless `Prove: skip`) with the ac-checker over every criterion, one top-tier review of the whole branch and the qa-tester; then Ship, which keeps the branch until the user says merge or PR.
6. **Plugin update:** `/sdlc:status` shows drift → `/sdlc:upgrade --dry-run` → `/sdlc:upgrade` on a branch → PR.
7. **Something feels off:** `/sdlc:doctor` → [runbook](runbook.md) procedure.

## 7. Requirements across capabilities

| ID | Requirement |
|---|---|
| PRD-1 | Everything a core phase needs ships in one plugin under the `sdlc:` namespace. Niche parts (the Ralph loop, hookify's list, configure and help commands, four extra review agents) are in the optional `sdlc-extras` plugin, which no core phase needs. |
| PRD-2 | Hooks and scripts are Python 3.9+ standard library only, and never fail the user's session on their own error. |
| PRD-3 | The plugin never merges, deploys to production, runs migrations, pushes or installs tools without the user's explicit go-ahead. |
| PRD-4 | Files the plugin writes into a project are tracked by ownership class; a user's edits are never overwritten without asking. |
| PRD-5 | Vendored material keeps its license and attribution (`NOTICE.md`, `licenses/`). |
| PRD-6 | Always-loaded context stays small: phase text is read only when that phase starts (the orchestrator core is about 1,000 words), each job has one entry point (duplicates are reference files), and `CLAUDE.md` is never written by the plugin. |
| PRD-7 | Works on macOS, Linux and Windows, and in single-package repos and polyglot monorepos. |
| PRD-8 | What the next step needs is on file: after Define, the build works from `intent.md`, `spec.md` and `plan.md` (S: the state file's `Intent:` and `Repro:` lines), not from the conversation. |

## 8. Success measures

The plugin collects no metrics. The primary measures come from the eval harness, which runs the same task with the plugin and with plain Claude:

| Measure | Last result (evals 8–10, planner task: plugin vs plain) | Target |
|---|---|---|
| Agent time | 107–160 min vs 20–26 | at most 2x plain |
| Weighted tokens | 7.7–8.0M vs 1.3M | at most 2.5x plain |
| Human touches | 4–5 vs 1 | down |
| Hidden acceptance and regression tests | 9/9 and 10/10, same as plain | held level |
| Blind-review defects | 0 blocking or major vs 1–2 major for plain | held level or fewer |

On those rounds the plugin took 4–7x the baseline's wall-clock time and about 6x its tokens, mostly from unbounded verifier and QA probing and from repeated fresh-verifier rounds, with no measured quality gain from that work. The four phases ([ADR 0010](adr/0010-four-phases.md)) and the bounded Prove ([ADR 0011](adr/0011-track-cost.md)) (no checkers on S, one verifier on M lite, one code review on M full, 2-minute and 10-minute limits, at most 5 probes, a stop when a requirement fails twice) target the first three rows; Eval rounds 12–13 showed the budget, as instructions only, wasn't followed, and M full's Prove still took 40–50 minutes; [ADR 0012](adr/0012-enforced-prove-budget.md) enforces the command cap with a hook and drops QA and the second verifier from M full, targeting 12–15 minutes. [ADR 0013](adr/0013-build-proves-prove-judges.md) stops Prove re-executing Build: Build records each criterion's test red and runs `verify.py`, and Prove reuses that run and dispatches a small ac-checker in place of the verifier, targeting Prove at 5 minutes or less on M. On the stage-1 S-task eval (3 runs each) quality was equal, but the plugin took 11.7x the tokens, 7.9x the agent time and 2 touches against 1; [ADR 0014](adr/0014-lighter-s-and-a-companion-plugin.md) drops S's documents and Ship's question on S and lite, and moves niche parts out of the always-on listing (4,643 tokens, target under 2,000). [ADR 0015](adr/0015-prove-only-where-it-pays.md) drops Prove on S and M lite, makes it skippable on M full and L, runs one Prove per backlog, and runs security reviews only on security-touched changes. Not yet re-measured.

For a team rollout, from repo artifacts: Prove passing within two rounds (`state.md`), deviations per feature, `CLAUDE.md` under 60 lines, a shrinking baseline, and repos on the current scaffold (`/sdlc:status`).

## 9. Constraints and dependencies

- **Runtime:** Claude Code, Codex, Cursor or Antigravity with plugin support; `git`; Python 3.9+; `gh` for PR and code-review commands; Node for the brainstorm companion; Git Bash for Claude Code on Windows.
- **Model calls:** the security reviewer uses the Claude API (API key or Claude Code's OAuth token); without credentials those reviews are skipped.
- **Licensing:** MIT plugin; bundled Superpowers (MIT), GitHub Spec Kit (MIT), Anthropic Claude Code plugins (Apache-2.0).

## 10. Release scope

The [changelog](../CHANGELOG.md) is the per-release record. As of 1.8.1 plus Unreleased (2026-10-27): releases through 1.8.1 brought setup, upgrade and eject, doctor and status, scope tracing, the baseline-aware verifier, UI design-system enforcement, the model router, and Codex, Cursor and Antigravity as hosts with hooks and the `sdlc-invariants` CI check. Unreleased adds the four phases with the three Define files, Prove's parallel round, `verify.py` and the ac-checker (Build proves, Prove judges), Learn on every feature, `/sdlc:deploy`, the Lite flow, backlog slices and autopilot, `state.py` with control contract v2, `/sdlc:context-diet`, the commit security review once per review-ready diff, an S track with no documents, Ship committing without asking on S and lite, no Prove on S and M lite (skippable on M full and L), one Prove per backlog, no per-task review on L (Prove is the only review), security reviews only on security-touched changes, and the optional `sdlc-extras` companion plugin, with Prove bounded by track, time and probe budgets and the cheap tier moved from `haiku` to `sonnet`.

## 11. Known gaps and open questions

Current:

- **The phase changes are instructed, not yet evaluated; Prove's per-command cap is enforced (ADR 0012), its 10-minute round budget is not.** A probe hidden behind a project command (`npm test; node probe.js`) escapes the cap. Build's `verify.py` evidence (ADR 0013) is tamper-evident, not tamper-proof ([spec 04](specs/04-verification.md#known-gaps)). Evals 8–10 predate them; whether they close the cost gap in §8 is open, and `Build: subagent` against `native` hasn't been compared ([ADR 0009](adr/0009-cheaper-pipeline-and-control-contract.md)).
- **Prompt-only guarantees:** apart from the model router, phase and hard-stop rules rest on instructions plus the user's approval. Mechanical are `verify.py`'s red records and drift check, freshness, Prove's 120 s command limit, guardrails, the surface check, file ownership, the model router, the role guard's file-tool limits, the commit review gate and the trust anchor, which makes a change visible rather than preventing it. Each spec marks which is which; their Known gaps sections list the rest. Prove's 10-minute agent budget, probe cap, round cap and two-round stop are instructions to the agents; nothing enforces them.
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
