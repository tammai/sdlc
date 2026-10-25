# Stage 5 · Verify and review (one parallel round, then one re-verification)

Entered from the Stage 4 gate (`state.py advance <f> 5 --gate pass`; Feature close: `advance <f> 5` from Stage 6). `Current: Stage 5 – Verify` switches on the freshness hook. Any code change (by any tool, in git repos) marks test results stale, a full test-suite run (no name filters, no single test file or package) marks them fresh, and finishing a turn while stale is blocked.

**The round.** On the review-ready commit (build done, full suite green), dispatch at the same time, each fresh, on the same commit:
- `sdlc:verifier`: feature dir, round number, the build/lint/typecheck/test commands. It runs everything fresh, proves each acceptance criterion and appends `## Round N — <time> — commit <hash>` to `test-report.md`. Never resume or message a verifier from an earlier round, and never verify inline.
- `sdlc:code-reviewer` with the brief in `review-brief.md`: top tier on the full flow (M and L) and at a backlog's Feature close; standard on S, Lite and slices. `sdlc:ui-reviewer` when the diff touches `areas.ui` (`ui-work.md`).
- Full flow only: `sdlc:silent-failure-hunter` on the diff (M and L); `sdlc:pr-test-analyzer` (gaps rated 1–10) on L. `sdlc:qa-tester` (below) on full-flow M, a single-session Lite feature and a backlog's Feature close. S: verifier and reviewer only. Lite and slices dispatch as their files say (`lite-flow.md`, `backlog-slices.md`).

**The qa-tester** gets the feature dir, the round, the commands and whether a browser tool is available; never the diff, plan or tests. It runs the feature against the spec as a user would and writes `qa-report.md`, keeping everything its runs create under `.sdlc/.work/qa/`. A failed scenario, edge case or Blocker probe is a finding like any other, fixed in this batch; only a failure that needs a new requirement goes to the user. On S, and outside these rounds, it runs only when the user asks.

**Then:**
1. Log the round: `state.py round <f> <N> pass|fail "<one-line reason>" --commit <sha>`; the review: `state.py log <f> "<summary>" --type review_done`.
2. Fix every high finding from all of them together, each with a failing test first (`sdlc:systematic-debugging` for anything unexplained); medium and low go to `<intents>/review.md` as tickets (comment noise flagged by the diff facts is medium and fixed now). Simplifications are findings like the rest. A failure the verifier asks to baseline is a user decision, recorded with `state.py deviation` naming the test (the sdlc-invariants CI check looks for it); never added silently. `Build: subagent`: the findings go back to the implementer.
3. **One re-verification** of the fixed commit: a new fresh `sdlc:verifier` (round N+1). Only the verifier reruns. Nothing to fix → no re-verification.
4. Still failing → fix and verify again, up to the core's round cap.

You may run commands to investigate, but the verdict always comes from the latest fresh verifier; `sdlc:verification-before-completion` applies to anything you claim yourself.

- S track: the bug's repro test must be among the verifier's evidence and must fail on Base (its red-green check).
- **Gate:** the latest verifier PASS on the current commit (the hook enforces no edits since), from an `sdlc:verifier` dispatched in Stage 5 (`.sdlc/.work/dispatches.jsonl` shows it; a verdict from any other agent doesn't count). PASS means no *new* failures: failures listed in `.sdlc/baseline.md` don't count. Every acceptance criterion has evidence; no unresolved high finding from the reviewers, hunter or qa-tester; no test gap ≥ 8 (L); no skipped or retried-until-green test touching this feature. Then `state.py verified <f> <commit> <tree>` (the core's Verified tree) and `state.py advance <f> 6 --gate pass`.
