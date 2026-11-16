# 2026-11-16-m-gh-56-verify-record-holds
Status: done
Process: 3
Change: .sdlc/2026-11-16-m-gh-56-verify-record-holds/change.md   (this feature's record for people)
Track: M   (sized up because: —; footprint: 13 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-16
Base: 0e774d2
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: 0e774d2 tree 24b9da52809e64f5e2bf843cc3729a7673a3e506
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [ ] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline: this session builds it, one part

## Handoff
- full(): AC rows exit-0 path scripts/verify.py:448; run() truncates output to 2000 chars at :209
- ship.verified() waiver scripts/ship.py:96; baseline_failures :83
- red() lock only when spec_backed_repo scripts/verify.py:787; red_at refuses standalone :541; full() lock check :454

## Tasks
1. **Zero tests is did not run** — AC-001
   - Files: `scripts/verify.py`, `tests/test_verify.py`
2. **Waive only listed failures** — AC-002 AC-003 AC-004 AC-005
   - Files: `scripts/ship.py`, `scripts/verify.py`, `tests/test_ship.py`
3. **Test lock on M and L everywhere** — AC-006 AC-007 AC-008
   - Files: `scripts/verify.py`, `scripts/spec_lock.py`, `tests/test_test_lock.py`
4. **PRD, spec, wiki, flow and changelog** — AC-009
   - Files: `docs/prd.md`, `docs/specs/04-verification.md`, `CHANGELOG.md`

## Public Surface
- none

## Gate log
- 2026-11-16 Stage 1: pass — plan not stopped for approval: low-risk M
- 2026-11-16 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-16 scripts/ship.py failing_tests, leaves, baseline_match What: new module-level helpers for the baseline waiver. Why: ship.verified needs them; tests import failing_tests. Effect: internal to the plugin's scripts, not a public API.
- 2026-11-16 scripts/verify.py locks_tests, run What: locks_tests added; run gains an optional tail argument (default 2000, as before). Why: P3's track check is shared by red, red --at; P2 keeps the test step's whole output. Effect: internal; existing callers unchanged.
- 2026-11-16 tests/test_spec_backed_mode.py What: the standalone red --at refusal's expected wording updated. Why: the message now names M and L. Effect: same behaviour checked (no Track: locks nothing).

## Open questions
-
