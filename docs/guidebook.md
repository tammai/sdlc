# sdlc guidebook

What the plugin is, how it thinks, and where things live. For "what do I do when…", see the [playbook](playbook.md). For "something is broken", see the [runbook](runbook.md).

## The idea

`sdlc` is one Claude Code plugin that takes a piece of work from request to shipped and learned-from. An **orchestrator** skill is the conductor: it sizes the work, runs one phase at a time (Define, Build, Prove, Ship), calls the bundled skills, subagents and commands for that phase, records progress in `.sdlc/state/<feature>.md`, and stops at **gates**. Nothing outside the plugin is needed for the core phases.

Three ideas carry the design:

1. **Smallest process that fits.** Work is sized S, M or L. The orchestrator picks the smallest track whose signals match and only sizes up for a named signal, because a bigger track brings brainstorming and design, which invite a bigger solution.
2. **Gates, not vibes.** Every phase has an exit criterion. A failed gate means stay in the phase or step back one. Some gates are checked by the orchestrator; others are **hard stops** where you decide.
3. **Independent checking.** The context that wrote the code never verifies or reviews it. Verification uses a fresh `verifier` subagent each round; review uses separate reviewer agents.

## Project setup

Before the first feature, `/sdlc:setup` prepares the repo once. `/sdlc:start` offers it when a repo isn't set up. See [sdlc_setup_phase.svg](diagrams/sdlc_setup_phase.svg).

- **Greenfield** (no source yet): a short stack interview; you approve; the ecosystem's own generators build the skeleton; the project's commands and CI pass on day one.
- **Brownfield** (existing code): the commands you already have, recorded as they are; a **baseline** of what already fails; a deep audit (conventions, git-history gotchas, decisions, area rules) drafted by explorer agents and written only as you approve each batch; existing AI configs (long CLAUDE.md, AGENTS.md, Cursor rules, ADRs) migrated into the three knowledge tiers, one diff per source.
- **Both:** policy rules, hookify guardrails, lint snippets, a permission allowlist for the project's commands, the sdlc marketplace and `enabledPlugins` in `.claude/settings.json` (only if you approve, so teammates are offered the plugin), `.gitignore` entries, an sdlc block in `AGENTS.md` once a second agent (Codex, Cursor, Antigravity) has set up the repo, a constitution (with the default Simplicity principle), the design system (projects with UI) and the knowledge folder.

Setup runs on a `sdlc/setup` branch with one commit per step, resumes where it stopped, and ends by asking whether to open a PR or merge locally.

**The project's commands.** Every set-up repo records its own `install`, `test`, `lint`, `typecheck` and `build` commands in `.sdlc/config.json`, exactly as the team already runs them (`pnpm test`, `go test ./...`, `make lint`, …); a step that doesn't apply is `null`. Phases, the verifier, CI, the allowlist and the freshness hook all read them from there, so nothing in the plugin is stack-specific and there's nothing extra to install. A monorepo lists `packages`, each with a path, a stack and its own commands, run from its directory; a polyglot repo (TS, Go, Rust, Dart, shell, …) is just several packages with different stacks.

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

| Track | Use when | Phases |
|---|---|---|
| **S · fix** | bug or tweak, 1–3 files, clear expected behavior | Define is a short `brief.md` with no approval; then Build, Prove, Ship |
| **M · feature** | a few files to a few days, approach mostly obvious | all four; risk low: `Flow: lite` (default); risk high or on request: `Flow: full` |
| **L · project** | new service or module, unclear approach, or touches auth, payments, data migration, public API | all four, with brainstorming and design in Define; `Flow: full` |

Anything touching auth, payments, secrets, PII or schema migrations is at least M and always gets full security in Prove. You can override the size at any time.

**Lite and full.** Every track has the same shape: one approval (none on S), one build, one parallel Prove round, one commit. `Flow: lite` is the default for M with `Risk: low` and for any backlog feature, because evals showed the old full M flow costing several times the tokens and more approvals for the same hidden-test results ([ADR 0008](adr/0008-lite-flow-for-low-risk-m.md)). `Flow:` picks how Prove re-verifies its fixes (lite: the full suite in this session; full: a fresh verifier) and the code-reviewer's tier (full: top); the full flow also writes the spec with `writing-specs` and its checklist, and on M adds the silent-failure-hunter. A Lite spec is short: a two-line Intent, requirements with an `Inferred` list, about 10 acceptance criteria, failure modes, 3–6 tasks and a Public Surface. It sizes up to full when a design decision comes up that the request doesn't settle, or when risk turns out high.

**Backlog slices.** Work bigger than one session (about 8–10 tasks, or several distinct parts) gets a `backlog.md` of vertical slices instead of one task list, approved with the spec in Define's one approval, on any track. Each slice runs Build → Prove → commit: a short `plan-B<n>.md`, a native build, one fresh verifier and one review of that slice's diff, one commit. Slices run back to back without asking; they stop at the round cap, a backlog change that adds scope, or a hard stop. Per-slice stops are opt-in (`Slice gates: plan, review, commit`). After the last slice, feature close runs once: a Prove round (a verifier over every acceptance criterion on the whole branch, the feature's one top-tier review checked against every slice plan's Public Surface, the qa-tester, security), then Ship with Learn and your merge, PR or keep. When the session's context runs low, it stops at a slice boundary and names the next slice; `/clear` then `/sdlc:start` picks it up, and `/sdlc:start B<n>` runs a named one once its dependencies are done. For a backlog too long for one session, **autopilot** (`python3 <plugin>/scripts/autopilot.py <feature>` in a terminal, only when you ask for it) runs each slice in a fresh headless Claude Code session, then feature close up to your merge decision. It stops on a blocked slice, a run that changed nothing, or a trust-anchor notice you haven't seen.

**Risk and models.** Risk is recorded apart from size: `Risk: high` for auth, payments, secrets, PII, schema migrations or a public API. Track and risk pick each subagent's model tier: cheap `haiku`, standard `sonnet`, top `opus`. A high-risk change gets `opus` reviewers even on the S track. The S fix itself goes to one implementer subagent on that tier, not the session. The session's own model is yours: the start announcement suggests `/model opus` for L or high-risk work on a smaller model, and `/model sonnet` for S or low-risk M work on Opus or above. It says so once and never blocks. Fable is used only if you ask for it ("use fable"), which sets `Top model: fable` in `state.md`. See [sdlc_tracks_full_stage_tree.svg](diagrams/sdlc_tracks_full_stage_tree.svg).

## The four phases

| Phase | Produces | Gate |
|---|---|---|
| Define | `spec.md` with `## Intent`, tasks and `## Public Surface`, or a `backlog.md` (full flow: `checklists/requirements.md`; L: `brainstorm.md`; a design when the approach isn't obvious; S: only `brief.md`) | **You approve once** (not on S): spec, tasks or backlog, design and `Build:`. No `[inferred]` items left, Non-Goals filled, acceptance criteria testable, every requirement has a task, Public Surface declared, design criteria hold |
| Build | code, tests | Every task done, build and full test suite pass, no TODO without a ticket |
| Prove (max 3 failed rounds) | `test-report.md`, `review.md`, `security.md` (full security) | Fresh verifier PASS on the current commit, every acceptance criterion has evidence, no unresolved high finding, no test gap rated 8+ (L), no critical or high security finding, no secrets in the diff |
| Ship, with Learn | `recurring-defects.md` lines (L: `retro.md`, a knowledge page), one commit, PR | Verified-tree check clean, Learn done, CI green. **Never merged without you saying so** |

`Build:` is `native`, `subagent` or `tasks` (subagent-driven development with a review per task), taken from the track (S `subagent`, M `native`, L `tasks`) and shown in Define's approval; change it in your reply. Prove runs verification, review and security in one parallel round on one commit. **Learn** runs on every feature, small: the defects Prove fixed go to `recurring-defects.md`, and a durable lesson is filed only when there is one.

Internally each phase keeps a stage number, because the hooks read it: `Current: Stage 1 – Define`, `Stage 4 – Build`, `Stage 5 – Prove`, `Stage 8 – Ship`. A feature started under the old 11 stages resumes in the phase its number maps to. **Deploy** is not a phase: `/sdlc:deploy`, on request, uses the existing deploy path, writes `release.md`, asks your go-ahead before a production deploy or DB migration, and runs a smoke test. Operate is gone.

Each phase starts with a header so you always know where you are:

```
▶ <Phase>   (track M, flow lite)
  Using: <skills/agents/commands>
  Gate:  <exit criterion>
```

The whole loop, with hard stops, is in [sdlc_orchestrator_decision_tree.svg](diagrams/sdlc_orchestrator_decision_tree.svg). Per-phase skills, subagents, hooks and gates are in [sdlc_full_flow.svg](diagrams/sdlc_full_flow.svg).

### Hard stops

The orchestrator always asks you before: Define's approval (not on S), anything that adds scope, any merge, production deploys, DB migrations, and anything irreversible. Everything else runs without asking, including failed verify rounds below the cap. If you say "skip" or "just ship it", it names the gates being skipped, records them under Deviations in `state.md`, then complies.

## Scope tracing

Over-engineering usually starts before any code exists, so every phase ties additions back to a request:

- **Questions come once.** Before the spec (L: before brainstorming; S: before the brief), the orchestrator asks only what would change what gets built, in one message, or nothing. Everything else is a guess the spec lists as `[inferred]`, so you confirm or veto the guesses together with the spec instead of answering one question per turn. `clarifying-specs` runs only when you ask.
- **Specs** tag each requirement `[user]`, `[clarified]` or `[inferred]`, and have a required Non-Goals section. At Define's approval, `[inferred]` items are listed on their own and **dropped unless you keep them**; dropped ones move to Non-Goals.
- **Designs** keep a Complexity Tracking table: every new module, layer, abstraction, dependency, service, config key or store cites a requirement or comes out.
- **Tasks** in the spec each name their requirement, and the spec declares a **Public Surface** (every new export, endpoint, command, config key, env var, dependency).
- **Review** runs `scripts/diff_stats.py --plan` to flag exports and dependencies missing from the Public Surface. Unrequested public surface is high severity. It's the feature's only whole-branch review: the execution skills skip their own final review under the orchestrator, and per-task reviews still run in Build (`Build: tasks`). On `Flow: full` and L it runs on the top tier (`Flow: lite` keeps the standard tier, except a backlog feature's close). The reviewer runs in parallel with the verifier on the same commit (with the qa-tester on M and the silent-failure-hunter on the full flow); all findings, simplifications included, are fixed together and re-verified once (`Flow: lite` re-verifies in the session). There is no separate simplifier pass. Every reviewer checks the spec's Failure modes and a recurring-defects list (the plugin's seed plus the project's own, which Learn extends); Ship checks the code still matches the `Verified:` commit before committing.

## Verification

Prove is the only phase with a hook that blocks you. While `state.md` says `Current: Stage 5 – Prove`, which covers review and security fixes too:

- any code change (by any tool, in a git repo) marks test results **stale**;
- a **full** test run marks them **fresh**. A run that names a test file, a pytest node id, a single Go package, or a name filter does not count;
- finishing a turn while stale is blocked with "re-run tests".

In a set-up repo the full run is the `test` command from `.sdlc/config.json`, with no file, name or package arguments. In a monorepo, freshness is per package: an edit under `services/api/` makes only `api` stale, and `cd services/api && <api's test command>` makes it fresh again; a file outside every package makes all of them stale. A root-level test command in config (e.g. `turbo run test`) counts for every package.

Failures listed in `.sdlc/baseline.md` (recorded at brownfield setup) don't fail a round: the verifier fails only on **new** failures, removes baseline items that now pass, and never adds any. Accepting a new failure into the baseline is your decision, recorded as a Deviation.

Each round spawns a new `verifier`, which runs build, lint, typecheck and tests fresh, proves each acceptance criterion, and appends a section to `test-report.md`. It also checks red-green: in a throwaway worktree with the feature's code put back to `Base:`, the feature's tests must fail; a test that still passes doesn't count as evidence. The code reviewer runs in the same parallel round. On the full flow the `silent-failure-hunter` joins it (M and L), the `pr-test-analyzer` on L, and on M the `qa-tester`, which runs the feature against the spec's scenarios and edge cases the way a user would (CLI, HTTP, browser or a script), without being told about the code, and writes `qa-report.md`; its failures are findings like the others. A single-session Lite feature and a backlog's Feature close run the qa-tester too. On full security the security-only reviewers join the same round, and the dependency audit runs in the session meanwhile. All findings are fixed together, each with a failing test first, and fixed high findings are listed under `## Fixed` in `review.md` for Learn. Then one re-verification: the full suite in the session on `Flow: lite`, a fresh verifier on the full flow and S. A re-verification that fails gets another fresh verifier round without asking you. Outside these rounds you can ask for a QA round any time; then you decide what its failures mean. After round 3 fails, the orchestrator stops and brings you what still fails, what each round changed, and a root-cause hypothesis.

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
| `code-explorer`, `code-architect` | Define's design: trace existing code, propose architectures |
| `verifier` | Prove: fresh, independent verification each round, including red-green |
| `qa-tester` | Prove on M and at feature close (and on request): runs the feature against the spec as a user would, without reading the code; its failures are findings |
| `pr-test-analyzer`, `silent-failure-hunter` | Prove: test gaps (rated 1–10), swallowed errors |
| `code-reviewer` | Prove's parallel round, with the shared reviewer brief |
| `comment-analyzer`, `type-design-analyzer`, `code-simplifier` | `/sdlc:review-pr`, chosen by the diff (the orchestrator has no simplifier pass) |
| `ui-reviewer` | Prove's parallel round when UI files change: design-system conformance, AI-slop styling, states, accessibility; screenshots on request |
| `feature-reviewer`, `code-reviewer` | Prove, on full security: security-only review brief |
| `conversation-analyzer` | `/sdlc:hookify` (Learn, or on request): find behaviors worth preventing with hooks |

### Commands

| Command | Does |
|---|---|
| `/sdlc:start [request]` | Start a feature, or resume the active one if the request is empty |
| `/sdlc:setup [what you're building]` | Set the repo up once (greenfield or brownfield); resumes if interrupted |
| `/sdlc:upgrade [--dry-run] [--revisit]` | Bring the repo's scaffold up to the installed plugin version |
| `/sdlc:eject` | Remove the plugin's files from the repo, keeping your work |
| `/sdlc:doctor` | Health check of the machine, the plugin and the repo, with a fix for each problem. Changes nothing |
| `/sdlc:deploy` | Deploy on request: the project's existing deploy path, `release.md`, your go-ahead before production or a DB migration, a smoke test |
| `/sdlc:status` | Setup state and version drift, then one line per feature in `.sdlc/`: track, phase, last gate; open questions. Changes nothing |
| `/sdlc:prune [--older-than 45d]` | Delete the plan, reports, review and checklists of merged features marked done; keeps spec, design, retro and state. Asks first, one commit |
| `/sdlc:context-diet` | Estimate each enabled plugin's and skill's per-call cost and propose turning the unrelated ones off for this project (`.claude/settings.local.json`, written after you approve). Any repo, Claude Code only |
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
| security-guidance | UserPromptSubmit, PostToolUse, Stop | Pattern warnings on edits, diff review at turn end, agentic review after `git commit` and `git push` (while a feature is active, build commits before Prove are reviewed with the next review-ready commit; spec 05) |
| verify-freshness | PostToolUse, PostToolUseFailure, Stop | Prove only (`Stage 5`; also Stage 6 for a feature started on the old Lite flow): stale/fresh test tracking (above) |
| model-router | PreToolUse (Agent) | While a feature is active: denies a subagent dispatch that names no model, asks for Fable without `Top model: fable`, or runs a reviewer below Opus on `Risk: high`; logs every dispatch with the stage to `.sdlc/.work/dispatches.jsonl` |
| trust-anchor | Stop, UserPromptSubmit | Tells you when what verification trusts changes: Track, Risk, Flow or Top model; new baseline failures; changed commands; the spec after Prove began; leaving Prove with untested code, or on `Flow: lite` any Stop outside Build and Prove with untested code. Your next message accepts it. A change that only makes the process stricter (Track up, Risk low → high, Flow lite → full) is shown without waiting for you |
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
  state/<feature>.md       track, phase, gate log, deviations, open questions, and the feature's Docs: folder
  lint/                    sdlc lint snippets your ESLint/Ruff config imports (seeded)
  ci/invariants.py         checks test reports, the baseline and specs of active features in CI (seeded)
  ci/contract-check.sh     the API contract check CI runs (multi-app repos that chose it; seeded)
  .work/                   scratch, git-ignored (also verify-freshness.json)
docs/sdlc/                 docs_dir: the documents people read (default; setup asks when the repo publishes docs/)
  constitution.md          project principles (yours)
  design-system.md         the design system UI work follows (UI projects; yours)
  recurring-defects.md     defects Prove fixed, one line each: Learn adds, Define and reviewers read
  intents/<feature>/
    brief.md  brainstorm.md  spec.md  design.md  backlog.md  plan-B<n>.md  test-report.md  qa-report.md  review.md  security.md  release.md  retro.md
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
Docs: <intents>   (this feature's documents folder)
Track: S | M | L   (sized up because: <named signal, or "—">)
Risk: low | high   (<signal>)
Flow: lite | full   (lite: M with risk low unless you asked for full, or any backlog feature)
Build: native | subagent | tasks   (the track's default, shown at Define's approval)
Top model: opus   (fable only if the user chose it)
Commands: test: `<test command>`   (monorepo: one per package; no setup: the detected command)
Base: <commit the feature started from>
Owner: <git email of whoever advances it>   Tool: <claude-code | codex | cursor | antigravity>
Verified: <commit the Prove gate passed on> tree <worktree tree at that gate>
Slice: B<n>   Slice base: <commit>   Slice gates: none   (backlog features only)
Current: Stage 1 – Define   (then Stage 4 – Build, Stage 5 – Prove, Stage 8 – Ship)
## Stages (1 Define, 4 Build, 5 Prove, 8 Ship) / ## Verify rounds / ## Gate log / ## Deviations / ## Open questions
```

The orchestrator never edits this file by hand: `scripts/state.py` makes each change in one call and writes the control contract beside it (`<feature>.json`, `<feature>.events.jsonl`; git-ignored) for a runner or control app ([spec 12](specs/12-control-contract.md)).

### Three-tier knowledge

| Tier | Where | Loads |
|---|---|---|
| 1 | `CLAUDE.md` (≤ 60 lines) | every session |
| 2 | `.claude/rules/<area>.md` with `paths:` | automatically, when matching files are touched |
| 3 | `knowledge/**.md` | on demand, via `knowledge/index.md` and links from tier 2 |

`retro.md` is history and is not loaded by later sessions. Learn promotes a durable lesson when the feature found one. Something corrected twice and checkable by machine becomes a hookify rule instead of more text.

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
| Phase | Define, Build, Prove or Ship; each runs at one internal stage number (1, 4, 5, 8) that the hooks read |
| Gate | Exit criterion for a phase |
| Hard stop | A gate where the orchestrator always asks you |
| Round | One verification pass in Prove; a new verifier each time; it stops after 3 fail |
| Stale / fresh | Whether test results predate the latest code change |
| Public Surface | Declared list of everything new that callers or users can see |
| Complexity Tracking | Design table that ties every addition to a requirement |
| Deviation | A gate you chose to skip, recorded in `state.md` |
| Constitution | Project principles in `docs/sdlc/constitution.md`, checked in Define |
| Design system | `docs/sdlc/design-system.md`: the library, tokens, components and patterns UI work must use; checked by `ui-reviewer` in Prove |
| Project commands | `install`, `test`, `lint`, `typecheck`, `build` in `.sdlc/config.json`, per package in a monorepo |
| Baseline | Failures that existed before setup; Prove only fails on new ones |
| Scaffold version / drift | The plugin version a repo was set up or upgraded with; "behind" means `/sdlc:upgrade` has work to do |
| Generated / seeded | Plugin files that upgrades regenerate / replace only while you haven't edited them |
| Migration | A versioned change to files you own, applied only with your approval |
