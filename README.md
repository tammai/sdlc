# sdlc

One Claude Code plugin for the whole software lifecycle. An orchestrator walks each piece of work through four phases (Define, Build, Prove, Ship), from spec to shipped and learned-from, and calls the bundled skills, agents, commands and hooks at each one. No other plugin is required.

Docs: [guidebook](docs/guidebook.md) (how it works) · [playbook](docs/playbook.md) (what to do when…) · [runbook](docs/runbook.md) (install, health, fixes) · [changelog](CHANGELOG.md)

**Contents:** [What you get](#what-you-get) · [Install](#install) · [Use](#use) · [Commands](#commands) · [Phases](#phases--what-runs) · [Knowledge](#knowledge-3-tier-loading) · [Limitations](#limitations) · [Contributing](#contributing) · [Credits and license](#credits-and-license)

## What you get

- **Sized process, not ceremony.** Work is sized S (fix), M (feature) or L (project), and only what that size needs runs. The smallest track that fits is the default.
- **Gates you can trust.** Each phase has an exit criterion. You decide at the hard stops (one approval of the spec, anything that adds scope, merge, deploy, migrations); everything else, passing checks and fixable failures included, runs on its own.
- **Independent verification.** Build proves its own work with one command, `verify.py`: every acceptance criterion's test recorded failing before its code and passing after it, plus the full checks and plan drift. On M full and L, Prove reuses that evidence and a fresh checker reads each test against its criterion (on M the one code reviewer, in its review pass; on L an `ac-checker`) (S and M lite have no Prove: Build's passing `verify.py` goes to Ship), time-boxed so nothing runs unbounded; a hook that won't let a turn finish on stale test results; and a baseline so old failures don't block new work.
- **Scope kept in check.** Requirements are traced from spec to diff: inferred requirements are dropped unless you keep them, every new abstraction or dependency cites a requirement, and undeclared public surface is flagged in review.
- **Conventions enforced where they happen.** Policy rules load while code is written, guardrails warn or block in real time (narrating comments, focused tests, secrets, force-push to main), and review gets measured facts from `diff_stats.py`.
- **UI that follows your design system.** UI work reads the project's design system, a guardrail warns on hard-coded colors and inline styles, and a UI reviewer flags off-system components and generic "AI look" styling before merge.
- **Knowledge that stays small.** Three loading tiers keep `CLAUDE.md` short; every feature ends by adding the defects it fixed to a list every later reviewer checks, and corrections that repeat become rules.
- **Any stack, any repo shape.** Setup records the commands your repo already uses, per package in a monorepo (TS, Go, Rust, Dart, Python, shell, …), and generates CI from them. A new multi-app repo becomes an `apps/` + `packages/` monorepo with a versioned API contract. Upgrades are versioned and never overwrite your edits.

## Install

From the marketplace that hosts it:

```
/plugin marketplace add tammai/sdlc
/plugin install sdlc@sdlc
```

Optional: `/plugin install sdlc-extras@sdlc` adds the companion plugin: the Ralph loop, hookify's list, configure and help commands, and four extra review agents `/sdlc:review-pr` and `/sdlc:hookify` use when present.

Restart the session afterward so the commands and hooks load. To work on the plugin from a checkout instead, see [Contributing](#contributing).

**Other coding agents** (setup detects the agent and writes its own files; [spec 11](docs/specs/11-multi-agent.md)). Setup is smoke-tested in Codex and Antigravity on Windows and in Cursor in WSL:

| Agent | Install |
|---|---|
| Codex | `codex plugin marketplace add tammai/sdlc`, then `codex plugin add sdlc@sdlc` |
| Cursor | Customize → Import from Repo with `https://github.com/tammai/sdlc`, or a clone in `~/.cursor/plugins/local` |
| Antigravity | `python3 scripts/hosts.py dist antigravity <folder>` in a clone, then `agy plugin install <folder>` (a direct `agy plugin install https://github.com/tammai/sdlc` loads only 3 of the agents, checked when there were 13) |

A repo can be shared by several agents: the first one to run setup does the shared part, and each agent after it adds only its own files.

**Update:** update the marketplace and the plugin from `/plugin`, restart, then run `/sdlc:upgrade` in each repo.

**Uninstall:** run `/sdlc:eject` in each repo first (it removes the plugin's files and keeps your work), then `/plugin uninstall sdlc`.

**Requirements:** `git`, `gh` (for `/sdlc:code-review` and PR commands), Python 3.9+ (hooks and scripts, stdlib only), Node (brainstorm visual companion), and for TypeScript code intelligence: `npm i -g typescript-language-server typescript`. The security hooks build their own Python environment on the first session start (about a minute). Your project needs nothing extra: sdlc runs the commands it already uses.

## Use

### 1. Check the install

```
/sdlc:doctor
```

One row per check (✅ / ⚠️ / ❌) for your machine, the plugin and the current repo, each problem with its fix. It changes nothing. Right after installing, expect a warning that the repo isn't set up yet.

### 2. Set up the repo (once)

```
/sdlc:setup                              # existing code
/sdlc:setup a REST API for invoices      # empty repo: say what you're building
```

- Works on a `sdlc/setup` branch, one commit per step; rerun it to resume if interrupted. Needs a clean working tree.
- **New repo:** a few stack questions, then a proposal you approve; the ecosystem's own generators build a skeleton whose commands pass on day one.
- **Existing repo:** records the commands you already use (`pnpm test`, `go test ./...`, `make lint`, …) per package, writes a **baseline** of what already fails so features aren't blamed for it, and drafts conventions, gotchas and per-area rules from the code and git history. Nothing from that audit is written until you approve it.
- Both get policy rules, guardrails (hookify), lint snippets, a permission allowlist for your commands, CI generated from those commands, a constitution and a knowledge folder. Projects with UI also get a **design system** record: the library, tokens and components you already use, or a mainstream library and minimal tokens you approve.
- On Claude Code, offers `/sdlc:context-diet` to switch off plugins this project doesn't need. That writes only your uncommitted `.claude/settings.local.json`.
- Ends by asking: open a PR, or merge locally.

What lands in the repo: `.sdlc/config.json` (your commands; to change one later, see [Configuration](docs/guidebook.md#configuration)), `docs/sdlc/constitution.md`, `docs/sdlc/design-system.md` (UI projects), `.claude/rules/sdlc-*.md`, `.claude/hookify/sdlc-*.md`, `.claude/settings.json` (command allowlist; with your approval, the sdlc marketplace and `enabledPlugins` so teammates are offered the plugin), `.github/workflows/sdlc-verify.yml` and `sdlc-invariants.yml` (checks the shared sdlc files, whichever agent changed them), `knowledge/`, and for existing code `.sdlc/baseline.md`. Your `CLAUDE.md` is never touched.

### 3. Start a piece of work

```
/sdlc:start fix: export button 500s when the report is empty
/sdlc:start add CSV export to the reports page
```

The orchestrator sizes it and proposes the smallest track that fits; you can override.

| Track | When | Phases |
|---|---|---|
| **S** fix | bug or tweak, 1–3 files | no documents: a one-line `Intent:` and the `Repro:` test in the state file (no approval) → build and verify in one place, repro test recorded red first, then `verify.py` → ship commits on a feature branch without asking (no prove) |
| **M** feature | a few files to a few days; also any change confined to 1–2 files with a settled approach, built as one piece | define (intent, spec and plan, one approval; design only if the approach isn't obvious) → build → prove → ship. Low risk: `Flow: lite`, no prove: Build's passing `verify.py` goes to ship. High risk or on request: `Flow: full`: prove reuses Build's `verify.py` run, one fresh checker (a code-reviewer) reads each acceptance test and reviews in the same pass; findings go back to build, then one re-verification. At Define's approval you can skip prove (`Prove: skip`) |
| **L** project | new service or module, several distinct parts, or an approach still unclear after define; auth/payments/migrations/public API only beyond 1–2 files | the same four, with brainstorming and design in define, top-tier checks in prove (skippable at Define's approval), and a full security pass when the change is security-touched |

Every feature ends with a small **learn** step inside ship. Deploying is a separate request: `/sdlc:deploy`.

On M and L in an interactive Claude Code session the main session stays thin: on M one kept-alive maker agent (`sonnet`) does define and build, and on L a Define agent and Build agents do define and build (and fix prove's high findings); and the main session shows you what they hand it, runs the state moves, writes prove's checker briefs and spawns the checkers on `opus`, and goes by their `VERDICT:` lines alone: the agent that wrote the code never judges (`skills/orchestrator/references/relay.md`). Define's `plan.md` starts with a `## Handoff to Build` (decisions, rejected options, facts, risks), the only thing the build agent knows of your conversation. S, autopilot and the other agents run in the session as before.

Work is sized by how many files it touches, not by risk words, and a change confined to 1–2 files is never sliced. Several distinct parts that won't fit one session get a backlog of vertical slices instead of one plan: you approve it once with the spec, then each slice is built, passes `verify.py` and is committed in turn (one prove at feature close, whatever the flow), without stopping unless a gate fails, scope would grow, or a hard stop comes up. `/sdlc:start B<n>` runs a named slice; `scripts/autopilot.py <feature>` runs the rest unattended, one fresh session per slice (pass `--permission-mode`, or allowlist the tools, since a headless session can't ask).

Each phase prints what it uses and its exit gate. Documents go to `docs/sdlc/intents/<feature>/` and state to `.sdlc/state/<feature>.md` (commit both; `docs_dir` in config moves the documents elsewhere, e.g. when `docs/` is a published site).

### 4. Decide at the gates

The orchestrator runs on its own between these stops, and always asks you here:

- **Define (M, L), one approval:** one message, in which every question that changes the build comes with a recommended answer already filled in (Define asks first only when a wrong guess would mean rewriting most of the documents). It approves the three files Define writes, which say everything the build needs: `intent.md` (why, and the approach chosen), `spec.md` (what) and `plan.md` (how: the tasks, or a backlog, and the Public Surface list of everything new others can see). It also shows the `[inferred]` list (the agent's guesses and requirements nobody asked for, each dropped unless you keep it), the design when there is one (every new module, abstraction or dependency cites a requirement), and how it will be built (`Build:`, which you can change in your reply).
- **Prove** (M full and L, unless you chose to skip it at Define's approval) needs no decision until it stalls: the checkers the track needs run in parallel on one commit, findings go back to build to be fixed test first, and the fixes are checked again, at most 3 rounds. It stops and asks you when the same requirement fails in two rounds, or when the third round fails. Only *new* failures count, not baseline ones. If code changes after the last full test run, a hook won't let the turn finish until tests are rerun.
- **Ship:** on every track it commits on a feature branch and reports `Branch <name> kept (<commit>); say "merge" or "PR" to go further.`, without asking.
- **Push, PR, merge, production deploy, DB migrations:** always yours.

### 5. Check progress, resume, pause

```
/sdlc:status          # setup state, then one line per feature: track · phase · last gate
/sdlc:start           # no argument: resume the active feature
/sdlc:prune           # clean up merged features done 45+ days ago; keeps intent, spec, design, retro, state (and review.md on high risk)
```

A new session needs no re-explaining; `state.md` carries it. To pause a feature, set `Status: paused` in its `state.md`.

### 6. After a plugin update

```
/sdlc:upgrade --dry-run    # see what would change
/sdlc:upgrade              # apply it, on its own branch
```

`/sdlc:start` and `/sdlc:status` tell you when the repo is behind. The upgrade regenerates the plugin's files, asks before touching any you edited (merge, skip, or keep yours), and applies versioned migrations one diff at a time.

### 7. When something's off, or to remove it

- `/sdlc:doctor` names the problem and the [runbook](docs/runbook.md) procedure that fixes it.
- Blocked at the end of a turn with "re-run tests": you're in Prove and code changed. Run the test command the message names.
- `/sdlc:eject` removes the plugin's files and keeps your specs, knowledge, constitution, commands and baseline. It shows a dry run first.

## Commands

| Command | Does |
|---|---|
| `/sdlc:setup [what you're building]` | Set the repo up once (new or existing code); resumes if interrupted |
| `/sdlc:start [request]` | Start a piece of work, or resume the active one with no argument |
| `/sdlc:status` | Setup state and version drift, then one line per feature. Read-only |
| `/sdlc:doctor` | Health check of machine, plugin and repo, with a fix per problem. Read-only |
| `/sdlc:upgrade [--dry-run] [--revisit]` | Bring the repo up to the installed plugin version |
| `/sdlc:eject` | Remove the plugin's files from the repo, keep your work |
| `/sdlc:review-pr` | Local pre-PR review with the right agents for the diff |
| `/sdlc:code-review` | Review a GitHub pull request (needs `gh`) |
| `/sdlc:commit`, `/sdlc:commit-push-pr`, `/sdlc:clean_gone` | Commit; commit, push and open a PR; delete local branches whose remote is gone |
| `/sdlc:hookify` | Turn a repeated correction into a rule |
| `/sdlc:revise-claude-md`, `/sdlc:knowledge-audit` | File lessons into the right knowledge tier; keep always-loaded context small |
| `/sdlc:context-diet` | Estimate what each plugin and skill adds to every call, and turn off the ones this project doesn't need, in `.claude/settings.local.json` after you approve. Works in any repo; Claude Code only |
| `/sdlc:deploy [feature] [environment]` | Deploy through the project's own deploy path, with your go-ahead before production or a migration, a smoke test and `release.md`. On request only |

With the optional `sdlc-extras` plugin: `/sdlc-extras:ralph-loop`, `/sdlc-extras:cancel-ralph`, `/sdlc-extras:ralph-help` (a self-iterating loop for one well-specified task) and `/sdlc-extras:hookify-list`, `/sdlc-extras:hookify-configure`, `/sdlc-extras:hookify-help` (list, toggle, explain rules).

Skills such as `sdlc:writing-specs` or `sdlc:test-driven-development` are used by the orchestrator in the right phase; you can also ask for one by name.

## Phases → what runs

| Phase | Replaces | Bundled pieces |
|---|---|---|
| Setup (once per repo) | | `setting-up-projects`, `/sdlc:setup`, `/sdlc:upgrade`, `/sdlc:eject`, `/sdlc:doctor` |
| Define | discover, design, plan | questions ride in the approval with recommended answers, `brainstorming` (L; asks you nothing under the orchestrator), `writing-specs`, `clarifying-specs` (on request), `designing-solutions` + `code-explorer`, `code-architect` agents (L, or an unclear approach), `analyzing-consistency` (L, backlogs) |
| Build | implement | `scripts/verify.py` (each AC's test recorded red before its code, one full run at the end, drift recorded in the plan), `using-git-worktrees`, `executing-plans` / one implementer subagent / `subagent-driven-development` (`Build:`), `dispatching-parallel-agents`, `test-driven-development`, `systematic-debugging`, `/sdlc-extras:ralph-loop` (when installed) |
| Prove | verify, review, security | M full and L with `Prove: run` (S, M lite and `Prove: skip` go from Build to Ship). First `verify.py status`: reuse Build's passing run, or rerun it once. M full: one fresh checker, a read-only `code-reviewer` that reads each acceptance criterion beside its test and reviews in one pass (correctness, silent failures, test gaps and security basics, with `diff_stats.py` facts; on `opus`, as every code review is), `ui-reviewer` on UI diffs. Security-touched (`Risk: high`, or the diff touches `areas.sensitive` or `areas.migrations`): one more `code-reviewer` with a security-only brief, and the dependency audit. One record, `review.md` (rounds, tickets, fixed, security). L: a separate `ac-checker` (reads each acceptance criterion beside its test; runs nothing) and a top-tier `code-reviewer`. A backlog's feature close (every backlog, once): the `ac-checker` over every criterion, one top-tier `code-reviewer` over the whole branch, `qa-tester`. Plans without `## Acceptance tests` (features started earlier) keep the fresh `verifier`. Commands are time-boxed (2 minutes each outside the project's own, enforced by the prove-budget hook). High findings go back to Build, fixed test first; then one re-verification (`verify.py`, and a fresh checker on the ACs that failed), max 3 rounds, and a stop when the same requirement fails twice; freshness hook. On request: `/sdlc:review-pr` (local diff), `/sdlc:code-review` (GitHub PR), `receiving-code-review` |
| Ship, with learn | PR / CI, learn | commit on a feature branch without asking on every track; `finishing-a-development-branch` when you ask for a merge or PR, `/sdlc:commit`, `/sdlc:commit-push-pr`, `/sdlc:clean_gone`; learn: fixed defects into `recurring-defects.md`, `managing-knowledge` (3-tier) and `/sdlc:hookify` only for a lesson that isn't obvious from the code or the commit, retro on L; the PR links `spec.md` and `review.md`. An advisor, where available, is called once before the commit only when no prove ran |
| `/sdlc:deploy` | deploy | on request: project's own deploy path, go-ahead, smoke test, `release.md` |

Operate (a watch window with agreed signals) is no longer part of the pipeline; its notes stay in `skills/orchestrator/references/operate.md`. Internally each phase keeps one stage number (`Current: Stage 1 – Define`, `4 – Build`, `5 – Prove`, `8 – Ship`), which the hooks read; features started under the old 11 stages carry on in the matching phase.

Always on: security-guidance hooks (during a feature, the commit's model review runs only on a security-touched change), the verify-freshness hook (in Prove, Stage 5, and it keeps its own copy of each `verify.py` run in Build and Prove, which `verify.py` itself writes after every full or `red` run, so any spelling of the command counts, and which the hook also takes from `verify.json` when its tree is the current code, also when the run is chained (`cd … && …`, `… | tail`); on the Lite flow also Stage 6, where a backlog slice rests after its commit; per package in a monorepo), the prove-budget hook (in Prove, Stage 5: every shell command other than the project's own is killed at 120 s and never runs in the background, so nothing is polled), the model-router hook (while a feature is active: every subagent dispatch names its model, never `haiku`, Fable only on your request, reviewers and the verifier on opus only on L, and each dispatch is logged), the trust-anchor hook (tells you when the risk, flow, `Prove:` choice, baseline, commands or spec change under a feature, or verify's record disagrees with the hook's copy, or it leaves Prove, or on the Lite flow stops outside Build and Prove, with untested code; a change that only adds checks, such as Lite to full, is shown without stopping you), the role-guard hook (reviewers, `sdlc-extras:` ones included, and the ac-checker can't edit files but their report under `.sdlc/.work/findings/`, the verifier writes only its report, the baseline and its probe scripts, the qa-tester can't read the code), hookify rules (personal `.claude/hookify.*.local.md`, team `.claude/hookify/*.md`), TypeScript LSP. Every hook starts through `hooks/sg-python.sh`, which skips the Microsoft Store `python3` stub.

## Knowledge: 3-tier loading

Keeps always-loaded context small while agents still find what they need:

| Tier | Where | Loads |
|---|---|---|
| 1 | `CLAUDE.md` (≤ 60 lines) | every session |
| 2 | `.claude/rules/<area>.md` with `paths:` | automatically when matching files are touched |
| 3 | `knowledge/**.md` (Open Knowledge Format) | on demand, via `knowledge/index.md` and links from tier 2 |

Retros in `docs/sdlc/intents/<feature>/retro.md` are history only. Every feature's learn step adds the defects it fixed to `recurring-defects.md` and promotes durable lessons when there are any; things corrected twice become hookify rules. Run `/sdlc:knowledge-audit` when CLAUDE.md grows.

The other part of the per-call floor is the listings of every enabled plugin, skill and command. `/sdlc:context-diet` estimates them per source and proposes turning the unrelated ones off for this project only. It also turns off the standalone `security-guidance` and `code-review`, which sdlc already bundles.

## Limitations

- **Outside services aren't bundled** (GitHub MCP, Linear, Sentry, Vercel, Playwright, …). Stages that would use them say which to add; see `skills/orchestrator/references/integrations.md`. Anthropic's `claude-security` plugin isn't bundled either (its license reserves all rights); install it separately for deep vulnerability scans.
- **Codex, Cursor and Antigravity are only partly tested.** They get the skills, the commands as skills (`start`, `setup`, `upgrade`, …; not hookify or the context diet; `sdlc-extras` is Claude Code only), the setup that detects them, and the policy rules through `AGENTS.md`. Setup has run in each, and a Claude Code join after Codex, but no one has run the phases in them yet. In Codex, Cursor and the Antigravity CLI, the freshness hook, the trust anchor and hookify run too (in Codex, once you trust them in `/hooks`). The other hooks (role, model, prove budget, security) run only in Claude Code. The subagent roles there are instructions, so those guarantees don't hold on the other agents ([spec 11](docs/specs/11-multi-agent.md)).
- **Generated CI is GitHub Actions only.** On other CI systems, run the same commands from `.sdlc/config.json` yourself.
- **Most gates are instructions plus your approval.** Machine-checked: each acceptance test recorded red before its code and plan drift (`verify.py`), test freshness and Prove's 120 s command limit (hooks), undeclared public surface (`diff_stats.py --plan`), the subagent model rules (model router) and hookify guardrails. Plan consistency on L and on backlogs is checked by a skill (`analyzing-consistency`), not mechanically. The S track has no plan and no reviewer, so drift and unrequested surface go unchecked there.
- **Freshness detection is heuristic.** It catches edits by any tool and filtered runs (file, name or package arguments), but not every possible filter, and not `.only` inside a test file (a guardrail warns on that instead).
- **Windows:** Claude Code runs commands in Git Bash, so project commands must work there; generated CI runs every step with `shell: bash`.

## Contributing

Repo layout, dev loop, tests, releases and vendored code: see [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits and license

MIT, © 2026 Tâm Mai, see [LICENSE](LICENSE).

sdlc bundles and adapts work from [Superpowers](https://github.com/obra/superpowers) (MIT, Jesse Vincent), [GitHub Spec Kit](https://github.com/github/spec-kit) (MIT, GitHub) and [Anthropic's Claude Code plugins](https://github.com/anthropics/claude-plugins-official) (Apache-2.0, Anthropic). What came from where, and what was changed, is in [NOTICE.md](NOTICE.md); license texts are in `licenses/`.
