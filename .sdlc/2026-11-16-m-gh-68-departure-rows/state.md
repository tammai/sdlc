# 2026-11-16-m-gh-68-departure-rows
Status: done
Process: 3
Change: .sdlc/2026-11-16-m-gh-68-departure-rows/change.md   (this feature's record for people)
Track: M   (sized up because: —; footprint: 6 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-16
Base: b6bcca6
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: b6bcca6 tree a18a26329c602e1c36af8022291879d77f33698c
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [ ] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline: this session builds it, one part

## Handoff
- acceptance_map scripts/verify.py:85; full() rows by AC :434; red_one :835; red lock loop :810; red_at row pick :566; bundle_check :646
- contracts C5 parser: scripts/contracts/v1/contracts.py parse_yaml :331, check_departures :966

## Tasks
1. **Departure rows in verify.py** — AC-001 AC-002 AC-003
   - Files: `scripts/verify.py`, `tests/test_recorded_tests.py`
2. **Docs** — AC-004
   - Files: `skills/orchestrator/references/flow.md`, `docs/wiki/Verification.md`, `docs/specs/04-verification.md`, `CHANGELOG.md`

## Public Surface
- none

## Test lock
- `tests/test_recorded_tests.py` sha256:22462bfb3f2ff37c74823e2fb83722b16b392115303b6f4209a62c08862fa237

## Gate log
- 2026-11-16 Stage 1: pass — plan not stopped for approval: low-risk M
- 2026-11-16 Stage 2: pass — no review: no trigger fired

## Deviations
- 2026-11-16 test-change tests/test_recorded_tests.py What: the fixture helper rows() renamed table(). Why: it clashed with the base fixture's self.rows attribute, so the red run failed on a TypeError rather than the missing feature.
- 2026-11-16 scripts/verify.py contracts, departure_check, test_rows What: new module-level helpers. Why: the departure row's check and the rows that name a test, shared by full, red, red --at. Effect: internal to the plugin's scripts.

## Open questions
-
