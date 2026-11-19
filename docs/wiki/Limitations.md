# Limitations

- **Outside services aren't bundled** (GitHub MCP, Linear, Sentry, Vercel, Playwright, …). Stages that would use them say which to add; see `skills/orchestrator/references/integrations.md`. Anthropic's `claude-security` plugin isn't bundled either (its license reserves all rights); install it separately for deep vulnerability scans.
- **Codex, Cursor and Antigravity are only partly tested.** They get the skills, the commands as skills (`start`, `setup`, `upgrade`, …; not hookify or the context diet; `sdlc-extras` is Claude Code only), the setup that detects them, and the policy rules through `AGENTS.md`. Setup has run in each, and a Claude Code join after Codex, but no one has run the phases in them yet. In Codex, Cursor and the Antigravity CLI, the freshness hook, the trust anchor and hookify run too (in Codex, once you trust them in `/hooks`). The other hooks (role, model, prove-budget, security) run only in Claude Code. The subagent roles there are instructions, so those guarantees don't hold on the other agents ([spec 11](../specs/11-multi-agent.md)).
- **Generated CI is GitHub Actions only.** On other CI systems, run the same commands from `.sdlc/config.json` yourself.
- **Most gates are instructions plus your approval.** Machine-checked: each acceptance test recorded red before its code and plan drift (`verify.py`), test freshness and Review's 120 s command limit (hooks), undeclared public surface (`diff_stats.py --plan`), the subagent model rules (model router), leaving Review only on a passing full run with no unwaived `VERDICT: FAIL` (trust anchor) and hookify guardrails. Which reviews run is the agent's judgment (yours on M and L); an S change whose recommendation is none gets no reviewer.
- **Freshness detection is heuristic.** It catches edits by any tool and filtered runs (file, name or package arguments), but not every possible filter, and not `.only` inside a test file (a guardrail warns on that instead).
- **Windows:** Claude Code runs commands in Git Bash, so project commands must work there; generated CI runs every step with `shell: bash`.

## Tested versions

The versions each agent was checked on, from the release notes' smoke-test lines. Newer versions haven't been checked.

| Agent | Checked on | What ran | Release notes |
|---|---|---|---|
| Claude Code | 2.1.318 to 2.1.322 | the full smoke test (A–H); later releases ran only the parts they changed | 3.2.0, 3.2.1, 3.6.0 |
| Codex | 0.154.0 | setup and a Claude Code join (smoke test J) | 3.2.0, 3.2.1 |
| Antigravity CLI | 1.0.16 and 1.5.1 | setup and a Claude Code join (smoke test J) | 3.2.0, 3.2.1 |
| Cursor | not yet recorded | installs with its hooks registered (1.8.1); the smoke test hasn't run | 1.8.1 |
| Windows (any agent) | not yet recorded | smoke test I hasn't run | 3.2.0, 3.2.1 |

Codex releases before 0.141.0 install the plugin but run no plugin hooks, as reported by another plugin's tests (microsoft/TokenEconomizer).
