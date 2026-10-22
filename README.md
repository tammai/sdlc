# sdlc

One Claude Code plugin for the whole software lifecycle. An orchestrator walks a feature through 11 gated stages and calls the bundled skills, agents, commands and hooks at each one. No other plugin is required.

## Install

From the marketplace that hosts it:

```
/plugin marketplace add tammai/sdlc
/plugin install sdlc@sdlc
```

Restart the session afterward so the commands and hooks load. To work on the plugin from a checkout instead, see the [runbook](docs/runbook.md#develop-locally).

**Requirements:** `git`, `gh` (for `/sdlc:code-review` and PR commands), Python 3 (hooks), Node (brainstorm visual companion), and for TypeScript code intelligence: `npm i -g typescript-language-server typescript`. The security hooks set up their own Python environment on first session start (can take a minute).

## Use

```
/sdlc:setup                                   # once per repo (new or existing)
/sdlc:start add CSV export to the reports page
/sdlc:status
/sdlc:upgrade                                 # after a plugin update
```

Setup gives the repo a `justfile` command contract (`install test lint typecheck build verify`), policy rules, guardrails, CI and, for existing code, a baseline of what already fails. Needs [`just`](https://just.systems) (≥ 1.31 for monorepos).

The orchestrator sizes the work (S fix / M feature / L project), picks the stages, and stops for your approval at: spec, design, execution method, merge, production deploy, DB migrations.

Artifacts live in `.sdlc/<feature>/` (commit them). Scratch files go to `.sdlc/.work/` (git-ignored). Project principles: `.sdlc/constitution.md`.

## Stages → what runs

| # | Stage | Bundled pieces |
|---|---|---|
| 1 | Discover | `brainstorming`, `writing-specs`, `clarifying-specs` |
| 2 | Design | `designing-solutions` + `code-explorer`, `code-architect` agents |
| 3 | Plan | `writing-plans`, `analyzing-consistency` |
| 4 | Implement | `using-git-worktrees`, `subagent-driven-development` / `executing-plans`, `dispatching-parallel-agents`, `test-driven-development`, `systematic-debugging`, `/sdlc:ralph-loop` |
| 5 | Verify | fresh `verifier` agent each round (max 3), `pr-test-analyzer`, `silent-failure-hunter`, freshness hook |
| 6 | Review | `/sdlc:review-pr`, `/sdlc:code-review`, `requesting-code-review`, `receiving-code-review`, `code-reviewer`, `feature-reviewer`, `comment-analyzer`, `type-design-analyzer`, `code-simplifier` |
| 7 | Security | security-guidance hooks (always on), reviewer agents with a security brief, dependency audit |
| 8 | PR / CI | `finishing-a-development-branch`, `/sdlc:commit`, `/sdlc:commit-push-pr`, `/sdlc:clean_gone` |
| 9 | Deploy | project's own deploy path + `release.md` |
| 10 | Operate | watch window with agreed signals |
| 11 | Learn | `managing-knowledge` (3-tier), `/sdlc:revise-claude-md`, `/sdlc:knowledge-audit`, `/sdlc:hookify`, `project-constitution` |

Always-on: security-guidance hooks, verify-freshness hook (Stage 5 only — blocks finishing when code changed after the last full test run), hookify rules (personal `.claude/hookify.*.local.md`, team `.claude/hookify/*.md`), TypeScript LSP.

## Knowledge: 3-tier loading

Keeps always-loaded context small while agents still find what they need:

| Tier | Where | Loads |
|---|---|---|
| 1 | `CLAUDE.md` (≤ 60 lines) | every session |
| 2 | `.claude/rules/<area>.md` with `paths:` | automatically when matching files are touched |
| 3 | `knowledge/**.md` (Open Knowledge Format) | on demand, via `knowledge/index.md` and links from tier 2 |

Retros in `.sdlc/<feature>/retro.md` are history only. Durable lessons are promoted in Stage 11; things corrected twice become hookify rules. Run `/sdlc:knowledge-audit` when CLAUDE.md grows.

Outside services (GitHub MCP, Linear, Sentry, Vercel, Playwright…) can't be bundled; see `skills/orchestrator/references/integrations.md`.

## Updating vendored code

Sources and licenses are listed in `NOTICE.md`. To pull upstream fixes, re-copy the listed files and re-apply the renames described there (`superpowers:` → `sdlc:`, paths → `.sdlc/`).

## Tests

The hooks have a stdlib-only test suite (no pytest needed). Each test runs a hook as a subprocess against a throwaway project directory:

```sh
python3 -m unittest discover -s tests -t tests
```

Run it after updating vendored code. `claude plugin test` doesn't apply here: it only runs TypeScript hook modules.
