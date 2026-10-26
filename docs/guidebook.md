# sdlc guidebook

What the plugin is, how it works, and where things live. For "what do I do when…", see the [playbook](playbook.md). For "something is broken", see the [runbook](runbook.md). Install is in the [README](../README.md).

## The idea

`sdlc` is one Claude Code plugin that takes a piece of work from request to shipped and learned-from. An **orchestrator** skill runs it: it sizes the work, runs one phase at a time (Define, Build, Prove, Ship), calls the bundled skills, subagents and commands for that phase, records progress in `.sdlc/state/<feature>.md`, and stops at **gates**. Nothing outside the plugin is needed for the core phases.

Four ideas carry the design:

1. **Smallest process that fits.** Work is sized S, M or L. The orchestrator picks the smallest track that fits and sizes up only for a named signal, because a bigger track brings brainstorming and design, which invite a bigger solution.
2. **Gates, not vibes.** Every phase has an exit criterion. A failed gate means stay in the phase or step back one. Most gates the orchestrator checks itself; a few are **hard stops** where you decide.
3. **Independent checking.** The context that wrote the code never verifies or reviews it on M and L: each verification round uses a fresh `verifier` subagent, and review uses separate reviewer agents. S, the smallest track, is the exception: it is built and verified in one place, repro test first, and the session runs the full suite once.
4. **Nothing stays in the conversation.** Define writes everything the build needs into three files (`intent.md`, `spec.md`, `plan.md`), so a fresh agent can build from them alone.

## Project setup

Before the first feature, `/sdlc:setup` prepares the repo once; `/sdlc:start` offers it when a repo isn't set up. See [sdlc_setup_phase.svg](diagrams/sdlc_setup_phase.svg).

**The project's commands.** Setup records the repo's own `install`, `test`, `lint`, `typecheck` and `build` commands in `.sdlc/config.json`, exactly as the team runs them (`pnpm test`, `go test ./...`, `make lint`, …); a step the repo doesn't have is `null`. Everything that runs them reads them from there, so nothing in the plugin is stack-specific. A monorepo lists `packages`, each with a path, a stack and its own commands, run from its directory; a polyglot repo is several packages with different stacks.

**It adds no tooling you didn't ask for.** Setup never changes the product's manifest or dependencies: no new fields (`bin`, `engines`, `packageManager`, scripts), no new linter, formatter or devDependency, and no tool installed without asking.

- **Greenfield** (no source yet): a short stack interview, then a proposal you approve. The ecosystem's own generator builds the skeleton, plus the test runner and one passing smoke test. A linter, toolchain pinning and extra manifest fields are separate choices in the proposal, off unless you say yes.
- **Brownfield** (existing code): the commands the repo already uses, shown to you before they're written; a **baseline** of what already fails; an audit (conventions, git-history gotchas, decisions, area rules) drafted by explorer agents and written only as you approve each batch; existing AI configs (long CLAUDE.md, AGENTS.md, Cursor rules, ADRs) migrated into the three knowledge tiers, one diff per source.
- **Common steps, both modes:** policy rules (`.claude/rules/sdlc*.md`); hookify guardrails; sdlc lint snippets, only for a linter the project already has; a permission allowlist for the project's commands; with your approval, the sdlc marketplace and `enabledPlugins` in `.claude/settings.json` so teammates are offered the plugin; with your approval, a context diet (`/sdlc:context-diet`) for this project; a CI workflow from the recorded commands (asked first if the repo already has CI); the sdlc block in `AGENTS.md` when another agent (Codex, Cursor, Antigravity) uses the repo; `.gitignore` entries; a constitution (with the default Simplicity principle); a design system (projects with UI); and the knowledge folder. The steps that write `.claude/` run only under Claude Code.

Setup runs on an `sdlc/setup` branch with one commit per step, resumes where it stopped, and ends by asking whether to open a PR or merge locally.

**Who owns which file.** Everything the plugin puts in a repo is tracked in `.sdlc/scaffold.lock.json` with a class that decides what an upgrade may do:

| Class | Examples | On upgrade |
|---|---|---|
| Generated | `.claude/rules/sdlc*.md` | regenerated |
| Seeded | `.claude/hookify/sdlc-*.md`, `.github/workflows/sdlc-verify.yml`, `sdlc-invariants.yml`, `.sdlc/ci/invariants.py`, `.sdlc/lint/*` | replaced only if you haven't edited it; otherwise you choose: merge, skip, or keep yours for good |
| Keyed merge | allowlist and plugin-enablement keys in `.claude/settings.json`, `.gitignore` lines, the `<!-- sdlc:begin -->` block in `AGENTS.md` | only the entries the plugin added; your text around the block is never touched |
| Yours | the commands in `.sdlc/config.json`, `CLAUDE.md`, constitution, design system, `knowledge/`, baseline, your own rules | changed only by migrations you approve |

Files named `sdlc-*` belong to the plugin; everything else is yours.

**Upgrades.** When the plugin is newer than the repo's scaffold, `/sdlc:start` and `/sdlc:status` suggest `/sdlc:upgrade`, which never blocks your work. It runs on its own branch: regenerate, replace untouched files, walk you through edited ones, then apply versioned migrations one diff at a time (declined ones are asked again only with `--revisit`). The repo pins a minimum plugin version, so teammates on an older plugin get a warning. `/sdlc:eject` removes what the plugin owns and keeps your work.

## Tracks

| Track | Use when | Phases |
|---|---|---|
| **S · fix** | bug or tweak, 1–3 files, clear expected behavior | Define writes short `intent.md`, `spec.md` and `plan.md` with no approval; Build builds and verifies in one place; Prove dispatches nothing; then Ship |
| **M · feature** | a few files to a few days, approach mostly obvious | all four; risk low: `Flow: lite` (default), Prove is one fresh verifier; risk high or on request: `Flow: full`, with light review |
| **L · project** | new service or module, unclear approach, or touches auth, payments, data migration, public API | all four, with brainstorming and design in Define; `Flow: full` |

Anything touching auth, payments, secrets, PII or schema migrations is at least M and gets full security in Prove. You can override the size at any time.

**Lite and full.** Every track has the same shape: one approval (none on S), one build, one Prove round (S: the session's own full-suite run), one commit. `Flow: lite` is the default for M with `Risk: low` and for any backlog feature, because evals showed the old full M flow costing several times the tokens and more approvals for the same hidden-test results ([ADR 0008](adr/0008-lite-flow-for-low-risk-m.md)). On Lite the orchestrator writes the spec and plan itself, Prove is one fresh verifier with no reviewers, and fixes are re-verified with the full suite in the session. On full, `writing-specs` (with a checklist) and `writing-plans` write them, one light, read-only code-reviewer on `sonnet` covers correctness, silent failures and security, and fixes are re-verified in the session as on Lite, unless the verifier itself failed a requirement or a fix went beyond the findings (then a fresh verifier). There is no qa-tester on M full ([ADR 0012](adr/0012-enforced-prove-budget.md)). A Lite feature sizes up to full when the spec needs a design decision the request doesn't settle, or risk turns out high.

**Backlog slices.** M or L work bigger than one session (more than about 8 tasks, or several distinct parts) gets a `backlog.md` of vertical slices, approved with the other Define files; S never gets one. `plan.md` then outlines each slice. Each slice writes its `plan-B<n>.md`, builds natively, gets one Prove round on its own diff, and is committed. Slices run back to back without asking until the round cap, a backlog change that adds scope, or a hard stop; per-slice stops are opt-in (`Slice gates: plan, review, commit`). After the last slice, **feature close** runs one Prove round over the whole branch, then Ship. When context runs low it stops at a slice boundary and names the next one; `/clear` then `/sdlc:start` picks it up (`/sdlc:start B<n>` for a named slice). **Autopilot** (`python3 <plugin>/scripts/autopilot.py <feature>` in a terminal, only when you ask) runs each slice and then feature close in a fresh headless Claude Code session, up to your merge decision; it stops on a blocked slice, a run that changed nothing, or a trust-anchor notice you haven't seen.

**Risk and models.** Risk is recorded apart from size: `Risk: high` for auth, payments, secrets, PII, schema migrations, a public API, or untrusted input reaching a shell, terminal, file path or database (S and M lite run no reviewer). Track and risk pick each subagent's model tier and Prove's checkers: the cheap and standard tiers are both `sonnet`, dispatched with `effort: high`; the top tier is `opus`. `haiku` is never used. Reviewers, the verifier and the qa-tester run on `opus` only on L; an M feature at risk high reviews on `sonnet`. Fable is used only if you ask ("use fable"), which sets `Top model: fable`. The session's model is yours; the start announcement may suggest `/model opus` or `/model sonnet` once, never blocking. See [sdlc_tracks_full_stage_tree.svg](diagrams/sdlc_tracks_full_stage_tree.svg).

**Why Prove is bounded.** On planner-team eval rounds 8–10 the plugin took 4–7x the baseline's wall-clock time and about 6x its tokens, mostly from unbounded verifier and QA probing and from repeated fresh-verifier rounds, with no measured quality gain from that work. The target is at most 2x the time and 2.5x the tokens, with hidden-test results and blind-review defects held level. That is not yet evaluated ([ADR 0011](adr/0011-track-cost.md)). So S dispatches no checkers, M lite one verifier, M full one light review; every checker has a time budget and a probe cap; and a requirement that fails twice stops the loop and goes to you ([Verification](#verification)). In eval rounds 12–13 that budget, given as instructions only, was not followed: single commands ran 4–7 minutes, background runs were polled in loops, and M full's Prove still took 40–50 minutes with QA on the critical path. So a hook now enforces the per-command limit, and M full drops QA and the second verifier ([ADR 0012](adr/0012-enforced-prove-budget.md)).

## The four phases

| Phase | Produces | Gate |
|---|---|---|
| Define | `intent.md`, `spec.md`, `plan.md` on every track; `backlog.md` when sliced; on the full flow `checklists/requirements.md`; `design.md` and its set when a design runs | **You approve once** (not on S). No `[inferred]` tags left, acceptance criteria testable, every requirement has a task, the three files stand alone |
| Build | code, tests; deviations written into `plan.md` | Every task done, build and full test suite pass, no TODO without a ticket |
| Prove (max 3 failed rounds) | `test-report.md`, `review.md`, `qa-report.md` (when the qa-tester runs), `security.md` (full security) | Fresh verifier PASS on the current commit, or the in-session suite after fixes where Prove re-verifies in the session (S: the repro test failed before the fix and the full suite passes in the session), every acceptance criterion has evidence, no unresolved high finding, no test gap rated 8+ (L), no critical or high security finding, no secrets in the diff |
| Ship, with Learn | `recurring-defects.md` lines (L: `retro.md`, a knowledge page), one commit, then a PR or merge on your word | Verified-tree check clean, Learn done, CI green. **Never merged without you saying so** |

**Define's three files.** `intent.md` is the why: the request verbatim, questions and answers, the approaches weighed, the chosen one and why, and how it works at design level (S: 10–20 lines; M: about a page; L: written by `brainstorming`). `spec.md` is the what: requirements and acceptance criteria, no files or tasks. `plan.md` is the how: tasks with their files, first test, command and requirement, plus Public Surface, UI mapping, Review Focus and Deviations. Reviewers read `intent.md` first.

**Build** works from `plan.md` (a slice: `plan-B<n>.md`), never from memory. `Build:` is `native` (in the session), `subagent` (one fresh implementer) or `tasks` (subagent-driven development with a review per task), taken from the track (S `subagent`, M `native`, L `tasks`) and shown in Define's approval; change it in your reply.

**Prove** is one parallel round on one commit, with a time budget on every checker ([Verification](#verification)). **Learn**, in Ship, is small: the defects Prove fixed go to `recurring-defects.md`, and a lesson is filed only when there is one.

Internally each phase keeps a stage number, because the hooks read it: `Stage 1 – Define`, `Stage 4 – Build`, `Stage 5 – Prove`, `Stage 8 – Ship`. A backlog slice rests at Stage 6 after its commit. A feature started under the old 11 stages resumes in the phase its number maps to ([ADR 0010](adr/0010-four-phases.md)). **Deploy** is not a phase: `/sdlc:deploy`, on request, uses the project's existing deploy path, asks your go-ahead before a production deploy or DB migration, runs a smoke test and writes `release.md`.

Each phase starts with a header:

```
▶ <Phase>   (track M, flow lite)
  Using: <skills/agents/commands>
  Gate:  <exit criterion>
```

The whole loop, with hard stops, is in [sdlc_orchestrator_decision_tree.svg](diagrams/sdlc_orchestrator_decision_tree.svg); per-phase skills, subagents, hooks and gates are in [sdlc_full_flow.svg](diagrams/sdlc_full_flow.svg).

### Hard stops

The orchestrator always asks you before: Define's approval (not on S), anything that adds scope, the round cap (3 failed rounds), a requirement that fails in two rounds, any merge, production deploys, DB migrations, and anything irreversible. Everything else runs without asking, including failed verify rounds below the cap. Where an advisor is available, the orchestrator consults it at most twice per feature: before Define's approval and before Ship's commit. If you say "skip" or "just ship it", it names the gates being skipped, records them under Deviations in `state.md`, then complies.

## Scope tracing

Every phase ties additions back to a request:

- **Questions come once.** Before `intent.md` (L: before brainstorming), the orchestrator asks only what would change what gets built, in one message, or nothing. Every other open point is a guess tagged `[inferred]`, which you keep or veto at the approval. `clarifying-specs` runs only when you ask.
- **Specs** tag each requirement `[user]`, `[clarified]` or `[inferred]` (Lite: an `Inferred` list) and have a Non-Goals section. At the approval, `[inferred]` items are listed on their own and **dropped unless you keep them**; dropped ones move to Non-Goals.
- **Designs** keep a Complexity Tracking table: every new module, layer, abstraction, dependency, service, config key or store cites a requirement or comes out.
- **Plans** tie each task to a requirement and declare a **Public Surface** (every new export, endpoint, command, config key, env var, dependency).
- **Review** runs `scripts/diff_stats.py --plan` to flag exports and dependencies missing from the Public Surface; unrequested public surface is high severity. Every reviewer also checks the spec's failure modes and the recurring-defects list (the plugin's seed plus the project's own). It's the feature's only whole-branch review, and simplifications are findings like any other.

## Verification

**The freshness hook.** While `state.md` says `Current: Stage 5 – Prove` (on `Flow: lite`, also Stage 6), Prove is the only phase with a hook that blocks you:

- any code change (by any tool, in a git repo) marks test results **stale**;
- a **full** test run marks them **fresh**. A run that names a test file, a pytest node id, a single Go package or a name filter doesn't count;
- finishing a turn while stale is blocked with "re-run tests".

The full run is the `test` command from `.sdlc/config.json`, with no extra arguments. In a monorepo freshness is per package: an edit under `services/api/` makes only `api` stale, and `cd services/api && <api's test command>` makes it fresh again; a file outside every package makes all of them stale. A root-level test command (e.g. `turbo run test`) counts for every package.

**The baseline.** Failures listed in `.sdlc/baseline.md` (recorded at brownfield setup) don't fail a round: the verifier fails only on **new** failures, removes baseline items that now pass, and never adds any. Accepting a new failure into the baseline is your decision, recorded as a Deviation.

**The round.** On the review-ready commit, the orchestrator dispatches the track's checkers at once, each fresh:

| Track | Verifier | Code reviewer | Also | Security |
|---|---|---|---|---|
| S | — | — | the session runs the full suite once | hooks only |
| M, `Flow: lite` | standard | — | — | light |
| M, `Flow: full`, either risk | standard | one light review, standard | ui-reviewer on UI | light; full, standard, on auth, payments, secrets, PII, migrations |
| L | top | top | silent-failure-hunter, pr-test-analyzer; ui-reviewer on UI | full, top |
| Backlog slice | standard (top on risk high) | the same, this slice only | ui-reviewer on UI | at feature close |
| Feature close | the same, whole branch | top, `Base..HEAD` | qa-tester; ui-reviewer on UI | light; full on L or risk high |

The light review is the only code reviewer on M full: its brief covers correctness, silent failures and security in one pass. The `ui-reviewer` joins on a UI diff, except on S and M lite. The `verifier` runs everything fresh, proves each acceptance criterion in `test-report.md`, and checks red-green: with the feature's code put back to `Base:`, its tests must fail. Light security is the dependency audit and the security hooks' findings, in the session; full security adds a security-only `feature-reviewer` and `code-reviewer` (top tier on L, `sonnet` on M).

**Bounded checks.** The verifier and the qa-tester run every command that isn't the project's own with a 2-minute limit, and get 10 minutes each per round. In Claude Code the prove-budget hook enforces the limit for everyone in Stage 5: the command runs under `timeout 120` and is killed there (exit 124, "could not verify within budget"), and background runs, Monitor and the PowerShell tool are refused for it, so nothing is polled. The verifier's red-green run on Base has a per-test timeout, and a test that times out there counts as failing. Code reviewers are read-only: they read code and diffs and may run the project's test command, and a suspicion that needs a probe is a finding. Whatever they can't prove is "could not verify within budget": it goes to you and is never counted as passed. With a qa-tester in the round the verifier writes no probes; without one it writes at most 5, and the qa-tester at most 5 of its own. Probes prefer planted states and fixed kill points to repetition, repeat at most 5 times, and stop once a gap reproduces in an area. Probe scripts live in `.sdlc/.work/probes/` (verifier) or `.sdlc/.work/qa/` (qa-tester); a defect a probe found becomes a failing test in the project's suite before the fix.

**Fix, then re-verify once.** All high findings are fixed together, each with a failing test first; medium and low go to `review.md` as tickets, and fixed high findings are listed under `## Fixed` in `review.md` for Learn. Then one re-verification: on S, `Flow: lite`, `Flow: full`, slices and feature close, the full suite in the session; on L, and on the full flow when the verifier itself failed a requirement or a fix touched files outside the findings, a fresh verifier. A re-verification that fails is fixed and checked again without asking you, with two stops: the same requirement failing in two rounds, and round 3 failing. Then the orchestrator brings you what still fails, what each round changed, and a root-cause hypothesis. You can ask for a QA round any time; outside Prove's rounds you decide what its failures mean.

## Building blocks

### Skills (`sdlc:` namespace)

| Group | Skills |
|---|---|
| Conductor | `orchestrator` |
| Set up | `setting-up-projects` (setup, upgrade, eject), `trimming-context` (`/sdlc:context-diet`) |
| Specify and design | `brainstorming`, `writing-specs`, `clarifying-specs`, `designing-solutions`, `project-constitution` |
| Plan and build | `writing-plans`, `analyzing-consistency`, `using-git-worktrees`, `subagent-driven-development`, `executing-plans`, `dispatching-parallel-agents`, `test-driven-development`, `systematic-debugging` |
| Check | `verification-before-completion`, `requesting-code-review`, `receiving-code-review` |
| Ship and learn | `finishing-a-development-branch`, `managing-knowledge`, `claude-md-improver`, `writing-hook-rules`, `todo` |

### Subagents

| Agent | Used for |
|---|---|
| `code-explorer`, `code-architect` | Define's design: trace existing code, propose architectures |
| `verifier` | Prove on M and L: fresh, independent verification each round, including red-green, within a time budget |
| `code-reviewer` | Prove on M full, L, slices and feature close: the round's code review, with the shared reviewer brief (M full: one light review covering correctness, silent failures and security) |
| `qa-tester` | Prove at feature close, or on request: runs the feature as a user would, without reading the code |
| `silent-failure-hunter`, `pr-test-analyzer` | Prove on L: swallowed errors; test gaps rated 1–10 |
| `ui-reviewer` | Prove on M full, L and backlog features, when UI files change: design-system conformance, AI-slop styling, states, accessibility; screenshots on request |
| `feature-reviewer` (with `code-reviewer`) | Prove, on full security: security-only review |
| `comment-analyzer`, `type-design-analyzer`, `code-simplifier` | `/sdlc:review-pr`, chosen by the diff |
| `conversation-analyzer` | `/sdlc:hookify`: find behaviors worth preventing with hooks |

### Commands

| Command | Does |
|---|---|
| `/sdlc:start [request]` | Start a feature, or resume the active one if the request is empty (`B<n>`: a named slice) |
| `/sdlc:setup [what you're building]` | Set the repo up once (greenfield or brownfield); resumes if interrupted |
| `/sdlc:upgrade [--dry-run] [--revisit]` | Bring the repo's scaffold up to the installed plugin version |
| `/sdlc:eject` | Remove the plugin's files from the repo, keeping your work |
| `/sdlc:doctor` | Health check of the machine, the plugin and the repo, with a fix for each problem. Changes nothing |
| `/sdlc:status` | Setup state and version drift, then one line per feature: track, phase, last gate, open questions. Changes nothing |
| `/sdlc:deploy [feature] [environment]` | Deploy on request through the project's own deploy path, with your go-ahead before production or a DB migration |
| `/sdlc:prune [--older-than 45d]` | Delete the working files of merged, finished features; keeps intent, spec, design, retro and state. Asks first, one commit |
| `/sdlc:context-diet` | Propose turning off plugins and skills this project doesn't need, in `.claude/settings.local.json`, after you approve. Any repo, Claude Code only |
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
| security-guidance | UserPromptSubmit, PostToolUse, Stop | Pattern warnings on edits, a diff review at turn end, an agentic review after `git commit` and `git push`. During a feature, build commits before Prove are reviewed together with the next review-ready commit ([spec 05](specs/05-security.md)) |
| verify-freshness | PostToolUse, PostToolUseFailure, Stop | Stage 5 (on `Flow: lite`, also Stage 6): stale/fresh test tracking ([above](#verification)) |
| prove-budget | PreToolUse (Bash, PowerShell, Monitor) | In Prove (Stage 5): a Bash command other than the project's own (`.sdlc/config.json` commands) is rewritten to run under `timeout -k 5 120` (a compound one under one `bash -c`), with the tool timeout at 130 s; such a command is refused `run_in_background`, Monitor and PowerShell; the project's own commands are untouched |
| model-router | PreToolUse (Agent) | While a feature is active: denies a dispatch that names no model or names `haiku`, asks for Fable without `Top model: fable`, or runs a reviewer, the verifier or the qa-tester below Opus on `Track: L`; logs every dispatch to `.sdlc/.work/dispatches.jsonl` |
| trust-anchor | Stop, UserPromptSubmit | Tells you when what verification trusts changes: Track, Risk, Flow, Top model or Base; new baseline failures; changed commands; the spec after Prove began; untested code leaving Prove (on S, a passing full run of the current code is the evidence, as no verifier is dispatched). It blocks once; your next message accepts it. A change that only adds checks (Track up, Risk low → high, Flow lite → full) is shown without blocking, except Flow lite → full on a backlog feature |
| role-guard | PreToolUse (file tools) | Holds the plugin's agents to their role: reviewers can't edit files, the verifier writes only its report, the baseline, its red-green worktree and its probe scripts, the qa-tester can't read or search code. Bash stays open to them |
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
  state/<feature>.json, <feature>.events.jsonl   control contract for a runner or control app (git-ignored)
  lint/                    sdlc lint snippets your ESLint/Ruff config imports (seeded)
  ci/invariants.py         checks test reports, the baseline and specs of active features in CI (seeded)
  ci/contract-check.sh     the API contract check CI runs (multi-app repos that chose it; seeded)
  .work/                   scratch, git-ignored (freshness, dispatch log, trust anchor, QA runs)
docs/sdlc/                 docs_dir: the documents people read (default; setup asks when the repo publishes docs/)
  constitution.md          project principles (yours)
  design-system.md         the design system UI work follows (UI projects; yours)
  recurring-defects.md     defects Prove fixed, one line each: Learn adds, Define and reviewers read
  intents/<feature>/
    intent.md  spec.md  plan.md                       Define, every track
    backlog.md  plan-B<n>.md                          backlog features
    design.md  research.md  data-model.md  contracts/  quickstart.md  checklists/   design and full flow
    test-report.md  review.md  qa-report.md  security.md                        Prove
    retro.md  release.md                              Ship (L), /sdlc:deploy
knowledge/                 tier 3, on-demand docs (index.md links everything)
.claude/rules/<area>.md    tier 2, loads when matching paths are touched (yours)
.claude/rules/sdlc*.md     plugin policy rules: workflow, code style, tests, migrations, sensitive areas, CI, UI (generated)
.claude/hookify/*.md       team hookify rules; sdlc-*.md are the plugin's guardrails (seeded)
.github/workflows/sdlc-verify.yml       CI generated from the commands in config (seeded)
.github/workflows/sdlc-invariants.yml   runs .sdlc/ci/invariants.py on pull requests and pushes (seeded)
CLAUDE.md                  tier 1, at most 60 lines (never touched by the plugin)
```

Each feature is named `<yyyy-mm-dd>-<s|m|l>-<slug>`, or `<yyyy-mm-dd>-<s|m|l>-<ticket>-<slug>` with a ticket (e.g. `2026-10-22-m-PROJ-123-month-filter`). The letter is the track it started on; a later size-up doesn't rename it. The branch uses the same name. Commit the state file and everything under `docs/sdlc/intents/<feature>/`. A repo set up before 1.7.0 keeps everything in `.sdlc/<feature>/` until `/sdlc:upgrade` moves it; the hooks read both layouts meanwhile ([ADR 0006](adr/0006-split-sdlc-docs-from-machinery.md)).

### `state.md`

Resume depends on this file. The orchestrator looks for `.sdlc/state/*.md` with `Status: active`: one match resumes, several asks which, none starts a new feature.

```markdown
# <feature>
Status: active
Docs: <intents>   (this feature's documents folder)
Track: S | M | L   (sized up because: <named signal, or "—">)
Risk: low | high   (<signal: auth, payments, secrets, PII, migration, public API, untrusted input>)
Flow: lite | full   (lite: M with risk low unless you asked for full, or any backlog feature)
Build: native | subagent | tasks   (the track's default, shown at Define's approval)
Top model: opus   (fable only if you chose it)
Commands: test: `<test command>`   (monorepo: one per package; no setup: the detected command)
Started: <date>
Base: <commit the feature started from>
Owner: <git email of whoever advances it>
Tool: <claude-code | codex | cursor | antigravity>
Verified: <commit the Prove gate passed on> tree <worktree tree at that gate>
Slice: B<n>   Slice base: <commit>   Slice gates: none   (backlog features only)
Current: Stage 1 – Define   (then Stage 4 – Build, Stage 5 – Prove, Stage 8 – Ship)

## Stages            (1 Define, 4 Build, 5 Prove, 8 Ship)
## Verify rounds
## Gate log
## Deviations
## Open questions
```

The orchestrator writes this file once from the template, then never edits it by hand: `scripts/state.py` makes each change in one call and writes the control contract beside it ([spec 12](specs/12-control-contract.md)). Before advancing someone else's feature (`Owner:`), it asks and records the handover.

### Three-tier knowledge

| Tier | Where | Loads |
|---|---|---|
| 1 | `CLAUDE.md` (≤ 60 lines) | every session |
| 2 | `.claude/rules/<area>.md` with `paths:` | automatically, when matching files are touched |
| 3 | `knowledge/**.md` | on demand, via `knowledge/index.md` and links from tier 2 |

`retro.md` is history and is not loaded by later sessions. Learn files a durable lesson in the right tier when the feature found one. Something corrected twice and checkable by machine becomes a hookify rule instead of more text.

### Configuration

Setup writes `.sdlc/config.json`; it's yours to edit and holds only what differs from the plugin's defaults (`templates/project/config.defaults.json`, deep-merged, your values win, lists replace). Most teams only touch it to change a command.

| Key | Meaning |
|---|---|
| `commands` | `install`, `test`, `lint`, `typecheck`, `build` as the team runs them. `null` means the step doesn't apply |
| `packages` | Monorepo instead of `commands`: `[{"name", "path", "stack", "commands"}]`, each run from its path. A root `commands.test` (e.g. `turbo run test`) counts for every package |
| `project.kind` | `greenfield` or `brownfield`, set by setup |
| `project.profile`, `project.owners` | Multi-app repos: `lean` or `large` (the answer to "who works here"), and for `large` the CODEOWNERS entries (`{pattern: [handles]}`, in order) |
| `api_contract` | Multi-app repos with the contract check: `{"path", "spec"}` of the versioned API contract |
| `docs_dir` | Where the sdlc documents live (default `docs/sdlc`; `.sdlc` or another in-repo folder if `docs/` is published as a site). Without it a repo is on the old all-in-`.sdlc/` layout |
| `contract.required` | The commands every package must list, `null` allowed (default all five) |
| `verify.order` | Order of the verify steps (default lint, typecheck, build, test) |
| `areas.*` | Path patterns for the policy rules and reviewers: `source`, `ui`, `tests`, `migrations`, `sensitive`, `ci` |
| `ci` | `os` matrix (default `["ubuntu-latest"]`; add `"windows-latest"` if teammates develop on Windows) and toolchain versions (`node_version`, `java_version`, `dotnet_version`, `oasdiff_version`) for the generated workflow |
| `baseline` | Where the known-failures baseline lives (default `.sdlc/baseline.md`) |
| `min_plugin_version` | Teammates on an older plugin get a warning to update |

After changing commands or `ci`, run `/sdlc:upgrade` so the generated CI workflow follows. Don't edit `.sdlc/scaffold.lock.json` by hand. Why it's designed this way: [ADR 0001](adr/0001-project-setup-upgrade-eject.md), [ADR 0002](adr/0002-record-the-repos-own-commands.md), [ADR 0005](adr/0005-greenfield-monorepo-layout.md), [ADR 0006](adr/0006-split-sdlc-docs-from-machinery.md), [ADR 0007](adr/0007-multi-tool-adapters.md); the `scaffold.py` reference is in the [runbook](runbook.md#setup-upgrade-eject-internals).

## Glossary

| Term | Meaning |
|---|---|
| Phase | Define, Build, Prove or Ship; each runs at one internal stage number (1, 4, 5, 8) that the hooks read |
| Gate | Exit criterion for a phase |
| Hard stop | A point where the orchestrator always asks you |
| Round | One verification pass in Prove, with a new verifier each time; it stops after 3 fail |
| Stale / fresh | Whether test results predate the latest code change |
| Slice | One vertical piece of a backlog feature, built, proved and committed on its own |
| Feature close | The whole-branch Prove round and Ship after a backlog's last slice |
| Public Surface | Declared list of everything new that callers or users can see |
| Complexity Tracking | Design table that ties every addition to a requirement |
| Deviation | A gate you chose to skip, or another departure, recorded in `state.md` |
| Trust anchor | The hook that shows you changes to what verification trusts |
| Constitution | Project principles in `docs/sdlc/constitution.md`, checked in Define |
| Design system | `docs/sdlc/design-system.md`: the library, tokens, components and patterns UI work must use; checked by `ui-reviewer` |
| Project commands | `install`, `test`, `lint`, `typecheck`, `build` in `.sdlc/config.json`, per package in a monorepo |
| Baseline | Failures that existed before setup; Prove fails only on new ones |
| Scaffold version / drift | The plugin version a repo was set up or upgraded with; "behind" means `/sdlc:upgrade` has work to do |
| Generated / seeded | Plugin files that upgrades regenerate / replace only while you haven't edited them |
| Migration | A versioned change to files you own, applied only with your approval |
