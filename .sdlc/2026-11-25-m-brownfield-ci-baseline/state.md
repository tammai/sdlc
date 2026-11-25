# 2026-11-25-m-brownfield-ci-baseline
Status: done
Process: 3
Change: .sdlc/2026-11-25-m-brownfield-ci-baseline/change.md   (this feature's record for people)
Track: M   (sized up because: —; footprint: 5 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-25
Base: 644b83b
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: 644b83b tree 09203367187717633e049217761f6f71213112b5
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [ ] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline: this session builds it, one part

## Handoff
- generate_ci: scripts/scaffold.py:1643; ship.py's matching to port: scripts/ship.py failing_tests/leaves/baseline_match

## Tasks
1. **The log check in invariants.py** — AC-001
   - Files: `templates/project/ci/invariants.py`
2. **Wrap the generated test step** — AC-002 AC-003
   - Files: `scripts/scaffold.py`
3. **Tests, docs and todo** — AC-001 AC-002 AC-003
   - Files: `tests/test_ci_baseline.py`, `CHANGELOG.md`, `docs/wiki/Limitations.md`, `.sdlc/todo.md`

## Public Surface
- none

## Test lock
- `tests/test_ci_baseline.py` sha256:5b8735b841739af71264bd1b29ce038035832df5bbbf971ce4b22f15529238b6

## Gate log
- 2026-11-25 Stage 1: pass — plan not stopped for approval: low-risk M
- 2026-11-25 review: ran code (a new --baseline-tests flag in the generated invariants.py and a generated CI shell step), self-chosen: low risk
- 2026-11-25 Stage 2: pass
- 2026-11-25 Stage 3: fail — code review r1: R1-1 R1-2 R1-3 R1-5 R1-6 high
- 2026-11-25 Stage 2: pass
- 2026-11-25 Stage 3: fail — code review r2: R2-1..R2-4 high; user chose ship.py's matching rule in CI
- 2026-11-25 Stage 2: pass
- 2026-11-25 Stage 3: fail — code review r3: R3-1 R3-2 high; user chose a fix round and a closing check
- 2026-11-25 Stage 2: pass
- 2026-11-25 Stage 3: fail — code review r4: R4-1 high (docs); user chose fix and ship, waiving another round
- 2026-11-25 Stage 2: pass — code review r4 waived by the user after its fixes; full suite 951 OK on 3.10

## Deviations
- 2026-11-25 test-change tests/test_ci_baseline.py What: the fixture's baseline row names its package (root), as setup writes it, not the template's placeholder dash, which every reader skips. Why: the red run failed for that, not for the missing feature.
- 2026-11-25 templates/project/ci/invariants.py check_test_log, failing_tests, leaves What: the log check and a stdlib copy of ship.py's failing_tests and leaves. Why: AC-001; the generated script imports nothing from the plugin. Effect: invariants.py gains --baseline-tests; keep the two copies of the runner patterns in step.
- 2026-11-25 AC-003 What: moved to Must never break, its test kept. Why: it states behaviour that doesn't change, so no red run can exist for it. Effect: two ACs.
- 2026-11-25 scripts/scaffold.py baselined_tests, BASELINE_TEST_STEP What: whether the baseline lists a failing test, and the wrapped step's script. Why: AC-002. Effect: internal to generate_ci.
- 2026-11-25 Base What: moved from 5bafdf9 to 644b83b. Why: PR #143 merged into main under this feature's uncommitted work. Effect: drift and the test lock compare against the merge.
- 2026-11-25 test-change tests/test_ci_baseline.py What: adds one test per code review r1 finding class (compound command, namesake in another file, coloured log, multi-line step, config baseline path and --json). Why: review fixes start with a failing test.
- 2026-11-25 templates/project/ci/invariants.py same_test What: replaces leaves(): a listed test matches only the same test in the same file, a unittest dotted name mapped from the file. Why: R1-3. Effect: stricter than ship.py --waive-baseline's leaves; docs/wiki/Limitations.md, CHANGELOG.md updated.
- 2026-11-25 test-change tests/test_ci_baseline.py What: the R1-3 namesake test becomes test_ci_matches_names_as_ship_does (go parent line, file › name rows, unittest names), and test_a_log_that_isnt_utf8_is_read is added. Why: code review r2; the user chose ship.py's matching rule for CI.
- 2026-11-25 templates/project/ci/invariants.py leaves What: same_test reverted to ship.py's leaves(). Why: R2-1..R2-3, the user's call after round 2. Effect: namesakes match loosely in CI as in Ship; documented in Limitations.
- 2026-11-25 test-change tests/test_ci_baseline.py What: adds R3-1 (a repeated go name) and R3-2 (a cp1252 baseline: no crash, and the new codes asserted). Why: code review r3.
- 2026-11-25 waived round 4: R4-1 — fixed (the wiki command now has --class seeded, read back) with R4-3 and the nits; the user chose to ship without another review round.
- 2026-11-25 test-change tests/test_ci_baseline.py What: config.json read through a closing helper; AC-001's test also asserts baseline_unmatched's --json code. Why: code review r4 (R4-5, R4-7).
- 2026-11-25 templates/project/ci/invariants.py read What: takes tolerant=True for the baseline only. Why: R3-2 and R4-3: a hand-saved baseline may not be UTF-8, the record files stay strict. Effect: the other checks read as before.

## Open questions
-
