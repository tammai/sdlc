# sdlc 2.0 Slim Process Core Implementation Plan

> **For agentic workers:** execute natively in this session (executing-plans), task by task, then one fresh top-tier review of the whole branch. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Turn the sdlc plugin into 2.0: the same intent/spec/plan record at every size, intent before code, a builder like plain Claude, reviews recommended after the build, learn before merge, green locally and on CI, stop at the PR.

**Architecture:** Approach C. The base stays: hooks, `verify.py`, `state.py`, setup/upgrade/eject, doctor, hookify, host adapters and every command. The flow is rewritten: the orchestrator and its references. Stage numbers stay so the hooks keep reading numbers, but there are only four phases: 1 Define, 4 Build, 5 Review, 8 Ship. A new state field, `Process: 2`, marks a 2.0 feature. Hooks ignore features without it, and `state.py` and `scaffold.py` refuse them, telling the user to finish them on 1.8.1. Prove's machinery is removed: the verifier, the ac-checker, rounds, the relay, Lite/Full and `Prove: run|skip`.

**Tech Stack:** Python 3.9+ stdlib (hooks, scripts), Markdown skills/agents/commands, unittest on Python 3.10.

**Spec:** `docs/sdlc/intents/2026-10-28-l-slim-process-core/brainstorm.md` (approved 2026-10-28). Read it first; this plan argues from it.

## Global Constraints

- Every typed command keeps its name and works: `/sdlc:setup`, `/sdlc:upgrade`, `/sdlc:eject`, `/sdlc:start`, `/sdlc:status`, `/sdlc:doctor`, `/sdlc:review-pr`, `/sdlc:code-review`, `/sdlc:hookify`, `/sdlc:knowledge-audit`, `/sdlc:revise-claude-md`, `/sdlc:commit`, `/sdlc:commit-push-pr`, `/sdlc:clean_gone`, `/sdlc:prune`, `/sdlc:context-diet`, `/sdlc:deploy`, and `/sdlc:start B<n>`.
- Codex, Cursor and Antigravity keep working: `scripts/hosts.py check` reports nothing stale.
- The always-on guards stay: secret blocking, pattern warnings, push security review, freshness hook, trust anchor, role guard.
- A hook stays silent outside the state it guards and never blocks on its own error (`.claude/rules/hooks.md`).
- Tests: one per user-visible behaviour, at the lowest level that proves it; no structural or meta tests. Run once on Python 3.10: `py -3.10 -m unittest discover -s tests -t tests`.
- Version `2.0.0` in `.claude-plugin/plugin.json`, `plugins/sdlc-extras/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.

## Acceptance tests

| AC | Behaviour | Test |
|---|---|---|
| AC-001 | A 2.0 feature's state carries `Process: 2`, and `advance` names the phases Define, Build, Review, Ship (stages 1, 4, 5, 8); any other stage number is refused | `tests/test_state.py::StateTest::test_a_2_0_feature_moves_through_four_phases` |
| AC-002 | `state.py` refuses a feature started under 1.x (no `Process: 2`), saying to finish it with sdlc 1.8.1 | `tests/test_state.py::StateTest::test_a_1x_feature_is_refused_with_how_to_finish_it` |
| AC-003 | The hooks ignore a 1.x feature: none of them acts on a state without `Process: 2` | `tests/test_sdlc_layout.py::LayoutTest::test_a_1x_feature_is_not_active_for_the_hooks` |
| AC-004 | The upgrade to 2.0 refuses while a 1.x feature is `Status: active`, naming it, and proceeds once none is | `tests/test_scaffold.py::ScaffoldTest::test_upgrade_to_2_waits_for_1x_features_to_finish` |
| AC-005 | At any size, leaving Review (Stage 5) without a passing full run on the current code is a trust-anchor notice | `tests/test_trust_anchor.py::TrustAnchorTest::test_leaving_review_needs_a_passing_full_run_at_every_size` |
| AC-006 | A reviewer's latest report with a FAIL verdict blocks leaving Review unless the user waived it | `tests/test_trust_anchor.py::TrustAnchorTest::test_a_review_fail_verdict_blocks_ship_unless_waived` |
| AC-007 | Every review agent (code-reviewer, ui-reviewer, qa-tester, pr-test-analyzer, silent-failure-hunter) runs on opus at every size | `tests/test_model_router.py::ModelRouterTest::test_every_review_runs_on_opus_at_every_size` |
| AC-008 | In Review, finishing on stale test results is blocked at every size (no Lite exemption) | `tests/test_verify_freshness.py::FreshnessTest::test_review_blocks_stale_results_at_every_size` |

## Public Surface

- state field `Process: 2`: AC-001, AC-002, AC-003
- state stage name `Review` (Stage 5): AC-001
- scaffold `upgrade-plan` key `old_features`: AC-004
- migration `migrations/2.0.0-slim-process.md`: AC-004
- template `templates/spec-template.md`, `templates/intent-template.md` and `templates/plan-template.md`, rewritten for every size: brainstorm goal 3
- reference `skills/orchestrator/references/review.md`, replacing `prove.md`: brainstorm goal 7

## Review Focus

1. **A repo with both a 1.x and a 2.0 feature active:** hooks act on the 2.0 one only; the 1.x one gets no notices. Test: Task 2's layout test includes both.
2. **A state file whose `Process:` line is hand-edited away mid-feature:** it becomes "1.x" and the hooks go quiet. The trust anchor must report a removed or changed `Process:` line like the other anchored fields. Test: Task 4.
3. **An old `Current: Stage 6/7` from 1.x** with `Process: 2` added by hand: `state.py` refuses unknown stages. Covered by AC-001's refusal of other numbers.
4. **The upgrade run with a 1.x feature `Status: done`:** done features don't block. Test: Task 3, in AC-004's test.
5. **The model router with no active 2.0 feature:** silent, as today. The existing `test_no_active_feature_is_silent` stays.

---

### Task 1: State has four phases and `Process: 2`

**Requirements:** AC-001, AC-002

**Files:**
- Modify: `scripts/state.py`: `STAGES`, `PHASES`, `FIELDS`, `check()`, the `round`, `verified` and `slice` commands
- Test: `tests/test_state.py`

**Interfaces:**
- Produces:
  - `STAGES = {1: "Define", 4: "Build", 5: "Review", 8: "Ship"}`
  - `check(text) -> int` raises `Refused("started under sdlc 1.x (no `Process: 2`): finish it with sdlc 1.8.1, or archive it")` when `^Process:\s*2\b` is missing.
  - `FIELDS` drops `Flow`, `Prove`, `Intent`, `Repro` and adds `Process`.
  - The `round` command is removed; `verified`, `log`, `deviation`, `blocker`, `set`, `sync`, `slice` and `advance` stay.

- [ ] **Step 1: Write the failing tests.** Both build their state the way `start.md` writes it, with `Process: 2`.
  - `test_a_2_0_feature_moves_through_four_phases`: `advance f 4`, then 5, then 8, each `ok`. The state reads `Current: Stage 5 – Review` after the second. `advance f 6` returns `ok: false` with "no Stage 6".
  - `test_a_1x_feature_is_refused_with_how_to_finish_it`: a state without `Process:`. `advance f 4` returns `ok: false`, and its error contains "sdlc 1.8.1".
- [ ] **Step 2:** `py -3.10 -m unittest tests.test_state -k four_phases -k 1x` → FAIL.
- [ ] **Step 3: Implement** the interfaces above. Remove the slice code paths only where they name Stage 6. A slice now rests at Stage 4 with its row `done <commit>`, and feature close goes 4 → 5.
- [ ] **Step 4:** Run `tests.test_state` and `tests.test_backlog`: PASS. Update the existing state tests that write states without `Process: 2`, or that use stages 2, 3, 6, 7, 9–11 or `round`, to the 2.0 shape. Delete tests whose only subject was a removed command.
- [ ] **Step 5: Commit** `feat(state)!: four phases and Process: 2; 1.x features are refused`.

### Task 2: Hooks see only 2.0 features

**Requirements:** AC-003

**Files:**
- Modify: `hooks/sdlc_layout.py`: `active(root)`
- Test: `tests/test_sdlc_layout.py`

**Interfaces:**
- Produces: `active(root) -> [(path, text)]` returns only states with `Status: active` **and** `^Process:\s*2\b`. Every hook that calls it (model_router, prove_budget, verify_freshness, trust_anchor, sdlc_review_gate's own `_active_features`) inherits this.

- [ ] **Step 1: Write the failing test.** `test_a_1x_feature_is_not_active_for_the_hooks`: two active states, one with `Process: 2` and one without; `active()` returns only the first.
- [ ] **Step 2:** Run it → FAIL.
- [ ] **Step 3: Implement** the filter in `active()`. In `hooks/sdlc_review_gate.py`, make `_active_features` add the same `Process: 2` condition.
- [ ] **Step 4:** Run the full suite. Add `Process: 2` to the hook tests' fixture states that should stay active: `test_model_router`, `test_prove_budget`, `test_verify_freshness`, `test_trust_anchor`, `test_sdlc_review_gate`, `test_role_guard`. PASS.
- [ ] **Step 5: Commit** `feat(hooks): act only on 2.0 features`.

### Task 3: Upgrade to 2.0 waits for 1.x features

**Requirements:** AC-004

**Files:**
- Modify: `scripts/scaffold.py`: `cmd_upgrade_plan` and the upgrade apply path
- Create: `migrations/2.0.0-slim-process.md`
- Test: `tests/test_scaffold.py`

**Interfaces:**
- Produces:
  - `upgrade-plan` JSON gains `"old_features": [<feature name>, ...]`: features with `Status: active` and no `Process: 2`.
  - When the target version's major is 2 and `old_features` is non-empty, the apply step exits 2 with `{"ok": false, "reason": "finish these with sdlc 1.8.1 first: <names>"}`.

- [ ] **Step 1: Write the failing test.** `test_upgrade_to_2_waits_for_1x_features_to_finish` uses a repo set up at 1.8.1 with one active 1.x feature and one `Status: done` 1.x feature.
  - `upgrade-plan` lists only the active one in `old_features`.
  - The upgrade exits 2 naming it.
  - After setting it to `Status: done`, the upgrade proceeds.
- [ ] **Step 2:** Run it → FAIL.
- [ ] **Step 3: Implement.**
  - Write the migration, in the shape of `1.7.0-artifact-layout.md`. It must:
    - explain 2.0 in three lines;
    - regenerate the rules;
    - delete the plugin-written files of removed agents, if a repo copied any;
    - point at the release notes.
  - Make `/sdlc:start` and `/sdlc:status` text (Task 7) say the same thing as `old_features`.
- [ ] **Step 4:** Run `tests.test_scaffold`: PASS.
- [ ] **Step 5: Commit** `feat(upgrade): 2.0 waits for 1.x features to finish`.

### Task 4: The trust anchor guards Review at every size

**Requirements:** AC-005, AC-006, Review Focus 2

**Files:**
- Modify: `hooks/trust_anchor.py`
- Test: `tests/test_trust_anchor.py`

**Interfaces:**
- `FIELDS = ("Track", "Risk", "Top model", "Base", "Process")`.
  - `STRICTER` keeps `Track` and `Risk`.
  - A removed or changed `Process:` line is a notice.
- Leaving Stage 5 without a passing full run on the current tree is a notice at every track. Remove:
  - the verifier and ac-checker dispatch evidence;
  - the Lite/Stage-6 and `Prove: skip` exemptions;
  - the M-checker rule.
- The VERDICT check stays. It reads every report under `.sdlc/.work/findings/<feature>/` named `code-reviewer*`, `security*`, `ui-reviewer*`, `qa-tester*` or `pr-test-analyzer*`. A waiver recorded with `state.py deviation` ("waived") still passes.
- The "spec.md changed after Stage 5" notice stays. The S `Repro:` notice goes, since S now has a spec.

- [ ] **Step 1: Write the failing tests.**
  - `test_leaving_review_needs_a_passing_full_run_at_every_size`: for `Track: S`, then `M`, then `L`, advance 4 → 5 → 8 with code changed after the last `verify.py` run, and expect a notice for each. Then with a fresh passing run, no notice.
  - `test_a_review_fail_verdict_blocks_ship_unless_waived`: a `code-reviewer-r1.md` ending `VERDICT: FAIL`; leaving 5 gives a notice. Add a `deviation` with "waived", and there's no notice.
  - Extend the anchored-field test so that removing `Process: 2` is a notice.
- [ ] **Step 2:** Run them → FAIL.
- [ ] **Step 3: Implement** the interfaces above.
- [ ] **Step 4:** Run `tests.test_trust_anchor`. Delete the tests for removed rules: the Lite flow, `Prove: skip`, the verifier, the ac-checker, the M checker and the S repro. Keep `test_hand_edited_verify_record_is_a_notice`, the risk-lowering tests and the baseline test. PASS.
- [ ] **Step 5: Commit** `feat(trust-anchor): Review needs a passing run at every size`.

### Task 5: Every review on opus; freshness and budget for Review

**Requirements:** AC-007, AC-008

**Files:**
- Modify: `hooks/model_router.py`, `hooks/verify_freshness.py`, `hooks/prove_budget.py` (deny messages say "Review"; file name kept, since hooks.json and the host adapters name it)
- Test: `tests/test_model_router.py`, `tests/test_verify_freshness.py`

**Interfaces:**
- `model_router.ALWAYS_TOP = {"code-reviewer", "feature-reviewer", "ui-reviewer", "qa-tester", "pr-test-analyzer", "silent-failure-hunter"}`. The Track-L-only floor goes.
- `verify_freshness`: active in Stage 5 only, at every track. Remove the `Flow: lite` Stage-6 branch.

- [ ] **Step 1: Write the failing tests.**
  - `test_every_review_runs_on_opus_at_every_size`: `ui-reviewer` on `sonnet` with `Track: S` is denied, and on `opus` goes ahead.
  - `test_review_blocks_stale_results_at_every_size`: `Track: S` at Stage 5 with stale results; Stop is blocked.
- [ ] **Step 2:** Run them → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4:** Run both test files. Remove the tests for `m_qa_tester_runs_on_sonnet` and `track_l_floor` and the Lite-flow freshness tests. PASS.
- [ ] **Step 5: Commit** `feat(hooks): every review on opus; freshness in Review at every size`.

### Task 6: Remove the old flow's agents, skills and references

**Requirements:** brainstorm "Decided after the builder check" and "Removed from the flow"

**Files:**
- Delete:
  - `agents/verifier.md`, `agents/ac-checker.md`, `agents/code-architect.md`;
  - the skills `writing-specs`, `clarifying-specs`, `designing-solutions`, `analyzing-consistency`, `executing-plans`, `subagent-driven-development`, `writing-plans`;
  - `skills/orchestrator/references/relay.md` and `templates/design-template.md`.
- Modify:
  - `hooks/role_guard.py` `REVIEWERS` (drop ac-checker, code-architect);
  - `hooks/model_router.py` (verifier gone);
  - `scripts/hosts.py` `RELAY_REPORT_ONLY` (only code-explorer and code-reviewer write reports);
  - `NOTICE.md` (removed files);
  - every skill or agent that names a removed one, found by grep, with the reference moved to what replaces it.
- Test: the full suite.

- [ ] **Step 1:** `grep -rn` each removed name across `skills agents commands hooks scripts templates plugins`. List every hit.
- [ ] **Step 2:** Delete the files, then fix each hit, pointing at the 2.0 reference or removing the line. Keep `sdlc:test-driven-development`, `sdlc:systematic-debugging`, `sdlc:brainstorming`, `sdlc:verification-before-completion`, `sdlc:todo`, `sdlc:managing-knowledge` and `sdlc:hookify`. The model-selection text that lived in subagent-driven-development moves into the orchestrator's SKILL.md (Task 7).
- [ ] **Step 3:** `py -3.10 scripts/hosts.py build`, then the full suite. Fix the tests that referenced deleted files. PASS.
- [ ] **Step 4: Commit** `refactor!: remove the 1.x flow's agents, skills and relay`.

### Task 7: Rewrite the flow (instructions)

**Requirements:** brainstorm goals 1–10 and the agent's calls

**Files:**
- Rewrite:
  - `skills/orchestrator/SKILL.md` (≤ 70 lines; a sizing table; model selection);
  - `references/start.md` (state template with `Process: 2`; 1.x refusal text);
  - `define.md` (intent before code, agent judges, one question at a time via `sdlc:brainstorming`, bug proven first with root cause, S writes all three files without stopping, M/L approval of intent + spec + plan);
  - `build.md` (how the build runs, decided before it and written in plan.md with its reason: inline by default, parts in fresh sessions when it won't fit one context, parallel subagents only for independent parts; builder like plain Claude, red-first via `verify.py`, must-never-break and failure modes, crash windows must-fix, parts via the backlog, one commit per part naming the record);
  - `ship.md` (learn before the final commit, local green, push, watch CI, one fix then ask, stop at the PR);
  - `backlog-slices.md` (parts land together; feature close → Review);
  - `ui-work.md` (unchanged rules; Prove → Review; S writes `## UI mapping` in plan.md).
- Create: `references/review.md` (replaces `prove.md`):
  - the recommendation: security; code low/default/high; UI; advisor where available; none, with the reasons based on the diff;
  - S runs the recommendation, M/L ask, autopilot and headless runs take it;
  - each review once, with high findings fixed test-first and fixing the rule, not the instance;
  - the record's review section.
- Modify: `references/review-brief.md` (the three depth variants and the security brief).
- Rewrite: `templates/intent-template.md`, `spec-template.md`, `plan-template.md` (brainstorm goal 3's sections; an S fills each in a line or two).
- Delete: `references/prove.md`.

- [ ] **Step 1:** Write each file from the brainstorm, in the repo's plain style (short sentences, no process jargon to the user). SKILL.md names the advisor rule: not called during an sdlc change unless the review step recommends it. SKILL.md also states the context rule from the brainstorm: read a file only when the context doesn't already hold it (no re-reads of what this session wrote, loaded or edited; read after /clear, a new session, compaction or in a subagent; ask state.py and verify.py status instead of opening state.md or logs; write each record file once; load each phase reference once).
- [ ] **Step 2:** Self-check against the brainstorm, goal by goal: each goal is said in exactly one reference, and nothing names Prove rounds, the verifier, the ac-checker, the relay, Lite/Full or `Prove: skip`. Check with `grep -rniE "prove round|verifier|ac-checker|relay|flow: lite|prove: skip" skills templates commands agents`. The only hits allowed are 1.x refusal text.
- [ ] **Step 3:** Run `py -3.10 scripts/hosts.py build && py -3.10 scripts/hosts.py check` and `claude plugin validate .`.
- [ ] **Step 4: Commit** `feat!: the 2.0 flow (intent before code, reviews recommended after the build, learn before merge)`.

### Task 8: Docs, ADR, version, release candidate

**Requirements:** CONTRIBUTING stale-docs audit; brainstorm "Done means"

**Files:**
- Create: `docs/adr/0020-sdlc-2-slim-process-core.md` (supersedes the Prove parts of 0012–0019; links the brainstorm).
- Modify:
  - `docs/adr/README.md`, `README.md`, `docs/guidebook.md`, `docs/playbook.md`, `docs/runbook.md`, `docs/prd.md`;
  - the `docs/specs/*.md` rows that name removed parts (each `[enforced]` row points at a test that still exists);
  - `CHANGELOG.md` (a `## 2.0.0` section with a "Before you update" line: finish in-progress features on 1.8.1);
  - the three version fields;
  - `knowledge/index.md` if a doc moves.
- Diagrams: update the `<desc>` text of `docs/diagrams/*.svg`. List the SVGs whose drawing needs relayout in the report rather than redrawing them.

- [ ] **Step 1:** Run the stale-docs audit in CONTRIBUTING.md over every removed name and phrase from Tasks 1–7, and fix each hit.
- [ ] **Step 2:** Run the full suite once on 3.10, `claude plugin validate .` and `claude plugin validate plugins/sdlc-extras`, and `hosts.py check`. All must pass.
- [ ] **Step 3: Smoke on a scratch repo,** using a `claude -p` session with `--plugin-dir` pointing at this worktree:
  1. `/sdlc:setup` on a tiny repo, then `/sdlc:start` with a one-line S fix. Expected: `intent.md`, `spec.md` and `plan.md` are written, there's no stop, and it ends at the branch with a review recommendation reported.
  2. On a repo with a 1.x state file, `/sdlc:start` refuses with the 1.8.1 message.
- [ ] **Step 4: Commit** `docs: sdlc 2.0`. Report to the user. The eval session runs the release candidate against plain Claude as a separate step.

---

## Handoff to Build

- **Decisions:**
  - Stage numbers stay (1, 4, 5, 8), so every hook keeps reading numbers. Stage 5 is renamed Review.
  - `Process: 2` is the only marker between 1.x and 2.0.
  - **Parts reuse the existing backlog** (`backlog.md`, `plan-B<n>.md`, `/sdlc:start B<n>`, autopilot): they already resume from files, land together at feature close, and are tested. This revises the brainstorm's call of "status lines in plan.md": it changes nothing the user decided, and it keeps `/sdlc:start B<n>` and autopilot working unchanged.
- **Rejected:**
  - A frozen copy of the 1.x flow inside 2.0 (the user chose finish-before-updating).
  - Renaming `prove_budget.py` (hooks.json and three host adapters name it).
- **Must not break:**
  - every typed command;
  - the three other hosts;
  - the security gate (ADR 0019);
  - `verify.py`'s red-first record and its tamper-evident copy.
- **Open:** none for the user. The SVG relayout is listed, not done.
