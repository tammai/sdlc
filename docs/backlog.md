# Backlog

Open work after 1.5.0. Most important first.

## Verify what's built

1. **Live recheck on an M-track feature** (about 10 min, about $4). The 1.5.0 smoke test covered the S track (simplifier before the reviewer, `Verified:` recorded, freshness blocks). Not yet seen live on M: Stage 4 skipping its final whole-branch review, the whole-branch `code-reviewer` on `opus`, a Stage 6 code fix going back to Stage 5, and Stage 8's `Verified:` check.
2. **Red-green in a monorepo:** the verifier's `install` per package inside the worktree hasn't run live.

## From the 1.5.0 smoke test

3. **`Verified:` on uncommitted work:** when the work isn't committed at the Stage 5 gate, the orchestrator writes "commit + working tree", which Stage 8's `git diff <Verified:>` can't use. Say what to record (or commit first) in §5.
4. **Gate-log order:** new lines go at the top of their section, so the log isn't in time order. Say "append at the end of the section".

## Pipeline audit, still open (`docs/audits/2026-10-22-pipeline-review.md`)

5. **PIPE-01 (Critical):** the files the hooks trust live in `.sdlc/`, which the agent can edit unnoticed. Seal each verify round (hash spec, baseline and config with the commit).
6. **PIPE-06:** freshness ignores the test exit code, tracks only the first Stage 5 feature, and fails silently. Check first whether the Bash `tool_response` carries an exit code.
7. **PIPE-04, rest:** `ui-reviewer` still inherits every tool (it needs browser tools whose names differ per install), and the reviewers keep Bash. A before/after worktree check around a round would cover both.
8. **PIPE-05, rest:** the router checks agent names, not which stage runs; log dispatches and check them at the gate.
9. **PIPE-10:** no CI for the plugin repo (tests and `claude plugin validate` on Linux and Windows).
10. **PIPE-07:** setup never runs the commands it records.
11. **PIPE-08:** team hookify rules in a cloned repo are trusted; list non-`sdlc-*` rules in `/sdlc:status` and Stage 0.

## Gaps

12. **`contracts/`:** nothing checks that the built interfaces match them (the on-demand qa-tester reads them, but only when asked).
