# sdlc

One Claude Code plugin for the whole software lifecycle. An orchestrator walks each piece of work through up to 11 gated stages, from spec to shipped and learned-from, and calls the bundled skills, agents, commands and hooks at each one. No other plugin is required.

Docs: [guidebook](docs/guidebook.md) (how it works) · [playbook](docs/playbook.md) (what to do when…) · [runbook](docs/runbook.md) (install, health, fixes) · [changelog](CHANGELOG.md)

**Contents:** [What you get](#what-you-get) · [Install](#install) · [Use](#use) · [Commands](#commands) · [Stages](#stages--what-runs) · [Knowledge](#knowledge-3-tier-loading) · [Limitations](#limitations) · [Contributing](#contributing) · [Credits and license](#credits-and-license)

## What you get

- **Sized process, not ceremony.** Work is sized S (fix), M (feature) or L (project), and only the stages that size needs run. The smallest track that fits is the default.
- **Gates you can trust.** Each stage has an exit criterion. You decide at the hard stops (spec, design, execution method, merge, deploy, migrations); everything else runs on its own.
- **Independent verification.** A fresh verifier agent each round, a hook that won't let a turn finish on stale test results, and a baseline so old failures don't block new work.
- **Scope kept in check.** Requirements are traced from spec to diff: inferred requirements are dropped unless you keep them, every new abstraction or dependency cites a requirement, and undeclared public surface is flagged in review.
- **Conventions enforced where they happen.** Policy rules load while code is written, guardrails warn or block in real time (narrating comments, focused tests, secrets, force-push to main), and review gets measured facts from `diff_stats.py`.
- **UI that follows your design system.** UI work reads the project's design system, a guardrail warns on hard-coded colors and inline styles, and a UI reviewer flags off-system components and generic "AI look" styling before merge.
- **Knowledge that stays small.** Three loading tiers keep `CLAUDE.md` short; lessons are promoted from retros, and corrections that repeat become rules.
- **Any stack, any repo shape.** Setup records the commands your repo already uses, per package in a monorepo (TS, Go, Rust, Dart, Python, shell, …), and generates CI from them. A new multi-app repo becomes an `apps/` + `packages/` monorepo with a versioned API contract. Upgrades are versioned and never overwrite your edits.

## Install

From the marketplace that hosts it:

```
/plugin marketplace add tammai/sdlc
/plugin install sdlc@sdlc
```

Restart the session afterward so the commands and hooks load. To work on the plugin from a checkout instead, see [Contributing](#contributing).

**Other coding agents** (setup detects the agent and writes its own files; [spec 11](docs/specs/11-multi-agent.md)). Setup is smoke-tested in Codex and Antigravity on Windows and in Cursor in WSL:

| Agent | Install |
|---|---|
| Codex | `codex plugin marketplace add tammai/sdlc`, then `codex plugin add sdlc@sdlc` |
| Cursor | Customize → Import from Repo with `https://github.com/tammai/sdlc`, or a clone in `~/.cursor/plugins/local` |
| Antigravity | `python3 scripts/hosts.py dist antigravity <folder>` in a clone, then `agy plugin install <folder>` (a direct `agy plugin install https://github.com/tammai/sdlc` loads only 3 of the 13 agents) |

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
- Ends by asking: open a PR, or merge locally.

What lands in the repo: `.sdlc/config.json` (your commands; to change one later, see [Configuration](docs/guidebook.md#configuration)), `docs/sdlc/constitution.md`, `docs/sdlc/design-system.md` (UI projects), `.claude/rules/sdlc-*.md`, `.claude/hookify/sdlc-*.md`, `.claude/settings.json` (command allowlist; with your approval, the sdlc marketplace and `enabledPlugins` so teammates are offered the plugin), `.github/workflows/sdlc-verify.yml` and `sdlc-invariants.yml` (checks the shared sdlc files, whichever agent changed them), `knowledge/`, and for existing code `.sdlc/baseline.md`. Your `CLAUDE.md` is never touched.

### 3. Start a piece of work

```
/sdlc:start fix: export button 500s when the report is empty
/sdlc:start add CSV export to the reports page
```

The orchestrator sizes it and proposes the smallest track that fits; you can override.

| Track | When | Stages |
|---|---|---|
| **S** fix | bug or tweak, 1–3 files | implement → verify → light review → PR |
| **M** feature | a few files to a few days | low risk: the Lite flow, spec-and-tasks (one approval) → implement → verify → review → light security → one commit. High risk or on request: spec → plan → implement → verify → review → light security → PR (+ design if the approach isn't obvious) |
| **L** project | new service, unclear approach, or auth/payments/migrations/public API | stages 1–8 and 11, including design and learn; deploy on request |

Work bigger than one session gets a backlog of vertical slices instead of one plan: you approve it once with the spec, then each slice is planned, built, verified, reviewed and committed in turn, without stopping unless a gate fails, scope would grow, or a hard stop comes up. `/sdlc:start B<n>` runs a named slice; `scripts/autopilot.py <feature>` runs the rest unattended, one fresh session per slice (pass `--permission-mode`, or allowlist the tools, since a headless session can't ask).

Each stage prints what it uses and its exit gate. Documents go to `docs/sdlc/intents/<feature>/` and state to `.sdlc/state/<feature>.md` (commit both; `docs_dir` in config moves the documents elsewhere, e.g. when `docs/` is a published site).

### 4. Decide at the gates

The orchestrator runs on its own between these stops, and always asks you here:

- **Spec (M, L):** any questions that block the work come first, all in one message (often none). Then read the `[inferred]` list: the agent's guesses and requirements nobody asked for. Each is dropped unless you keep it. Approve the spec.
- **Design (L, or M when unclear):** every new module, abstraction or dependency must cite a requirement in the Complexity Tracking table. Approve the design.
- **Plan:** check the Public Surface list (everything new others can see), then pick subagent-driven or native execution. The Lite flow has no separate plan: you approve the spec and its task list together, and it builds in the session.
- **Verify** needs no decision: a fresh `verifier` agent runs your commands each round, at most 3. Only *new* failures count, not baseline ones. If code changes after the last full test run, a hook won't let the turn finish until tests are rerun.
- **Merge, production deploy, DB migrations:** always yours.

### 5. Check progress, resume, pause

```
/sdlc:status          # setup state, then one line per feature: track · stage · last gate
/sdlc:start           # no argument: resume the active feature
/sdlc:prune           # clean up merged features done 45+ days ago; keeps spec, design, retro, state
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
- Blocked at the end of a turn with "re-run tests": you're in Verify and code changed. Run the test command the message names.
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
| `/sdlc:hookify`, `/sdlc:hookify-list`, `/sdlc:hookify-configure`, `/sdlc:hookify-help` | Turn a repeated correction into a rule; list, toggle, explain rules |
| `/sdlc:revise-claude-md`, `/sdlc:knowledge-audit` | File lessons into the right knowledge tier; keep always-loaded context small |
| `/sdlc:ralph-loop`, `/sdlc:cancel-ralph`, `/sdlc:ralph-help` | Optional self-iterating loop for one well-specified task |

Skills such as `sdlc:writing-specs` or `sdlc:test-driven-development` are used by the orchestrator at the right stage; you can also ask for one by name.

## Stages → what runs

| # | Stage | Bundled pieces |
|---|---|---|
| 0 | Setup (once per repo) | `setting-up-projects`, `/sdlc:setup`, `/sdlc:upgrade`, `/sdlc:eject`, `/sdlc:doctor` |
| 1 | Discover | blocking questions in one message (or none), `brainstorming`, `writing-specs`, `clarifying-specs` (on request) |
| 2 | Design | `designing-solutions` + `code-explorer`, `code-architect` agents |
| 3 | Plan | `writing-plans`, `analyzing-consistency` |
| 4 | Implement | `using-git-worktrees`, `subagent-driven-development` / `executing-plans`, `dispatching-parallel-agents`, `test-driven-development`, `systematic-debugging`, `/sdlc:ralph-loop` |
| 5 | Verify | fresh `verifier` agent each round (max 3) with a red-green check, `pr-test-analyzer`, `silent-failure-hunter`, freshness hook; `qa-tester` on request |
| 6 | Review | `/sdlc:review-pr`, `/sdlc:code-review`, `requesting-code-review`, `receiving-code-review`, `code-reviewer`, `feature-reviewer`, `comment-analyzer`, `type-design-analyzer`, `code-simplifier`, `ui-reviewer` (UI diffs), `diff_stats.py` |
| 7 | Security | security-guidance hooks (always on), reviewer agents with a security brief, dependency audit |
| 8 | PR / CI | `finishing-a-development-branch`, `/sdlc:commit`, `/sdlc:commit-push-pr`, `/sdlc:clean_gone` |
| 9 | Deploy | on request: project's own deploy path + `release.md` |
| 10 | Operate | parked, no track runs it: watch window with agreed signals |
| 11 | Learn | `managing-knowledge` (3-tier), `/sdlc:revise-claude-md`, `/sdlc:knowledge-audit`, `/sdlc:hookify`, `project-constitution` |

Always on: security-guidance hooks, the verify-freshness hook (Stage 5 only, or Stages 5–6 on the Lite flow; per package in a monorepo), the model-router hook (while a feature is active: every subagent dispatch names its model, Fable only on your request, and each dispatch is logged), the trust-anchor hook (tells you when the risk, flow, baseline, commands or spec change under a feature, or it leaves Stage 5, or on the Lite flow stops outside Stages 4–6, with untested code), the role-guard hook (reviewers can't edit files, the verifier writes only its report and the baseline, the qa-tester can't read the code), hookify rules (personal `.claude/hookify.*.local.md`, team `.claude/hookify/*.md`), TypeScript LSP.

## Knowledge: 3-tier loading

Keeps always-loaded context small while agents still find what they need:

| Tier | Where | Loads |
|---|---|---|
| 1 | `CLAUDE.md` (≤ 60 lines) | every session |
| 2 | `.claude/rules/<area>.md` with `paths:` | automatically when matching files are touched |
| 3 | `knowledge/**.md` (Open Knowledge Format) | on demand, via `knowledge/index.md` and links from tier 2 |

Retros in `docs/sdlc/intents/<feature>/retro.md` are history only. Durable lessons are promoted in Stage 11; things corrected twice become hookify rules. Run `/sdlc:knowledge-audit` when CLAUDE.md grows.

## Limitations

- **Outside services aren't bundled** (GitHub MCP, Linear, Sentry, Vercel, Playwright, …). Stages that would use them say which to add; see `skills/orchestrator/references/integrations.md`. Anthropic's `claude-security` plugin isn't bundled either (its license reserves all rights); install it separately for deep vulnerability scans.
- **Codex, Cursor and Antigravity are only partly tested.** They get the skills, the commands as skills (`start`, `setup`, `upgrade`, …; not the Ralph loop or hookify), the setup that detects them, and the policy rules through `AGENTS.md`. Setup has run in each, and a Claude Code join after Codex, but no one has run the stages in them yet. In Codex, Cursor and the Antigravity CLI, the freshness hook, the trust anchor and hookify run too (in Codex, once you trust them in `/hooks`). The other hooks (role, model, security) run only in Claude Code. The subagent roles there are instructions, so those guarantees don't hold on the other agents ([spec 11](docs/specs/11-multi-agent.md)).
- **Generated CI is GitHub Actions only.** On other CI systems, run the same commands from `.sdlc/config.json` yourself.
- **Most gates are instructions plus your approval.** Machine-checked: test freshness (hook), undeclared public surface (`diff_stats.py --plan`), the subagent model floor (model router) and hookify guardrails. Plan consistency on L and larger M plans is checked by a skill (`analyzing-consistency`), not mechanically. The S track has no plan, so unrequested surface there is the reviewer's call.
- **Freshness detection is heuristic.** It catches edits by any tool and filtered runs (file, name or package arguments), but not every possible filter, and not `.only` inside a test file (a guardrail warns on that instead).
- **Windows:** Claude Code runs commands in Git Bash, so project commands must work there; generated CI runs every step with `shell: bash`.

## Contributing

Repo layout, dev loop, tests, releases and vendored code: see [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits and license

MIT, © 2026 Tâm Mai, see [LICENSE](LICENSE).

sdlc bundles and adapts work from [Superpowers](https://github.com/obra/superpowers) (MIT, Jesse Vincent), [GitHub Spec Kit](https://github.com/github/spec-kit) (MIT, GitHub) and [Anthropic's Claude Code plugins](https://github.com/anthropics/claude-plugins-official) (Apache-2.0, Anthropic). What came from where, and what was changed, is in [NOTICE.md](NOTICE.md); license texts are in `licenses/`.
