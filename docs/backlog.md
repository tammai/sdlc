# Backlog

Open work after 1.5.0. Most important first.

## Verify what's built

1. **Live recheck on an M-track feature** (about 10 min, about $4). The prompt-only rules of 1.5.0 have never run in a real session: Stage 4 skips the final whole-branch review; Stage 6 runs the simplifier first, then the whole-branch `code-reviewer` on `opus`, and any code change goes back to Stage 5; Stage 8 checks `Verified:`; the qa-tester reruns only when non-test code changed; dated feature names; `state.md` lines land under their own headings.
2. **qa-tester paths not yet run live:** a UI feature with a browser tool; `Risk: high`; a monorepo (red-green `install` per package); a feature with no runnable surface.

## Pipeline audit, still open (`docs/audits/2026-10-22-pipeline-review.md`)

3. **PIPE-01 (Critical):** the files the hooks trust live in `.sdlc/`, which the agent can edit unnoticed. Seal each verify round (hash spec, baseline and config with the commit).
4. **PIPE-06:** freshness ignores the test exit code, tracks only the first Stage 5 feature, and fails silently. Check first whether the Bash `tool_response` carries an exit code.
5. **PIPE-04, rest:** `qa-tester` and `ui-reviewer` still inherit every tool (they need browser tools whose names differ per install), and the reviewers keep Bash. A before/after worktree check around a round would cover both.
6. **PIPE-05, rest:** the router checks agent names, not which stage runs; log dispatches and check them at the gate.
7. **PIPE-10:** no CI for the plugin repo (tests and `claude plugin validate` on Linux and Windows).
8. **PIPE-07:** setup never runs the commands it records.
9. **PIPE-08:** team hookify rules in a cloned repo are trusted; list non-`sdlc-*` rules in `/sdlc:status` and Stage 0.

## Decisions and gaps

10. **Which tracks get the qa-tester.** Stays on M and L. Revisit after a few real M features; if it never catches what the verifier misses, move it to L and high-risk only (one line in the orchestrator).
11. **Design:** M features rarely get a `quickstart.md`; the qa-tester falls back to the spec and README. No change unless that proves weak.
12. **`contracts/`:** the qa-tester uses them as input, but nothing checks that the built interfaces match them.
