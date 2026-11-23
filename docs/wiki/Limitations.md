# Limitations

## What is machine-checked, and what isn't

Most gates are instructions plus your approval. These are enforced by code:

| Checked by machine | By |
|---|---|
| Each acceptance test recorded failing before its code; plan drift | `verify.py` |
| Test freshness in Review; Review's 120 s command limit | Hooks |
| Undeclared public surface | `diff_stats.py --plan` |
| Subagent model rules | Model router |
| Leaving Review only on a passing full run with no unwaived `VERDICT: FAIL` | Trust anchor |
| Your guardrails | hookify |

**Not** machine-checked: which reviews run is the agent's judgment (yours where you pick). An S change whose recommendation is none gets no reviewer.

## Known gaps

- **Freshness detection is heuristic.** It catches edits by any tool and filtered runs (file, name or package arguments), but not every possible filter, and not `.only` inside a test file (a guardrail warns on that instead).
- **A workbench's read-only guard stops mistakes, not a determined agent.** The guard reads command text, and the read-only watch behind it keeps its baseline and marker outside the agent's view only by name: an agent set on it can spell around the text check, remove or rewrite those files, feed the watch a fake event, or forge `refs/remotes` so a local commit looks pushed. The same goes for the guard's reading of a shell command: it denies the syntax it knows it reads differently from the shell, but a determined spelling (ANSI-C quoting as an argument, a substitution split by quotes, an array subscript evaluated as arithmetic) can still get a write past it; the watch reports what changed afterwards. Likewise, in a workbench a done feature keeps the commit review on its app repos until its branch shows as merged in the remote's default branch, which the agent could fake by rewriting local refs (`git branch -f`, `update-ref`) or, for a deleted branch, HEAD's reflog (`git checkout -B <branch> origin/main`, back, then delete it); the push review still covers those commits. Treat it as a seatbelt; keep another team's repos protected on their remote (branch protection, no push rights).
- **Modes and skips are protected by notice, not by lock.** A move to advisory or a newly skipped step counts only after the trust anchor showed it and you replied, or once it is committed in any checkout with no local record (a fresh clone, a new worktree); an agent that commits the change and removes the record (`.sdlc/.work/trust-anchor.json`) still gets it honoured, visibly in git history, and one that writes an accepted entry straight into that record gets it honoured with nothing in git ([ADR 0030](../adr/0030-modes-and-skips.md)).
- **Generated CI is GitHub Actions only.** On other CI systems, run the commands from `.sdlc/config.json` yourself.
- **Windows:** Claude Code runs commands in Git Bash, so project commands must work there. Generated CI runs every step with `shell: bash`.
- **Outside services aren't bundled** (GitHub MCP, Linear, Sentry, Vercel, Playwright, …). Phases that would use one say which to add (`skills/orchestrator/references/integrations.md`). Anthropic's `claude-security` plugin isn't bundled (its license reserves all rights); install it separately for deep scans.

## Other coding agents

Codex, Cursor and Antigravity are **only partly tested**: setup has run in each, plus a Claude Code join after Codex, but nobody has run the phases there yet.

| | Claude Code | Codex · Cursor · Antigravity |
|---|---|---|
| Skills, commands as skills (`start`, `setup`, `upgrade`, …) | ✅ | ✅ (not hookify or the context diet) |
| Policy rules | ✅ | ✅ via `AGENTS.md` |
| Freshness, trust anchor, hookify hooks | ✅ | ✅ (Codex: after you trust them in `/hooks`) |
| Role, model, prove-budget, security hooks | ✅ | ❌ |
| Subagent role guarantees | ✅ enforced | Instructions only |
| `sdlc-extras` | ✅ | ❌ |

More: [spec 11](../specs/11-multi-agent.md).

## Tested versions

From the release notes' smoke-test lines. Newer versions haven't been checked.

| Agent | Checked on | What ran | Release notes |
|---|---|---|---|
| Claude Code | 2.1.318 to 2.1.322 | Full smoke test (A–H); later releases ran only the parts they changed | 3.2.0, 3.2.1, 3.6.0 |
| Codex | 0.154.0 | Setup and a Claude Code join (smoke test J) | 3.2.0, 3.2.1 |
| Antigravity CLI | 1.0.16 and 1.5.1 | Setup and a Claude Code join (smoke test J) | 3.2.0, 3.2.1 |
| Cursor | not yet recorded | Installs with its hooks registered (1.8.1); smoke test not run | 1.8.1 |
| Windows (any agent) | not yet recorded | Smoke test I not run | 3.2.0, 3.2.1 |

Codex releases before 0.141.0 install the plugin but run no plugin hooks, as reported by another plugin's tests (microsoft/TokenEconomizer).
