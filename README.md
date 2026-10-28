# sdlc

One Claude Code plugin for the whole software lifecycle. An orchestrator walks each piece of work through four phases (Define, Build, Review, Ship), from intent to an open PR, and calls the bundled skills, agents, commands and hooks at each one. No other plugin is required.

Docs: [guidebook](docs/guidebook.md) (how it works) · [playbook](docs/playbook.md) (what to do when…) · [runbook](docs/runbook.md) (install, health, fixes) · [changelog](CHANGELOG.md)

**Contents:** [What you get](#what-you-get) · [Install](#install) · [Use](#use) · [Commands](#commands) · [Phases](#phases--what-runs) · [Knowledge](#knowledge-3-tier-loading) · [Limitations](#limitations) · [Contributing](#contributing) · [Credits and license](#credits-and-license)

## What you get

- **A record of every change.** S, M or L, every change leaves the same two files, committed with the code and kept for good: `change.md` for people (why, what must be true with each criterion's test, and what was checked after the build) and the feature's state file for the agent (where it stands and how it's built: tasks, files, Public Surface, deviations). Each commit names the record, so `git blame` leads from a line to its why.
- **Intent before code.** Nothing is built until what, why and how are written down. The agent asks only when something is unclear, one question at a time. A bug is proven first (a failing test or exact steps), then its root cause is found.
- **Gates you can trust.** You decide at the hard stops (on M and L, approving `change.md` and the plan, then choosing the reviews; anything that adds scope; merge; deploy; migrations). S runs straight through.
- **Test-first, checked by a script.** Build proves its own work with one command, `verify.py`: every acceptance criterion's test recorded failing before its code and passing after it, plus the full checks and plan drift. A hook won't let Review finish on stale test results, and a baseline keeps old failures from blocking new work.
- **Reviews that fit the change.** After the build the agent recommends reviews from what the diff touched: security, code (low, default or high depth), UI, an advisor where there is one, or none. Each runs once, fresh, on `opus`.
- **Scope kept in check.** Proposals nobody asked for are dropped unless you keep them, and public surface missing from the plan is flagged in review.
- **Conventions enforced where they happen.** Policy rules load while code is written, guardrails warn or block in real time (narrating comments, focused tests, secrets, force-push to main), and review gets measured facts from `diff_stats.py`.
- **UI that follows your design system.** UI work reads the project's design system, a guardrail warns on hard-coded colors and inline styles, and a UI reviewer flags off-system components and generic "AI look" styling before merge.
- **Knowledge that stays small.** Three loading tiers keep `CLAUDE.md` short; before its final commit, every feature adds the defects it fixed to a list every later reviewer checks, and corrections that repeat become rules.
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

**Upgrading from 1.x to 2.0:** finish every feature in progress on sdlc 1.8.1 first, or archive it (`Status: done` in its state file). 2.0 won't run a 1.x feature, and `/sdlc:upgrade` refuses while one is active. Why 2.0 changed the flow: [ADR 0020](docs/adr/0020-sdlc-2-slim-process-core.md).

**Uninstall:** run `/sdlc:eject` in each repo first (it removes the plugin's files and keeps your work), then `/plugin uninstall sdlc`.

**Requirements:** `git`, `gh` (for `/sdlc:code-review` and PR commands), Python 3.9+ (hooks and scripts, stdlib only), Node (brainstorm visual companion), and for TypeScript code intelligence: `npm i -g typescript-language-server typescript`. The security hooks build their own Python environment in the background the first time a security-touched feature needs a model review. Your project needs nothing extra: sdlc runs the commands it already uses.

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
| **S** fix | a fix or tweak, 1–2 files, clear expected behaviour | define (`change.md` and the plan, a few lines each; no stop) → build → review (a fixed trigger list, none by default) → ship |
| **M** feature | a few files to a few days, approach mostly clear | define (`change.md` and the plan in full; you read and approve `change.md`) → build → review (you pick from the recommendation) → ship |
| **L** project | several distinct parts, or an approach still unclear | the same four, with the brainstorming interview in define |

Every track has the same four phases and the same record; the track sets only the record's depth and whether there's a stop before the build and before the reviews. **Learn** happens inside ship, before the final commit. Deploying is a separate request: `/sdlc:deploy`.

Define asks only when what, why or how isn't clear, one question at a time. A bug is proven first: a failing test (it becomes the fix's first acceptance test) or exact steps, then the root cause. The build runs like plain Claude, in this session by default; Define may instead choose parts in fresh sessions (work too big for one context) or parallel subagents (truly independent parts), and says why in the state file.

Work is sized by how many files it touches, not by risk words, and a change confined to 1–2 files is never split. Several distinct parts that won't fit one session get a backlog of parts: you approve it once with the other files, then each part is built, passes `verify.py` and is committed in turn, and all of them land together (one review and one ship, after the last part). `/sdlc:start B<n>` runs a named part; `scripts/autopilot.py <feature>` runs the rest unattended, one fresh session per part (pass `--permission-mode`, or allowlist the tools, since a headless session can't ask).

Each phase prints what it uses and its exit gate. Documents go to `docs/sdlc/intents/<feature>/` and state to `.sdlc/state/<feature>.md` (commit both; `docs_dir` in config moves the documents elsewhere, e.g. when `docs/` is a published site).

### 4. Decide at the gates

The orchestrator runs on its own between these stops, and always asks you here:

- **Define (M, L), one approval:** one message with the path to `change.md` (why, the decisions and what was ruled out; the acceptance criteria, each with its test; must-never-break lines; out of scope), a table of the decisions with how the build runs (the tasks and the Public Surface list of everything new others can see are in the state file), plus any proposals nobody asked for, each dropped unless you keep it. You read the files and approve, or change anything.
- **Review (M, L):** after the build the agent recommends reviews, each with a reason from what the diff touched; you pick. A high finding goes back to build, fixed with a failing test first; a disagreement over one comes to you. If code changes after the last full test run, a hook won't let the turn finish until tests are rerun.
- **CI still red after one fix:** the agent tells you what failed. A CI-only problem (a secret, a runner, a flaky test) is never worked around in code.
- **Merge, production deploy, DB migrations:** always yours. Ship commits, pushes, opens the PR, watches CI and stops: `PR <url> open, local and CI green; say "merge" to merge.` Without a remote it stops with the branch ready.

### 5. Check progress, resume, pause

```
/sdlc:status          # setup state, then one line per feature: track · phase · last gate
/sdlc:start           # no argument: resume the active feature
/sdlc:prune           # clean up merged features done 45+ days ago; keeps change.md and state, drops the parts' plans and reports
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
- Blocked at the end of a turn with "re-run tests": you're in Review and code changed. Run the test command the message names.
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

Skills such as `sdlc:brainstorming` or `sdlc:test-driven-development` are used by the orchestrator in the right phase; you can also ask for one by name.

## Phases → what runs

| Phase | Replaces | Bundled pieces |
|---|---|---|
| Setup (once per repo) | | `setting-up-projects`, `/sdlc:setup`, `/sdlc:upgrade`, `/sdlc:eject`, `/sdlc:doctor` |
| Define | discover, specify, plan | `brainstorming` (the interview on L), `systematic-debugging` (a bug's proof and root cause), `knowledge/index.md` and `recurring-defects.md`, the `change.md` template and the state file's plan sections, `ui-work.md` on UI work, a backlog of parts when the work won't fit one session |
| Build | implement | `scripts/verify.py` (each AC's test recorded red before its code, one full run at the end, drift recorded in the state file), `test-driven-development`, `systematic-debugging`; parts in fresh sessions (`/sdlc:start B<n>`, `autopilot.py`) or the `dispatching-parallel-agents.md` reference when Define chose them; the `using-git-worktrees.md` reference; `/sdlc-extras:ralph-loop` (when installed) |
| Review | verify, review, security | the agent recommends from `diff_stats.py` facts and the spec; each chosen review runs once, fresh, on `opus`: `code-reviewer` at low, default or high depth; `code-reviewer` with the security brief plus the dependency audit; `ui-reviewer` (always recommended when the diff touches `areas.ui`); the advisor where the agent has one. S runs a fixed trigger list, none by default; M and L ask; autopilot takes it. High findings go back to Build, fixed test first; the review isn't rerun. One record, `change.md`'s `## Review`. Freshness and prove-budget hooks. On request: `qa-tester` (runs the feature as a user would), `/sdlc:review-pr` (local diff), `/sdlc:code-review` (GitHub PR), `receiving-code-review` |
| Ship, with learn | PR / CI, learn | learn first: `managing-knowledge` (3-tier) and `/sdlc:hookify` only for a lesson that isn't obvious from the code, fixed defects into `recurring-defects.md`; then `verify.py` green on that code, and one call that commits (naming the record), pushes and opens the PR with git and `gh` (the PR links `change.md`), CI watched with one fix, stop at the PR; `finishing-a-development-branch.md` when you say merge, `/sdlc:clean_gone` |
| `/sdlc:deploy` | deploy | on request: project's own deploy path, go-ahead, smoke test, `release.md` |

Operate (a watch window with agreed signals) is no longer part of the pipeline; its notes stay in `skills/orchestrator/references/operate.md`. Internally each phase keeps one stage number (`Current: Stage 1 – Define`, `4 – Build`, `5 – Review`, `8 – Ship`), which the hooks read. A 2.0 feature's state file says `Process: 2`; the hooks act only on those.

Always on: security-guidance hooks (pattern warnings on every edit; the turn-end and commit model reviews run only while a security-touched feature is active, ADR 0019), the verify-freshness hook (in Review, Stage 5, and it keeps its own copy of each `verify.py` run in Build and Review, which `verify.py` itself writes after every full or `red` run, so any spelling of the command counts, and which the hook also takes from `verify.json` when its tree is the current code, also when the run is chained (`cd … && …`, `… | tail`); per package in a monorepo), the prove-budget hook (in Review, Stage 5: every shell command other than the project's own is killed at 120 s and never runs in the background, so nothing is polled), the model-router hook (while a feature is active: every subagent dispatch names its model, never `haiku`, Fable only on your request, every review on opus at every size, and each dispatch is logged), the trust-anchor hook (tells you when the track, risk, top model, base, `Process:`, baseline, commands or `change.md`'s criteria and tests change under a feature, or verify's record disagrees with the hook's copy, or it leaves Review with untested code or a review's `VERDICT: FAIL` you didn't waive; a change that only adds checks, such as risk low to high, is shown without stopping you), the role-guard hook (reviewers, `sdlc-extras:` ones included, can't edit files but their report under `.sdlc/.work/findings/`, the qa-tester can't read the code), hookify rules (personal `.claude/hookify.*.local.md`, team `.claude/hookify/*.md`), TypeScript LSP. Every hook starts the Python that `hooks/sg-python.sh` found and remembered, or the launcher itself when none is remembered; it skips the Microsoft Store `python3` stub.

## Knowledge: 3-tier loading

Keeps always-loaded context small while agents still find what they need:

| Tier | Where | Loads |
|---|---|---|
| 1 | `CLAUDE.md` (≤ 60 lines) | every session |
| 2 | `.claude/rules/<area>.md` with `paths:` | automatically when matching files are touched |
| 3 | `knowledge/**.md` (Open Knowledge Format) | on demand, via `knowledge/index.md` and links from tier 2 |

Every feature's learn step, before its final commit, adds the defects it fixed to `recurring-defects.md` and files durable lessons when there are any (linked from its `change.md`'s `## Review`), so they ship in the same PR; things corrected twice become hookify rules. Run `/sdlc:knowledge-audit` when CLAUDE.md grows.

The other part of the per-call floor is the listings of every enabled plugin, skill and command. `/sdlc:context-diet` estimates them per source and proposes turning the unrelated ones off for this project only. It also turns off the standalone `security-guidance` and `code-review`, which sdlc already bundles.

## Limitations

- **Outside services aren't bundled** (GitHub MCP, Linear, Sentry, Vercel, Playwright, …). Stages that would use them say which to add; see `skills/orchestrator/references/integrations.md`. Anthropic's `claude-security` plugin isn't bundled either (its license reserves all rights); install it separately for deep vulnerability scans.
- **Codex, Cursor and Antigravity are only partly tested.** They get the skills, the commands as skills (`start`, `setup`, `upgrade`, …; not hookify or the context diet; `sdlc-extras` is Claude Code only), the setup that detects them, and the policy rules through `AGENTS.md`. Setup has run in each, and a Claude Code join after Codex, but no one has run the phases in them yet. In Codex, Cursor and the Antigravity CLI, the freshness hook, the trust anchor and hookify run too (in Codex, once you trust them in `/hooks`). The other hooks (role, model, prove-budget, security) run only in Claude Code. The subagent roles there are instructions, so those guarantees don't hold on the other agents ([spec 11](docs/specs/11-multi-agent.md)).
- **Generated CI is GitHub Actions only.** On other CI systems, run the same commands from `.sdlc/config.json` yourself.
- **Most gates are instructions plus your approval.** Machine-checked: each acceptance test recorded red before its code and plan drift (`verify.py`), test freshness and Review's 120 s command limit (hooks), undeclared public surface (`diff_stats.py --plan`), the subagent model rules (model router), leaving Review only on a passing full run with no unwaived `VERDICT: FAIL` (trust anchor) and hookify guardrails. Which reviews run is the agent's judgment (yours on M and L); an S change whose recommendation is none gets no reviewer.
- **Freshness detection is heuristic.** It catches edits by any tool and filtered runs (file, name or package arguments), but not every possible filter, and not `.only` inside a test file (a guardrail warns on that instead).
- **Windows:** Claude Code runs commands in Git Bash, so project commands must work there; generated CI runs every step with `shell: bash`.

## Contributing

Repo layout, dev loop, tests, releases and vendored code: see [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits and license

MIT, © 2026 Tâm Mai, see [LICENSE](LICENSE).

sdlc bundles and adapts work from [Superpowers](https://github.com/obra/superpowers) (MIT, Jesse Vincent), [GitHub Spec Kit](https://github.com/github/spec-kit) (MIT, GitHub) and [Anthropic's Claude Code plugins](https://github.com/anthropics/claude-plugins-official) (Apache-2.0, Anthropic). What came from where, and what was changed, is in [NOTICE.md](NOTICE.md); license texts are in `licenses/`.
