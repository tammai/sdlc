# 2026-11-16-m-gh-56-ci-test-lock
Status: done
Process: 3
Change: .sdlc/2026-11-16-m-gh-56-ci-test-lock/change.md   (this feature's record for people)
Track: M   (sized up because: —; footprint: 2 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-16
Base: b6bcca6
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: b6bcca6 tree ec3b3dbd7bdc3ada462cf2400b974180b49925bd
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [ ] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline: this session builds it, one part

## Handoff
- templates/project/ci/invariants.py main() loops features at :117; lock lines '- `file` sha256:<hex>' under ## Test lock (scripts/state.py:363)

## Tasks
1. **Lock and test-file checks in invariants.py** — AC-001 AC-002 AC-003
   - Files: `templates/project/ci/invariants.py`, `tests/test_invariants.py`
2. **Docs** — AC-001
   - Files: `CHANGELOG.md`, `docs/specs/04-verification.md`

## Public Surface
- none

## Test lock
- `tests/test_invariants.py` sha256:a9ec2c6d53f84829bc77808a8beb794d7d45cd06f2605dfd67d9718f3fc65b41

## Gate log
- 2026-11-16 Stage 1: pass — plan not stopped for approval: low-risk M
- 2026-11-16 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-16 test-change tests/test_invariants.py What: a workbench case added to test_each_ac_test_file_exists. Why: an app repo's test file isn't in the workbench's checkout; the check must skip it.
- 2026-11-16 templates/project/ci/invariants.py sha256s, app_repos, check_lock, check_test_files, changed_since What: new helpers in the generated CI script. Why: the two P6 checks. Effect: internal to that script.

## Open questions
-
