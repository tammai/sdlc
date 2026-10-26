# Prove (Stage 5): verify, review and security in one parallel round

Entered from Build's gate (`state.py advance <f> 5 --gate pass`; Feature close: `advance <f> 5` from Stage 6). Old Stages 5–7 live here: a feature resumed at 6 or 7 picks up from what its Gate log shows. Stage 5 switches on the budget hook (every shell command other than the project's own is killed at 120 s, exit 124, and never runs in the background or under Monitor, so nothing is polled) and the freshness hook for every fix: a code change marks test results stale, a full suite run (no filters, no single file or package) marks them fresh, and a turn can't end stale.

## The round

On the review-ready commit (build done, full suite green), dispatch at the same time, each fresh, on the same commit, what the track runs:

| Track | Verifier | Code reviewer | Also | Security | Re-verification |
|---|---|---|---|---|---|
| S | — | — | — | hooks only | in-session suite |
| M, `Flow: lite` | standard | — | — | light | in-session suite |
| M, `Flow: full`, either risk | standard | one, standard, light brief | ui-reviewer on UI | light; full, standard, on auth, payments, secrets, PII, migrations | in-session suite; fresh verifier only when the verifier failed or a fix went beyond the findings |
| L | top | top | silent-failure-hunter; pr-test-analyzer; ui-reviewer on UI | full, top | fresh verifier |
| Slice | standard (top on risk high) | the same, this slice only | ui-reviewer on UI | at Feature close | in-session suite |
| Feature close | the same, whole branch | top, `Base..HEAD` | qa-tester; ui-reviewer on UI | light; full on L or risk high | in-session suite |

- **S dispatches nothing.** The fix was built and checked in one place (`build.md`): its repro test failed before the fix, and the full suite passed after it. Here, run the full suite once yourself and confirm the implementer's report shows the repro test failing before the fix; log it with `state.py round <f> 1 pass|fail "<reason>" --commit <sha>`. A red suite goes back to the implementer.
- **`sdlc:verifier`:** the feature dir, the round number, the build/lint/typecheck/test commands, and whether a qa-tester runs in this round (then it writes no probes). It runs everything fresh, proves each acceptance criterion within its budget (2 min per command beyond the project's own, 10 min per round; runs the red-green check on Base with a per-test timeout) and appends `## Round N — <time> — commit <hash>` to `test-report.md`. Never resume or message a verifier from an earlier round, and never verify inline.
- **`sdlc:code-reviewer`:** never the context that wrote the code. Its brief is `review-brief.md` plus the diff facts: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/diff_stats.py" --format md [--base <ref>] --plan <intents>/plan.md` (a slice: its `plan-B<n>.md`). On every track it is read-only: it reads code and diffs and may run the project's test command, never scripts of its own; a suspicion that needs a probe is a finding for the verifier or the user. On M full it is the **light review**, the only code reviewer: add to its brief "Cover correctness, silent failures (swallowed errors, fallbacks that hide a failure, missing error paths) and security (injection, untrusted input reaching a shell, terminal, file path or database, secrets in the diff) in one pass." `sdlc:ui-reviewer` (`ui-work.md`) on a UI diff, except on M lite.
- **`sdlc:qa-tester`** (Feature close only): the feature dir, the round, the commands and whether a browser tool is available. Never the diff, plan or tests. It runs the feature against the spec as a user would and writes `qa-report.md`, keeping everything its runs create under `.sdlc/.work/qa/`. Outside these rounds it runs only when the user asks.
- **`sdlc:silent-failure-hunter`** on the diff and **`sdlc:pr-test-analyzer`** (gaps rated 1–10), on L.
- **Full security:** `sdlc:feature-reviewer` and `sdlc:code-reviewer` (L: top tier; M: standard), with a security-only brief: injection, authz, secrets, SSRF, XSS, unsafe deserialization, dependency risk.
- **Meanwhile, in this session** (light and full security): the stack's dependency audit (`npm audit --omit=dev`, `pip-audit`, …), and every finding the security-guidance hooks have raised. Deeper scans (optional, not bundled): `integrations.md`.

## Then

1. **Log.** The round: `state.py round <f> <N> pass|fail "<one-line reason>" --commit <sha>`. The reviews: `state.py log <f> "<summary>" --type review_done`.
2. **Fix every high finding together**, from all checkers and the audit, each with a failing test first (`sdlc:systematic-debugging` for anything unexplained; `Build: subagent`: back to the implementer). A defect a probe found starts from that probe's script (`.sdlc/.work/probes/`, `.sdlc/.work/qa/`): turn it into a failing test in the project's suite, then fix.
   - A failed qa scenario is a finding like any other; only a failure that needs a new requirement goes to the user.
   - Simplifications are findings.
   - Medium and low go to `<intents>/review.md` as tickets. Comment noise flagged by the diff facts is medium and fixed now.
   - List each fixed high finding in `review.md` under `## Fixed`, one line each (what and where); Learn reads it.
   - A failure the verifier asks to baseline is the user's decision, recorded with `state.py deviation` naming the test; never added silently.
3. **One re-verification** of the fixed code. L, and `Flow: full` when the verifier itself failed a requirement or a fix touched files outside the findings: a new fresh `sdlc:verifier` (round N+1); only the verifier reruns. S, `Flow: lite`, `Flow: full` otherwise (fixes for reviewer, security or UI findings only), slices and Feature close: the full suite in this session, which includes the fixes' new failing-first tests, `state.py verified` with the resulting tree, and `state.py log <f> "lite: fixes re-verified in-session (<suite result>)"`. Nothing to fix and the verifier passed: no re-verification.
4. **Still failing** (the in-session suite is red after a fix pass, a verifier FAIL the fixes don't address, or a fresh verifier FAIL): when a requirement that failed in the previous round fails again, stop (below). Otherwise fix it and re-verify as in step 3, without asking.
5. **UI.** The ui-reviewer's high findings are off-system values or components, AI-slop patterns, missing states and accessibility blockers. A visual check (screenshots) runs only when the user asks; say so in its brief. Its "Proposed design-system changes" go to the user. Accepted: add them to `<docs>/design-system.md`, log it, and the findings they cover are resolved. Declined: the code moves to an existing token or component, which is a code change, so re-verify.

The verdict comes from the latest verifier (or, where step 3 re-verifies in the session, the in-session run after the fixes; S: the in-session run); `sdlc:verification-before-completion` covers anything you claim yourself. On request: `/sdlc:review-pr`, `/sdlc:code-review` (a GitHub PR), `sdlc:receiving-code-review`.

**Stop and ask** when the same requirement fails in two rounds, or after verify round 3 fails (the round cap): bring the user what still fails, what each round changed and a root-cause hypothesis. Don't start another round. A criterion the verifier or QA could not verify within budget also goes to the user, never counted as passed.

**Gate:**
- A verifier dispatched in Stage 5 ran this round, and it passes on the current commit, or, where step 3 re-verifies in the session, the full suite passes on it after the fixes (`.sdlc/.work/dispatches.jsonl` shows it; a verdict from any other agent doesn't count). PASS means no *new* failures: those in `.sdlc/baseline.md` don't count. S: the repro test failed before the fix and the full suite, run in this session on the current code, passes.
- Every acceptance criterion has evidence.
- No unresolved high finding from any checker (a waiver is the user's, recorded with `state.py deviation`); medium and low are ticketed.
- No test gap ≥ 8 (L), and no skipped or retried-until-green test touching this feature.
- No critical or high security finding open, and no secrets in the diff. Write `<intents>/security.md` on full security; otherwise log the audit result.

Then `state.py verified <f> <commit> <tree>` (the core's Verified tree) and `state.py advance <f> 8 --gate pass`.
