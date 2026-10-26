# Prove (Stage 5): verify, review and security in one parallel round

Entered from Build's gate (`state.py advance <f> 5 --gate pass`; Feature close: `advance <f> 5` from Stage 6). Old Stages 5–7 live here: a feature resumed at 6 or 7 picks up from what its Gate log shows. Stage 5 switches on the freshness hook for every fix: a code change marks test results stale, a full suite run (no filters, no single file or package) marks them fresh, and a turn can't end stale.

## The round

On the review-ready commit (build done, full suite green), dispatch at the same time, each fresh, on the same commit, what the track runs:

| Track | Verifier | Code reviewer | Also | Security | Re-verification |
|---|---|---|---|---|---|
| S | standard | standard | — | hooks only | fresh verifier |
| M, `Flow: lite` | standard | standard | qa-tester (single session); ui-reviewer on UI | light | in-session suite |
| M, `Flow: full` | standard | top | qa-tester, silent-failure-hunter; ui-reviewer on UI | light; full on auth, payments, secrets, PII, migrations | fresh verifier |
| L, or risk high | top | top | silent-failure-hunter; pr-test-analyzer (L); qa-tester (M); ui-reviewer on UI | full, top | fresh verifier |
| Slice | standard (top on risk high) | the same, this slice only | ui-reviewer on UI | at Feature close | in-session suite |
| Feature close | the same, whole branch | top, `Base..HEAD` | qa-tester; ui-reviewer on UI | light; full on L or risk high | in-session suite |

- **`sdlc:verifier`:** the feature dir, the round number, the build/lint/typecheck/test commands. It runs everything fresh, proves each acceptance criterion and appends `## Round N — <time> — commit <hash>` to `test-report.md`. Never resume or message a verifier from an earlier round, and never verify inline.
- **`sdlc:code-reviewer`:** never the context that wrote the code. Its brief is `review-brief.md` plus the diff facts: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/diff_stats.py" --format md [--base <ref>] --plan <intents>/plan.md` (a slice: its `plan-B<n>.md`). `sdlc:ui-reviewer` (`ui-work.md`) on a UI diff.
- **`sdlc:qa-tester`:** the feature dir, the round, the commands and whether a browser tool is available. Never the diff, plan or tests. It runs the feature against the spec as a user would and writes `qa-report.md`, keeping everything its runs create under `.sdlc/.work/qa/`. Outside these rounds it runs only when the user asks.
- **`sdlc:silent-failure-hunter`** on the diff; **`sdlc:pr-test-analyzer`** on L (gaps rated 1–10).
- **Full security:** `sdlc:feature-reviewer` and `sdlc:code-reviewer`, top tier, with a security-only brief: injection, authz, secrets, SSRF, XSS, unsafe deserialization, dependency risk.
- **Meanwhile, in this session** (light and full security): the stack's dependency audit (`npm audit --omit=dev`, `pip-audit`, …), and every finding the security-guidance hooks have raised. Deeper scans (optional, not bundled): `integrations.md`.

## Then

1. **Log.** The round: `state.py round <f> <N> pass|fail "<one-line reason>" --commit <sha>`. The reviews: `state.py log <f> "<summary>" --type review_done`.
2. **Fix every high finding together**, from all checkers and the audit, each with a failing test first (`sdlc:systematic-debugging` for anything unexplained; `Build: subagent`: back to the implementer).
   - A failed qa scenario is a finding like any other; only a failure that needs a new requirement goes to the user.
   - Simplifications are findings.
   - Medium and low go to `<intents>/review.md` as tickets. Comment noise flagged by the diff facts is medium and fixed now.
   - List each fixed high finding in `review.md` under `## Fixed`, one line each (what and where); Learn reads it.
   - A failure the verifier asks to baseline is the user's decision, recorded with `state.py deviation` naming the test; never added silently.
3. **One re-verification** of the fixed code. `Flow: full` and S: a new fresh `sdlc:verifier` (round N+1); only the verifier reruns. `Flow: lite`, slices and Feature close: the full suite in this session, `state.py verified` with the resulting tree, and `state.py log <f> "lite: fixes re-verified in-session (<suite result>)"`. Nothing to fix and the verifier passed: no re-verification.
4. **Still failing** (the in-session suite is red after a fix pass, a verifier FAIL the fixes don't address, or a fresh verifier FAIL): fix and dispatch a fresh verifier round, on any flow, without asking. Only the core's round cap stops.
5. **UI.** The ui-reviewer's high findings are off-system values or components, AI-slop patterns, missing states and accessibility blockers. A visual check (screenshots) runs only when the user asks; say so in its brief. Its "Proposed design-system changes" go to the user. Accepted: add them to `<docs>/design-system.md`, log it, and the findings they cover are resolved. Declined: the code moves to an existing token or component, which is a code change, so re-verify.

The verdict comes from the latest verifier (`Flow: lite`: or the in-session run after fixes that address its failures); `sdlc:verification-before-completion` covers anything you claim yourself. S: the bug's repro test must be among the verifier's evidence and must fail on Base. On request: `/sdlc:review-pr`, `/sdlc:code-review` (a GitHub PR), `sdlc:receiving-code-review`.

**Round cap:** after verify round 3 fails, stop and bring the user what still fails, what each round changed and a root-cause hypothesis.

**Gate:**
- The verifier passes on the current commit, dispatched in Stage 5 (`.sdlc/.work/dispatches.jsonl` shows it; a verdict from any other agent doesn't count). PASS means no *new* failures: those in `.sdlc/baseline.md` don't count.
- Every acceptance criterion has evidence.
- No unresolved high finding from any checker (a waiver is the user's, recorded with `state.py deviation`); medium and low are ticketed.
- No test gap ≥ 8 (L), and no skipped or retried-until-green test touching this feature.
- No critical or high security finding open, and no secrets in the diff. Write `<intents>/security.md` on full security; otherwise log the audit result.

Then `state.py verified <f> <commit> <tree>` (the core's Verified tree) and `state.py advance <f> 8 --gate pass`.
