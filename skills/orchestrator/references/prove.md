# Prove (Stage 5): judge Build's evidence, review and security in one round

**Who gets Prove.** M on `Flow: full`, L, and every backlog at its Feature close, unless the user chose `Prove: skip` before Build (Define's approval). S, M on `Flow: lite`, and `Prove: skip` go from Build straight to Ship on Build's passing `verify.py` (`build.md`'s gate), except that a security-touched change on `Prove: skip` still comes here for its full security review alone. A feature split into slices or tasks gets one Prove, at the end (`backlog-slices.md`'s Feature close), never one per slice or task.

Entered from Build's gate (`state.py advance <f> 5 --gate pass`; Feature close: `advance <f> 5` from Stage 6). Old Stages 5–7 live here: a feature resumed at 6 or 7 picks up from what its Gate log shows. Stage 5 switches on the budget hook (every shell command other than the project's own is killed at 120 s, exit 124, and never runs in the background or under Monitor, so nothing is polled) and the freshness hook for every fix: a code change marks test results stale, a full run (`verify.py`, or the suite with no filters) marks them fresh, and a turn can't end stale.

Build produced the evidence (`build.md`): every acceptance criterion's test recorded failing before its code, then one passing `verify.py`. Prove doesn't execute that again; it judges it (ADR 0013).

## The round

`$V` below stands for `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/verify.py"`: type that full command each time, never a shell variable or alias, or the hooks won't recognise the run (no record, and in Prove it is killed at 120 s). On the review-ready commit:

1. **Evidence.** Never rerun Build's own proof scripts (an old-vs-new comparison, a load or timing run) unless the files they cover changed since; `verify.py`'s record is the evidence. `$V status`. `reuse: true`: the last verify passed, the hook's own copy agrees and the code hasn't changed since, so use it. Otherwise run `$V` once in this session; a FAIL goes back to Build with its failure lines. `verify.py` doesn't read `.sdlc/baseline.md`: when a project has one and only the test step fails, read the output yourself, and if every failure is listed there, log it with `state.py log` and go on (no reuse then; rerun `$V` after any later change).
2. **Security-touched?** Yes when `Risk: high`, or the diff since `Base:` touches `areas.sensitive` or `areas.migrations` in `.sdlc/config.json` (auth, payments, secrets, PII, migrations by default). Only then does security run (the column below); otherwise there is no security review beyond the always-on pattern hooks.
3. **Dispatch at the same time**, each fresh, on the same commit, what the track runs:

| Track | AC checker | Code reviewer | Also | Security, when security-touched | Re-verification |
|---|---|---|---|---|---|
| M, `Flow: full`, either risk | none: the checker does it | the **checker**: one, top, one-pass brief plus the AC check | ui-reviewer on UI | one, top | fixes in Build, then `verify.py` and a fresh checker on what changed |
| L | standard | one, top, one-pass brief | ui-reviewer on UI | one, top | fixes in Build, then `verify.py` and the AC checker on what failed |
| Feature close (every backlog) | standard, every AC | one, top, `Base..HEAD`, one-pass brief | qa-tester; ui-reviewer on UI | one, top | fixes in Build, then `verify.py` and the AC checker on what failed |

- **Old plan** (no `## Acceptance tests` in `plan.md`; `$V` says so): this feature keeps the previous round. Dispatch a fresh `sdlc:verifier` in place of the AC checker (the feature dir, the round number, the commands, whether a qa-tester runs), and re-verify fixes with a fresh verifier.
- **The checker** (M): one fresh `sdlc:code-reviewer` that also does the AC check, reading the diff once: add to its one-pass brief "First read each `AC-nnn` in `spec.md` beside the test `plan.md`'s `## Acceptance tests` names for it and say whether the test would fail if the behaviour were missing (`AC-001: proves` / `does not prove: <what it misses>`)." Never resumed; a re-check is a fresh checker on what changed.
- **`sdlc:ac-checker`** (standard tier; L and Feature close): the feature dir; in a later round, only the AC ids that failed. It reads each acceptance criterion beside its named test (or what a `manual` row points to) and says whether the test proves it. It runs nothing. Never resume or message one from an earlier round.
- **`sdlc:code-reviewer`:** never the context that wrote the code. Its brief is `review-brief.md` plus the diff facts: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/diff_stats.py" --format md [--base <ref>] --plan <intents>/plan.md` (Feature close: one `--plan` per `plan-B*.md` too). It is read-only: it reads code and diffs and may run the project's test command, never scripts of its own; a suspicion that needs a probe is a finding for the user. It is the only code reviewer, on every track, with the **one-pass brief**: add "Cover in one pass: correctness; silent failures (swallowed errors, fallbacks that hide a failure, missing error paths); test gaps (a behaviour or failure mode the spec implies that no test would catch, rated 1–10, 8 or more is high); and, unless a security review runs, security (injection, untrusted input reaching a shell, terminal, file path or database, secrets in the diff)." `sdlc:ui-reviewer` (`ui-work.md`) on a UI diff.
- **`sdlc:qa-tester`** (Feature close only): the feature dir, the round, the commands and whether a browser tool is available. Never the diff, plan or tests. It runs the feature against the spec as a user would and writes `qa-report.md`, keeping everything its runs create under `.sdlc/.work/qa/`. Outside these rounds it runs only when the user asks.
- **Full security** (security-touched only): one more `sdlc:code-reviewer` (top tier, like every code review: the model router enforces it), with a security-only brief: injection, authz, secrets, SSRF, XSS, unsafe deserialization, dependency risk. Meanwhile, in this session: the stack's dependency audit (`npm audit --omit=dev`, `pip-audit`, …), and every finding the security-guidance hooks have raised. Deeper scans (optional, not bundled): `integrations.md`.

## Then

1. **Log.** One file holds Prove's record: `<intents>/review.md` (a feature started earlier keeps its `test-report.md` and `security.md`). Append a round to it in this shape (the `sdlc-invariants` CI check reads the header, both tables and the verdict line):

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
   ```

   Then `state.py round <f> <N> pass|fail "<one-line reason>" --commit <sha>`, and the reviews with `state.py log <f> "<summary>" --type review_done`.
2. **Findings go back to Build.** With any high finding (from any checker or the audit): `state.py advance <f> 4`, and fix them all together there, each with a failing test first (`sdlc:systematic-debugging` for anything unexplained; `Build: subagent`: back to the implementer), then `$V`.
   - An AC the checker says doesn't prove: fix its test (or its Run cell) so it would catch the behaviour missing, and record the change in `## Deviations` (what, why, effect). Its code already exists, so it can't be recorded red again; the fresh AC checker in step 3 reads the new test.
   - A failed qa scenario is a finding like any other; only a failure that needs a new requirement goes to the user.
   - Simplifications are findings.
   - Medium and low go to `review.md`'s `## Tickets`. Comment noise flagged by the diff facts is medium and fixed now.
   - List each fixed high finding in `review.md` under `## Fixed`, one line each (what and where); Learn reads it.
   - A failure to baseline is the user's decision, recorded with `state.py deviation` naming the test; never added silently.
3. **One re-verification** once the fixes pass `$V` in Build: `state.py advance <f> 5`, `$V status` (reuse), then what the track's Re-verification column says: on M a fresh checker on what changed and the earlier highs; on L and Feature close a fresh `sdlc:ac-checker` on the ACs that failed (only when one did), and no second reviewer round. Then `state.py verified` with the resulting tree, and `state.py log <f> "fixes re-verified (<verify result>)"`. Nothing to fix: no re-verification.
4. **Still failing** (verify is red after a fix pass, or the AC checker, on M the checker, still says an AC doesn't prove or a high stands): when a requirement that failed in the previous round fails again, stop (below). Otherwise back to Build and re-verify as in steps 2 and 3, without asking.
5. **UI.** The ui-reviewer's high findings are off-system values or components, AI-slop patterns, missing states and accessibility blockers. A visual check (screenshots) runs only when the user asks; say so in its brief. Its "Proposed design-system changes" go to the user. Accepted: add them to `<docs>/design-system.md`, log it, and the findings they cover are resolved. Declined: the code moves to an existing token or component, which is a code change, so back to Build.

The verdict comes from the latest `verify.py` run on the current code and the latest AC checker; `sdlc:verification-before-completion` covers anything you claim yourself. On request: `/sdlc:review-pr`, `/sdlc:code-review` (a GitHub PR), `sdlc:receiving-code-review`.

**Report when done:** the end-of-Prove message lists every drift (what, why, effect) and every `manual` AC, so the user sees them without opening the plan.

**Stop and ask** when the same requirement fails in two rounds, or after round 3 fails (the round cap): bring the user what still fails, what each round changed and a root-cause hypothesis. Don't start another round.

**Gate:**
- `verify.py` passes on the current code (`$V status` shows `reuse: true`), and an `sdlc:ac-checker` dispatched in Stage 5 (on M, the checker) passed every AC (`.sdlc/.work/dispatches.jsonl` shows it). Old plans: a verifier dispatched in Stage 5 passes on the current commit, as before. PASS means no *new* failures: those in `.sdlc/baseline.md` don't count.
- Every acceptance criterion has a test that failed before its code and passes now, or is `manual` with its reason and the checker's reading.
- No unresolved high finding from any checker (a waiver is the user's, recorded with `state.py deviation`); medium and low are ticketed. Under the relay, every report of the latest round ends `VERDICT: PASS`: only a checker judges, never the agent that wrote the code.
- No test gap rated 8 or more, and no skipped or retried-until-green test touching this feature.
- Security-touched: no critical or high security finding open, no secrets in the diff, and `review.md`'s `## Security` section written (findings, the dependency audit, the hooks' findings). Otherwise: nothing to record beyond the pattern hooks.

Then `state.py verified <f> <commit> <tree>` (the core's Verified tree) and `state.py advance <f> 8 --gate pass`.
