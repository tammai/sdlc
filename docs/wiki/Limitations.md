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
- **An unlisted git folder in a workbench is reviewed like a member.** A git folder inside a seeded workbench that `workbench.json` doesn't list (a scratch clone, say) counts as a repo of unsure ownership, so each commit in it gets the model's commit review. That costs a review, never a missed one: limiting it to repos the watch has seen let a repo added and dropped between two looks escape review. Keep scratch clones outside the workbench folder.
- **Modes and skips are protected by notice, not by lock.** A move to advisory or a newly skipped step counts only after the trust anchor showed it and you replied, or once it is committed in any checkout with no local record (a fresh clone, a new worktree); an agent that commits the change and removes the record (`.sdlc/.work/trust-anchor.json`) still gets it honoured, visibly in git history, and one that writes an accepted entry straight into that record gets it honoured with nothing in git ([ADR 0030](../adr/0030-modes-and-skips.md)).
- **Plan approval is protected by notice, not by lock.** Under config `approval`, `state.py advance 2` waits for an approval recorded in `.sdlc/.work/approvals.json`; an agent that writes an entry there itself gets past it, as with the other records under `.sdlc/.work/`. A move to fewer stops (`ml` → `high-risk`), or a guard turned off in `guards`, is honoured without a notice the same way a mode or skip is: committed with the trust anchor's record removed, or written as accepted into that record ([ADR 0031](../adr/0031-approval-policy.md)). Headless Cursor sends no prompt event, so a typed `approve <feature>` can't reach it there.
- **Guarded changes are caught at verify, not at the edit, and read by name rules.** With `guards.dependencies` or `guards.lint_config` on, the edit or install itself goes ahead; verify (and so the part's commit, Review and Ship) waits for your Allow. TOML, YAML and `go.mod` manifests are read by a simple name rule that may flag a line that isn't a dependency; suppressions are counted per file, so swapping one for another of the same kind isn't flagged. A typed `allow` allows every item the last verify listed for the one feature waiting, which may include items you haven't read yet; the dialog allows only the items its question names. The allow record (`.sdlc/.work/guarded.json`) is agent-writable like the others; the allowed items reach the Gate log at Ship.
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

- **Headless Cursor sends no turn-end events.** `cursor-agent -p` (2026.11.05) registers `beforeSubmitPrompt` and `stop` but never fires them, so the review-cap lift, the freshness check and the trust anchor's turn-end check don't run in a headless Cursor run; its per-call checks do. The interactive app is unchecked.
- **Codex started from a Claude Code session** inherits that session's `CLAUDE_*` variables; the hooks drop `CLAUDE_PROJECT_DIR` and judge the repo Codex works in (checked live with Codex 0.154). Codex runs the sdlc version it cached at install: after updating sdlc, refresh it with `codex plugin add sdlc@sdlc`.

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
