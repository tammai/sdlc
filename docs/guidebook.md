# sdlc guidebook

What the plugin is, how it thinks, and where things live. For "what do I do when…", see the [playbook](playbook.md). For "something is broken", see the [runbook](runbook.md).

## The idea

`sdlc` is one Claude Code plugin that takes a piece of work from request to shipped and learned-from. An **orchestrator** skill is the conductor: it sizes the work, runs one stage at a time, calls the bundled skills, subagents and commands for that stage, records progress in `.sdlc/state/<feature>.md`, and stops at **gates**. Nothing outside the plugin is needed for the core stages.

Three ideas carry the design:

1. **Smallest process that fits.** Work is sized S, M or L. The orchestrator picks the smallest track whose signals match and only sizes up for a named signal, because a bigger track brings brainstorming and design, which invite a bigger solution.
2. **Gates, not vibes.** Every stage has an exit criterion. A failed gate means stay in the stage or step back one. Some gates are checked by the orchestrator; others are **hard stops** where you decide.
3. **Independent checking.** The context that wrote the code never verifies or reviews it. Verification uses a fresh `verifier` subagent each round; review uses separate reviewer agents.

## Project setup

Before the first feature, `/sdlc:setup` prepares the repo once. `/sdlc:start` offers it when a repo isn't set up. See [sdlc_setup_phase.svg](diagrams/sdlc_setup_phase.svg).

- **Greenfield** (no source yet): a short stack interview; you approve; the ecosystem's own generators build the skeleton; the project's commands and CI pass on day one.
- **Brownfield** (existing code): the commands you already have, recorded as they are; a **baseline** of what already fails; a deep audit (conventions, git-history gotchas, decisions, area rules) drafted by explorer agents and written only as you approve each batch; existing AI configs (long CLAUDE.md, AGENTS.md, Cursor rules, ADRs) migrated into the three knowledge tiers, one diff per source.
- **Both:** policy rules, hookify guardrails, lint snippets, a permission allowlist for the project's commands, the sdlc marketplace and `enabledPlugins` in `.claude/settings.json` (only if you approve, so teammates are offered the plugin), `.gitignore` entries, an sdlc block in `AGENTS.md` once a second agent (Codex, Cursor, Antigravity) has set up the repo, a constitution (with the default Simplicity principle), the design system (projects with UI) and the knowledge folder.

Setup runs on a `sdlc/setup` branch with one commit per step, resumes where it stopped, and ends by asking whether to open a PR or merge locally.

**The project's commands.** Every set-up repo records its own `install`, `test`, `lint`, `typecheck` and `build` commands in `.sdlc/config.json`, exactly as the team already runs them (`pnpm test`, `go test ./...`, `make lint`, …); a step that doesn't apply is `null`. Stages, the verifier, CI, the allowlist and the freshness hook all read them from there, so nothing in the plugin is stack-specific and there's nothing extra to install. A monorepo lists `packages`, each with a path, a stack and its own commands, run from its directory; a polyglot repo (TS, Go, Rust, Dart, shell, …) is just several packages with different stacks.

**Who owns which file.** Everything the plugin puts in a repo is tracked in `.sdlc/scaffold.lock.json` with one of these classes, which decides what an upgrade may do:

| Class | Examples | On upgrade |
|---|---|---|
| Generated | `.claude/rules/sdlc*.md` | regenerated |
| Seeded | `.claude/hookify/sdlc-*.md`, `.github/workflows/sdlc-verify.yml`, `sdlc-invariants.yml`, `.sdlc/ci/invariants.py`, `.sdlc/lint/*` | replaced only if you haven't edited it; otherwise you choose: merge, skip, or keep yours for good |
| Keyed merge | allowlist and plugin-enablement keys in `.claude/settings.json`, `.gitignore` lines, the `<!-- sdlc:begin -->` block in `AGENTS.md` | only the entries the plugin added; the block is rebuilt, your text around it is never touched |
| Yours | the commands in `.sdlc/config.json`, `CLAUDE.md`, constitution, design system, `knowledge/`, baseline, your own rules | changed only by migrations you approve |

Files named `sdlc-*` belong to the plugin; everything else is yours.

**Upgrades.** When the plugin is newer than the repo's scaffold, `/sdlc:start` and `/sdlc:status` say so and suggest `/sdlc:upgrade`, which never blocks your work. The upgrade runs on its own branch: regenerate, replace untouched files, walk you through edited ones, then apply versioned migrations one diff at a time (declined ones are recorded and not asked again unless you use `--revisit`). The repo pins a minimum plugin version so teammates on an older plugin get a warning. `/sdlc:eject` removes what the plugin owns and keeps your work.

## Tracks

| Track | Use when | Stages |
|---|---|---|
| **S · fix** | bug or tweak, 1–3 files, clear expected behavior | 4 → 5 → 6 (light) → 8 |
| **M · feature** | a few files to a few days, approach mostly obvious | risk low: the Lite flow (below); risk high or on request: 1 → 3 → 4 → 5 → 6 → 7 (light) → 8, plus 2 if the approach is unclear |
| **L · project** | new service or module, unclear approach, or touches auth, payments, data migration, public API | 1–8 → 11 (9 on request) |

Anything touching auth, payments, secrets, PII or schema migrations is at least M and always gets the full Stage 7. You can override the size at any time.

**The Lite flow** (`Flow: lite`) is the default for M with `Risk: low`, because evals showed the full M flow costing several times the tokens and more approvals for the same hidden-test results ([ADR 0008](adr/0008-lite-flow-for-low-risk-m.md)). One `spec.md` holds the requirements, an `Inferred` list, the acceptance criteria and 3–6 tasks, and you approve it once. The session builds natively, test first. One fresh standard-tier verifier runs; one standard-tier reviewer checks the diff with durable writes, error paths and loaded data named in its brief. Review fixes are re-verified with an in-session full run (the freshness hook keeps tracking through Stage 6 for this). Then light security and one commit. It sizes up to the full M flow when a design decision comes up that the request doesn't settle, or when risk turns out high.

**Backlog slices.** Work bigger than one session (about 8–10 tasks, or several distinct parts) gets a `backlog.md` of vertical slices instead of one plan, approved once with the spec on M, or at the Stage 3 gate on L. Each slice runs the Lite inner loop: a short `plan-B<n>.md`, a native build, one fresh verifier, one review of that slice's diff, one commit. Slices run back to back without asking; they stop on a failed gate, a backlog change that adds scope, or a hard stop. Per-slice stops are opt-in (`Slice gates: plan, review, commit`). When the session's context runs low, it stops at a slice boundary and names the next slice; `/clear` then `/sdlc:start` picks it up, and `/sdlc:start B<n>` runs a named one once its dependencies are done.

**Risk and models.** Risk is recorded apart from size: `Risk: high` for auth, payments, secrets, PII, schema migrations or a public API. Track and risk pick each subagent's model tier: cheap `haiku`, standard `sonnet`, top `opus`. A high-risk change gets `opus` reviewers even on the S track. The S fix itself goes to one implementer subagent on that tier, not the session. The session's own model is yours: the start announcement suggests `/model opus` for L or high-risk work on a smaller model, and `/model sonnet` for S or low-risk M work on Opus or above. It says so once and never blocks. Fable is used only if you ask for it ("use fable"), which sets `Top model: fable` in `state.md`. See [sdlc_tracks_full_stage_tree.svg](diagrams/sdlc_tracks_full_stage_tree.svg).

## The 11 stages

| # | Stage | Produces | Gate |
|---|---|---|---|
| 1 | Discover & specify | `spec.md`, `checklists/requirements.md` (L: `brainstorm.md`) | **You approve.** Checklist passes, no `[inferred]` items left, Non-Goals filled, acceptance criteria testable |
| 2 | Design | `design.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` | **You approve.** Every requirement maps to the design, every added module or dependency cites a requirement, constitution check passes |
| 3 | Plan | `plan.md` | No CRITICAL or HIGH scope findings, every task cites a requirement, Public Surface declared. **You pick the execution method** |
| 4 | Implement | code, tests | Every plan task checked, build and full test suite pass, no TODO without a ticket |
| 5 | Verify (max 3 rounds) | `test-report.md` | Fresh verifier PASS on the current commit, no test gap rated 8+, no high-severity silent failure |
| 6 | Review | `review.md` | No unresolved high-severity finding; the rest fixed or ticketed |
| 7 | Security | `security.md` | No critical or high finding open, no secrets in the diff |
| 8 | Commit, PR, CI | PR | CI green. **Never merged without you saying so** |
| 9 | Deploy (on request) | `release.md` | **Your go-ahead** before any production deploy or DB migration; smoke test passes |
| 10 | Operate (parked: no track runs it) | | Agreed signals stay within threshold for the watch window, or a rollback/fix ticket exists |
| 11 | Learn | `retro.md`, knowledge updates | Lessons promoted and linked, CLAUDE.md ≤ 60 lines, `state.md` marked `Status: done` |

Each stage starts with a header so you always know where you are:

```
▶ Stage N – <name>   (track M)
  Using: <skills/agents/commands>
  Gate:  <exit criterion>
```

The whole loop, with hard stops, is in [sdlc_orchestrator_decision_tree.svg](diagrams/sdlc_orchestrator_decision_tree.svg). Per-stage skills, subagents, hooks and gates are in [sdlc_full_flow.svg](diagrams/sdlc_full_flow.svg).

### Hard stops

The orchestrator always asks you before: end of Stage 1, end of Stage 2, choosing the execution method, any merge, production deploys, DB migrations, and anything irreversible. If you say "skip" or "just ship it", it names the gates being skipped, records them under Deviations in `state.md`, then complies.

## Scope tracing

Over-engineering usually starts before any code exists, so every stage ties additions back to a request:

- **Questions come once.** Before the spec (L: before brainstorming; S: before the brief), the orchestrator asks only what would change what gets built, in one message, or nothing. Everything else is a guess the spec lists as `[inferred]`, so you confirm or veto the guesses together with the spec instead of answering one question per turn. `clarifying-specs` runs only when you ask.
- **Specs** tag each requirement `[user]`, `[clarified]` or `[inferred]`, and have a required Non-Goals section. At the Stage 1 gate, `[inferred]` items are listed on their own and **dropped unless you keep them**; dropped ones move to Non-Goals.
- **Designs** keep a Complexity Tracking table: every new module, layer, abstraction, dependency, service, config key or store cites a requirement or comes out.
- **Plans** give each task a `Requirements:` line and declare a **Public Surface** (every new export, endpoint, command, config key, env var, dependency).
- **Review** runs `scripts/diff_stats.py --plan` to flag exports and dependencies missing from the Public Surface. Unrequested public surface is high severity. It's the feature's only whole-branch review: the execution skills skip their own final review under the orchestrator, and per-task reviews still run in Stage 4. On M and L it runs on the top tier (the Lite flow keeps the standard tier). The simplifier runs before the reviewers, and any code change in Stage 6 or 7 goes back to Stage 5 for another round (the Lite flow re-verifies in the session instead); Stage 8 checks the code still matches the `Verified:` commit before committing.

## Verification

Stage 5 is the only stage with a hook that blocks you. While `state.md` says `Current: Stage 5 – Verify`:

- any code change (by any tool, in a git repo) marks test results **stale**;
- a **full** test run marks them **fresh**. A run that names a test file, a pytest node id, a single Go package, or a name filter does not count;
- finishing a turn while stale is blocked with "re-run tests".

In a set-up repo the full run is the `test` command from `.sdlc/config.json`, with no file, name or package arguments. In a monorepo, freshness is per package: an edit under `services/api/` makes only `api` stale, and `cd services/api && <api's test command>` makes it fresh again; a file outside every package makes all of them stale. A root-level test command in config (e.g. `turbo run test`) counts for every package.

Failures listed in `.sdlc/baseline.md` (recorded at brownfield setup) don't fail a round: the verifier fails only on **new** failures, removes baseline items that now pass, and never adds any. Accepting a new failure into the baseline is your decision, recorded as a Deviation.

Each round spawns a new `verifier`, which runs build, lint, typecheck and tests fresh, proves each acceptance criterion, and appends a section to `test-report.md`. It also checks red-green: in a throwaway worktree with the feature's code put back to `Base:`, the feature's tests must fail; a test that still passes doesn't count as evidence. In M and L, `pr-test-analyzer` and `silent-failure-hunter` run alongside, except on the Lite flow. When you ask for a QA round, a new `qa-tester` runs the feature against the spec's scenarios and edge cases the way a user would (CLI, HTTP, browser or a script), without being told about the code, and writes `qa-report.md`; you decide what its failures mean, and it isn't part of the gate. If a round fails, the work goes back to Stage 4 for the listed failures only. After round 3 fails, the orchestrator stops and brings you what still fails, what each round changed, and a root-cause hypothesis.

## Building blocks

### Skills (`sdlc:` namespace)

| Group | Skills |
|---|---|
| Conductor | `orchestrator` |
| Set up | `setting-up-projects` (setup, upgrade, eject) |
| Specify and design | `brainstorming`, `writing-specs`, `clarifying-specs`, `designing-solutions`, `project-constitution` |
| Plan and build | `writing-plans`, `analyzing-consistency`, `using-git-worktrees`, `subagent-driven-development`, `executing-plans`, `dispatching-parallel-agents`, `test-driven-development`, `systematic-debugging` |
| Check | `verification-before-completion`, `requesting-code-review`, `receiving-code-review` |
| Ship and learn | `finishing-a-development-branch`, `managing-knowledge`, `claude-md-improver`, `writing-hook-rules`, `todo` |

### Subagents

| Agent | Used for |
|---|---|
| `code-explorer`, `code-architect` | Stage 2: trace existing code, propose architectures |
| `verifier` | Stage 5: fresh, independent verification each round, including red-green |
| `qa-tester` | On request: runs the feature against the spec as a user would, without reading the code (not part of any gate) |
| `pr-test-analyzer`, `silent-failure-hunter` | Stage 5 and 6: test gaps (rated 1–10), swallowed errors |
| `code-reviewer`, `comment-analyzer`, `type-design-analyzer`, `code-simplifier` | Stage 6, chosen by `/sdlc:review-pr` based on the diff |
| `ui-reviewer` | Stage 6 when UI files change: design-system conformance, AI-slop styling, states, accessibility; screenshots on request |
| `feature-reviewer`, `code-reviewer` | Stage 7: security-only review brief |
| `conversation-analyzer` | Stage 11: find behaviors worth preventing with hooks |

### Commands

| Command | Does |
|---|---|
| `/sdlc:start [request]` | Start a feature, or resume the active one if the request is empty |
| `/sdlc:setup [what you're building]` | Set the repo up once (greenfield or brownfield); resumes if interrupted |
| `/sdlc:upgrade [--dry-run] [--revisit]` | Bring the repo's scaffold up to the installed plugin version |
| `/sdlc:eject` | Remove the plugin's files from the repo, keeping your work |
| `/sdlc:doctor` | Health check of the machine, the plugin and the repo, with a fix for each problem. Changes nothing |
| `/sdlc:status` | Setup state and version drift, then one line per feature in `.sdlc/`: track, stage, last gate; open questions. Changes nothing |
| `/sdlc:prune [--older-than 45d]` | Delete the plan, reports, review and checklists of merged features marked done; keeps spec, design, retro and state. Asks first, one commit |
| `/sdlc:review-pr` | Local pre-PR review with the right agents for the diff |
| `/sdlc:code-review` | Review a GitHub PR (needs `gh`) |
| `/sdlc:commit`, `/sdlc:commit-push-pr`, `/sdlc:clean_gone` | Git helpers |
| `/sdlc:ralph-loop`, `/sdlc:cancel-ralph`, `/sdlc:ralph-help` | Optional self-iterating loop for one well-specified task |
| `/sdlc:revise-claude-md`, `/sdlc:knowledge-audit` | Promote lessons; keep always-loaded context small |
| `/sdlc:hookify`, `/sdlc:hookify-list`, `/sdlc:hookify-configure`, `/sdlc:hookify-help` | Turn repeated corrections into rules |

### Hooks

| Hook | Events | Does |
|---|---|---|
| hookify | PreToolUse, UserPromptSubmit, Stop | Evaluates rules from `.claude/hookify.*.local.md` (personal, git-ignored) and committed `.claude/hookify/*.md` (team). Rules warn or block |
| security-guidance | UserPromptSubmit, PostToolUse, Stop | Pattern warnings on edits, diff review at turn end, agentic review after `git commit` and `git push` |
| verify-freshness | PostToolUse, PostToolUseFailure, Stop | Stage 5 only (Stages 5–6 on the Lite flow): stale/fresh test tracking (above) |
| model-router | PreToolUse (Agent) | While a feature is active: denies a subagent dispatch that names no model, asks for Fable without `Top model: fable`, or runs a reviewer below Opus on `Risk: high`; logs every dispatch with the stage to `.sdlc/.work/dispatches.jsonl` |
| trust-anchor | Stop, UserPromptSubmit | Tells you when what verification trusts changes: Track, Risk or Top model; new baseline failures; changed commands; the spec after Stage 5 began; leaving Stage 5 (Lite: or 6) with untested code. Your next message accepts it |
| role-guard | PreToolUse (file tools) | Holds the plugin's own agents to their role: reviewers can't edit files, the verifier writes only its report, the baseline and its red-green worktree, the qa-tester can't read or search code. Bash stays open to them |
| ralph-loop | Stop | Only while a `/sdlc:ralph-loop` is running |
| SessionStart | SessionStart | Creates a Python environment for the security reviewer on first run |

In Codex, Cursor and the Antigravity CLI, `hosts/hook.py` runs hookify, verify-freshness and trust-anchor on the agent's own hook events (in Codex, once you trust them in `/hooks`; see [spec 11](specs/11-multi-agent.md)).

## Where things live

```
.sdlc/
  config.json              the project's commands (per package in a monorepo) and overrides on the plugin's defaults (yours)
  scaffold.lock.json       what the plugin placed, versions, migrations (machine-only)
  baseline.md              known failures from before setup (yours)
  state/<feature>.md       track, stage, gate log, deviations, open questions, and the feature's Docs: folder
  lint/                    sdlc lint snippets your ESLint/Ruff config imports (seeded)
  ci/invariants.py         checks test reports, the baseline and specs of active features in CI (seeded)
  ci/contract-check.sh     the API contract check CI runs (multi-app repos that chose it; seeded)
  .work/                   scratch, git-ignored (also verify-freshness.json)
docs/sdlc/                 docs_dir: the documents people read (default; setup asks when the repo publishes docs/)
  constitution.md          project principles (yours)
  design-system.md         the design system UI work follows (UI projects; yours)
  intents/<feature>/
    brainstorm.md  spec.md  design.md  plan.md  test-report.md  qa-report.md  review.md  security.md  release.md  retro.md
knowledge/                 tier 3, on-demand docs (index.md links everything)
.claude/rules/<area>.md    tier 2, loads when matching paths are touched (yours)
.claude/rules/sdlc*.md     plugin policy rules: workflow, code style, tests, migrations, sensitive areas, CI (generated)
.claude/hookify/*.md       team hookify rules; sdlc-*.md are the plugin's guardrails (seeded)
.github/workflows/sdlc-verify.yml   CI generated from the commands in config (seeded)
.github/workflows/sdlc-invariants.yml   runs .sdlc/ci/invariants.py on pull requests and pushes (seeded)
CLAUDE.md                  tier 1, at most 60 lines (never touched by the plugin)
```

Each feature (its state file and its documents folder) is named `<yyyy-mm-dd>-<slug>` (with a ticket key after the date when there is one, e.g. `2026-10-22-PROJ-123-month-filter`), so folders sort by start date and a new feature never reuses an old one's folder; the branch uses the same name. Commit its state and everything under `docs/sdlc/intents/<feature>/`. Only `.sdlc/.work/` is ignored. A repo set up before 1.7.0 keeps everything in `.sdlc/<feature>/` until `/sdlc:upgrade` moves it; the hooks read both layouts meanwhile ([ADR 0006](adr/0006-split-sdlc-docs-from-machinery.md)).

### `state.md`

Resume depends on this file. The orchestrator looks for `.sdlc/state/*.md` with `Status: active`; one match resumes, several asks which, none starts a new feature.

```markdown
# <feature>
Status: active
Track: S | M | L   (sized up because: <named signal, or "—">)
Risk: low | high   (<signal>)
Flow: lite | full   (lite: M with risk low, unless you asked for full)
Top model: opus   (fable only if the user chose it)
Base: <commit the feature started from>
Owner: <git email of whoever advances it>   Tool: <claude-code | codex | cursor | antigravity>
Verified: <commit the Stage 5 gate passed on> tree <worktree tree at that gate>
Slice: B<n>   Slice base: <commit>   Slice gates: none   (backlog features only)
Commands: test: `<test command>`   (monorepo: one per package; no setup: the detected command)
Current: Stage <n> – <name>
## Stages / ## Verify rounds / ## Gate log / ## Deviations / ## Open questions
```

### Three-tier knowledge

| Tier | Where | Loads |
|---|---|---|
| 1 | `CLAUDE.md` (≤ 60 lines) | every session |
| 2 | `.claude/rules/<area>.md` with `paths:` | automatically, when matching files are touched |
| 3 | `knowledge/**.md` | on demand, via `knowledge/index.md` and links from tier 2 |

`retro.md` is history and is not loaded by later sessions. Durable lessons are promoted in Stage 11. Something corrected twice and checkable by machine becomes a hookify rule instead of more text.

### Configuration

Setup writes `.sdlc/config.json`; it's yours to edit and holds only what differs from the plugin's defaults (`templates/project/config.defaults.json`). Most teams only touch it to change a command.

| Key | Meaning |
|---|---|
| `commands` | `install`, `test`, `lint`, `typecheck`, `build` as the team runs them. `null` means the step doesn't apply to this stack |
| `packages` | Monorepo instead of `commands`: `[{"name", "path", "stack", "commands"}]`, each run from its path. A root `commands.test` (e.g. `turbo run test`) counts for every package |
| `project.profile`, `project.owners` | Multi-app repos: `lean` or `large` (the answer to "who works here"), and for `large` the CODEOWNERS entries (`{pattern: [handles]}`, in order) |
| `api_contract` | Multi-app repos with the contract check: `{"path", "spec"}` of the versioned API contract |
| `docs_dir` | Where the sdlc documents live (default `docs/sdlc`; `.sdlc` or another in-repo folder if `docs/` is published as a site). Set by setup or the 1.7.0 upgrade; without it a repo is on the old all-in-`.sdlc/` layout |
| `verify.order` | Order of the verify steps (default lint, typecheck, build, test) |
| `areas.*` | Path patterns for the policy rules: `source`, `tests`, `migrations`, `sensitive`, `ci` |
| `ci` | `os` matrix (default `["ubuntu-latest"]`; add `"windows-latest"` if teammates develop on Windows) and toolchain versions for the generated workflow |
| `baseline` | Where the known-failures baseline lives (default `.sdlc/baseline.md`) |
| `min_plugin_version` | Teammates on an older plugin get a warning to update |

After changing commands or `ci`, run `/sdlc:upgrade` so the generated CI workflow follows. Don't edit `.sdlc/scaffold.lock.json` by hand. Why it's designed this way: [ADR 0001](adr/0001-project-setup-upgrade-eject.md), [ADR 0002](adr/0002-record-the-repos-own-commands.md), [ADR 0005](adr/0005-greenfield-monorepo-layout.md), [ADR 0006](adr/0006-split-sdlc-docs-from-machinery.md), [ADR 0007](adr/0007-multi-tool-adapters.md); the `scaffold.py` reference is in the [runbook](runbook.md#setup-upgrade-eject-internals).

## Glossary

| Term | Meaning |
|---|---|
| Gate | Exit criterion for a stage |
| Hard stop | A gate where the orchestrator always asks you |
| Round | One pass of Stage 5; a new verifier each time, at most 3 |
| Stale / fresh | Whether test results predate the latest code change |
| Public Surface | Declared list of everything new that callers or users can see |
| Complexity Tracking | Design table that ties every addition to a requirement |
| Deviation | A gate you chose to skip, recorded in `state.md` |
| Constitution | Project principles in `docs/sdlc/constitution.md`, checked in Stage 2 |
| Design system | `docs/sdlc/design-system.md`: the library, tokens, components and patterns UI work must use; checked by `ui-reviewer` in Stage 6 |
| Project commands | `install`, `test`, `lint`, `typecheck`, `build` in `.sdlc/config.json`, per package in a monorepo |
| Baseline | Failures that existed before setup; Stage 5 only fails on new ones |
| Scaffold version / drift | The plugin version a repo was set up or upgraded with; "behind" means `/sdlc:upgrade` has work to do |
| Generated / seeded | Plugin files that upgrades regenerate / replace only while you haven't edited them |
| Migration | A versioned change to files you own, applied only with your approval |
