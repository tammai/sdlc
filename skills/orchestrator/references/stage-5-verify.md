# Stage 5 · Verify (rounds, max 3)

`state.py advance <f> 5` first: `Current: Stage 5 – Verify` switches on the freshness hook. Any code change (by any tool, in git repos) marks test results stale, a full test-suite run (no name filters, no single test file or package) marks them fresh, and finishing a turn while stale is blocked.

Each round:
1. **Spawn a NEW `sdlc:verifier` agent.** Always a fresh spawn: never resume or message a verifier from an earlier round, and never verify inline in this context. Brief it with: feature dir, round number, the build/lint/typecheck/test commands from state. It runs everything fresh, proves each acceptance criterion, and appends `## Round N — <time> — commit <hash>` to `test-report.md`.
2. In parallel (M and L tracks, full flow), spawn fresh `sdlc:pr-test-analyzer` (gaps rated 1–10) and `sdlc:silent-failure-hunter` on the current diff.
3. Log the round: `state.py round <f> <N> pass|fail "<one-line reason>" --commit <sha>`.
4. Verdict:
   - Verifier PASS, no test gap rated ≥ 8, no high-severity silent failure → gate passes. PASS means no *new* failures: failures listed in `.sdlc/baseline.md` don't fail the round. If the verifier asks to baseline a failure, that's a user decision, recorded with `state.py deviation` naming the test (the sdlc-invariants CI check looks for it); it's never added silently.
   - Otherwise → back to Stage 4 for the listed failures only (TDD: failing test first, `sdlc:systematic-debugging` for anything unexplained), then Stage 5 again and the next round with another fresh verifier.
5. **Round cap** (the core's).

You may run commands to investigate, but the verdict always comes from that round's fresh verifier; `sdlc:verification-before-completion` applies to anything you claim yourself.

- S track: one verifier per round (no analyzer or hunter); the bug's repro test must be among the evidence and must fail on Base (the verifier's red-green check).
- QA round, only when the user asks for one: spawn a fresh `sdlc:qa-tester` with the feature dir, the commands and whether a browser tool is available, and no diff, plan or test files. It runs the feature against the spec as a user would and writes `qa-report.md`. Bring its failures to the user, who decides whether they send the feature back to Stage 4; it isn't part of the gate.
- **Gate:** latest round's verifier verdict PASS on the current commit (no code edits since: the hook enforces this), from an `sdlc:verifier` dispatched in Stage 5 (`.sdlc/.work/dispatches.jsonl`, written by the model router, shows it; a verdict from any other agent doesn't count); every acceptance criterion has evidence; no gap ≥ 8; no skipped or retried-until-green test touching this feature. On a pass, `state.py verified <f> <commit> <tree>` (the core's Verified tree), then `state.py advance <f> 6 --gate pass`.
