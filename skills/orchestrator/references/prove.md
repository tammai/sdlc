# Prove (Stage 5): judge Build's evidence, review and security in one parallel round

Entered from Build's gate (`state.py advance <f> 5 --gate pass`; Feature close: `advance <f> 5` from Stage 6). Old Stages 5–7 live here: a feature resumed at 6 or 7 picks up from what its Gate log shows. Stage 5 switches on the budget hook (every shell command other than the project's own is killed at 120 s, exit 124, and never runs in the background or under Monitor, so nothing is polled) and the freshness hook for every fix: a code change marks test results stale, a full run (`verify.py`, or the suite with no filters) marks them fresh, and a turn can't end stale.

Build produced the evidence (`build.md`): every acceptance criterion's test recorded failing before its code, then one passing `verify.py`. Prove doesn't execute that again; it judges it (ADR 0013).

## The round

`V="python3 ${CLAUDE_PLUGIN_ROOT}/scripts/verify.py"`. On the review-ready commit:

1. **Evidence.** `$V status`. `reuse: true`: the last verify passed, the hook's own copy agrees and the code hasn't changed since, so use it. Otherwise run `$V` once in this session; a FAIL goes back to Build with its failure lines. `verify.py` doesn't read `.sdlc/baseline.md`: when a project has one and only the test step fails, read the output yourself, and if every failure is listed there, log it with `state.py log` and go on (no reuse then; rerun `$V` after any later change).
2. **Dispatch at the same time**, each fresh, on the same commit, what the track runs:

| Track | AC checker | Code reviewer | Also | Security | Re-verification |
|---|---|---|---|---|---|
| S | — | — | — | hooks only | in-session `verify.py` |
| M, `Flow: lite` | standard | — | — | light | in-session `verify.py` |
| M, `Flow: full`, either risk | standard | one, standard, light brief | ui-reviewer on UI | light; full, standard, on auth, payments, secrets, PII, migrations | in-session `verify.py` |
| L | standard | top | silent-failure-hunter; pr-test-analyzer; ui-reviewer on UI | full, top | in-session `verify.py` |
| Slice | standard | the same, this slice only | ui-reviewer on UI | at Feature close | in-session `verify.py` |
| Feature close | standard, every AC | top, `Base..HEAD` | qa-tester; ui-reviewer on UI | light; full on L or risk high | in-session `verify.py` |

- **Old plan** (no `## Acceptance tests` in `plan.md`; `$V` says so): this feature keeps the previous round. Dispatch a fresh `sdlc:verifier` in place of the AC checker (the feature dir, the round number, the commands, whether a qa-tester runs), and re-verify L and full-flow fixes with a fresh verifier.
- **S dispatches nothing.** The fix was built and checked in one place (`build.md`): its repro test recorded red, then `verify.py` passed. Confirm with step 1 and log it with `state.py round <f> 1 pass|fail "<reason>" --commit <sha>`. A FAIL goes back to the implementer.
- **`sdlc:ac-checker`** (standard tier): the feature dir; in a later round, only the AC ids that failed. It reads each acceptance criterion beside its named test (or what a `manual` row points to) and says whether the test proves it. It runs nothing. Never resume or message one from an earlier round.
- **`sdlc:code-reviewer`:** never the context that wrote the code. Its brief is `review-brief.md` plus the diff facts: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/diff_stats.py" --format md [--base <ref>] --plan <intents>/plan.md` (a slice: its `plan-B<n>.md`). On every track it is read-only: it reads code and diffs and may run the project's test command, never scripts of its own; a suspicion that needs a probe is a finding for the user. On M full it is the **light review**, the only code reviewer: add to its brief "Cover correctness, silent failures (swallowed errors, fallbacks that hide a failure, missing error paths) and security (injection, untrusted input reaching a shell, terminal, file path or database, secrets in the diff) in one pass." `sdlc:ui-reviewer` (`ui-work.md`) on a UI diff, except on M lite.
- **`sdlc:qa-tester`** (Feature close only): the feature dir, the round, the commands and whether a browser tool is available. Never the diff, plan or tests. It runs the feature against the spec as a user would and writes `qa-report.md`, keeping everything its runs create under `.sdlc/.work/qa/`. Outside these rounds it runs only when the user asks.
- **`sdlc:silent-failure-hunter`** on the diff and **`sdlc:pr-test-analyzer`** (gaps rated 1–10), on L.
- **Full security:** `sdlc:feature-reviewer` and `sdlc:code-reviewer` (L: top tier; M: standard), with a security-only brief: injection, authz, secrets, SSRF, XSS, unsafe deserialization, dependency risk.
- **Meanwhile, in this session** (light and full security): the stack's dependency audit (`npm audit --omit=dev`, `pip-audit`, …), and every finding the security-guidance hooks have raised. Deeper scans (optional, not bundled): `integrations.md`.

## Then

1. **Log.** Append a round to `<intents>/test-report.md` in this shape (the `sdlc-invariants` CI check reads the header, both tables and the verdict line):

   ```markdown
   ## Round <N> — <UTC time> — commit <hash>

   | Check | Command | Result |
   |---|---|---|
   | Verify | `verify.py` | ✅ pass, reused from Build (41s) / ❌ … |

   | Criterion | Evidence | Status |
   |---|---|---|
   | AC-001 … | `tests/x.py` › name: red at Build, passes; ac-checker: proves | ✅ |
   | AC-002 … | manual: checked by reading, not by a test (<what the checker read>) | ✅ |

   **Drift:** each `## Deviations` line from `plan.md` (what, why, effect), or none
   **Verdict:** PASS | FAIL
   ``` Then `state.py round <f> <N> pass|fail "<one-line reason>" --commit <sha>`, and the reviews with `state.py log <f> "<summary>" --type review_done`.
2. **Fix every high finding together**, from all checkers and the audit, each with a failing test first (`sdlc:systematic-debugging` for anything unexplained; `Build: subagent`: back to the implementer).
   - An AC the checker says doesn't prove: fix its test (or its Run cell) so it would catch the behaviour missing, and record the change in `## Deviations` (what, why, effect). Its code already exists, so it can't be recorded red again; the fresh AC checker in step 3 reads the new test.
   - A failed qa scenario is a finding like any other; only a failure that needs a new requirement goes to the user.
   - Simplifications are findings.
   - Medium and low go to `<intents>/review.md` as tickets. Comment noise flagged by the diff facts is medium and fixed now.
   - List each fixed high finding in `review.md` under `## Fixed`, one line each (what and where); Learn reads it.
   - A failure to baseline is the user's decision, recorded with `state.py deviation` naming the test; never added silently.
3. **One re-verification** of the fixed code, in this session: `$V`, then a fresh `sdlc:ac-checker` on the ACs that failed (only when one did), then `state.py verified` with the resulting tree, and `state.py log <f> "fixes re-verified in-session (<verify result>)"`. No second reviewer round. Nothing to fix: no re-verification.
4. **Still failing** (verify is red after a fix pass, or the AC checker still says an AC doesn't prove): when a requirement that failed in the previous round fails again, stop (below). Otherwise fix it and re-verify as in step 3, without asking.
5. **UI.** The ui-reviewer's high findings are off-system values or components, AI-slop patterns, missing states and accessibility blockers. A visual check (screenshots) runs only when the user asks; say so in its brief. Its "Proposed design-system changes" go to the user. Accepted: add them to `<docs>/design-system.md`, log it, and the findings they cover are resolved. Declined: the code moves to an existing token or component, which is a code change, so re-verify.

The verdict comes from the latest `verify.py` run on the current code and the latest AC checker; `sdlc:verification-before-completion` covers anything you claim yourself. On request: `/sdlc:review-pr`, `/sdlc:code-review` (a GitHub PR), `sdlc:receiving-code-review`.

**Report when done:** the end-of-Prove message lists every drift (what, why, effect) and every `manual` AC, so the user sees them without opening the plan.

**Stop and ask** when the same requirement fails in two rounds, or after round 3 fails (the round cap): bring the user what still fails, what each round changed and a root-cause hypothesis. Don't start another round.

**Gate:**
- `verify.py` passes on the current code (`$V status` shows `reuse: true`), and an `sdlc:ac-checker` dispatched in Stage 5 passed every AC (`.sdlc/.work/dispatches.jsonl` shows it). Old plans: a verifier dispatched in Stage 5 passes on the current commit, as before. S: the repro test recorded red and `verify.py` passes. PASS means no *new* failures: those in `.sdlc/baseline.md` don't count.
- Every acceptance criterion has a test that failed before its code and passes now, or is `manual` with its reason and the checker's reading.
- No unresolved high finding from any checker (a waiver is the user's, recorded with `state.py deviation`); medium and low are ticketed.
- No test gap ≥ 8 (L), and no skipped or retried-until-green test touching this feature.
- No critical or high security finding open, and no secrets in the diff. Write `<intents>/security.md` on full security; otherwise log the audit result.

Then `state.py verified <f> <commit> <tree>` (the core's Verified tree) and `state.py advance <f> 8 --gate pass`.
