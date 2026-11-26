# 2026-11-26-s-ci-baseline-path
Status: done
Process: 3
Track: S   (footprint: 2 files)
Risk: high
Top model: opus
Base: 1116410
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: 1116410 tree 339a1569e2f9d068979821376d052ffc3a862988
Current: Stage 4 – Ship

## Tasks
1. **CI reads the baseline path as Ship does** — AC-001 AC-002 AC-003 AC-004
   - Files: `templates/project/ci/invariants.py`, `tests/test_invariants.py`
2. **Ship refuses a linked baseline by name** — AC-005
   - Files: `scripts/ship.py`, `tests/test_ship.py`

## Public Surface
- none

## Gate log
- 2026-11-26 Stage 1: pass
- 2026-11-27 Stage 2: pass — security review: r1 FAIL fixed, r2 PASS

## Deviations
- 2026-11-26 Risk What: raised from low to high after the red step. Why: config's baseline (untrusted repo config) reaches a file path. Effect: a security review runs.
- 2026-11-26 tests/test_invariants.py What: AC-004's test gained the default-path link case after its red step. Why: the default path skipped the link check Ship runs on every path. Effect: invariants.py checks the default path too.
- 2026-11-26 Tests What: run on Python 3.9.6, not 3.10. Why: no Python 3.10 on this machine; 3.9 is the floor. Effect: none expected.
- 2026-11-26 baseline_path What: a new function in templates/project/ci/invariants.py, not in the Public Surface. Why: the one resolver both CI checks call; the template can't import ship.py. Effect: none outside invariants.py.
- 2026-11-27 tests/test_ship.py What: test_a_baseline_path_out_of_the_repo_is_never_read now expects 'leaves the repo: not read'. Why: security review r1 S2: an absolute path is refused by its text before realpath runs, so the old link message no longer fits. Effect: a clearer refusal.
- 2026-11-27 Review fixes What: security review r1 S1-S5 fixed test first in invariants.py and ship.py (tracked-regular-file rule, text-first absolute paths, config() as an object, FIFO refused). Why: each a bug in code this change touched. Effect: four new tests in test_invariants.py, a folder-link case in AC-005's test.
- 2026-11-27 Review r2 fixes What: L1 (folders on the way checked for links before any call that follows them, CI and Ship) and L2 (the waiver runs where git isn't installed) fixed; L3 ticketed in todo. Why: low bugs in touched code, fixed without another round. Effect: one new test; the folder-link case's CI message is now 'goes through a link'.

## Open questions
-
