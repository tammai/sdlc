# 2026-11-05-s-doctor-knowledge-links-with-spaces
Status: done
Process: 3
Change: .sdlc/2026-11-05-s-doctor-knowledge-links-with-spaces/change.md   (this feature's record for people)
Track: S   (footprint: 2 files)
Risk: low   (read-only health check; no auth, secrets, PII or public API)
Top model: opus
Commands: test: `python3 -m unittest discover -s tests -t tests`
Started: 2026-11-05
Base: 58a2c04
Owner: tam.mai@bigin.vn
Tool: claude-code
Verified: 1001051 tree f1944746b98de89e58db6e7e5a9a23ecd9ed8492
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [ ] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## Tasks
1. **Parse `<…>` and %-encoded knowledge index links** — AC-001, AC-002
   - Files: `scripts/doctor.py`, `tests/test_doctor.py`, `CHANGELOG.md`, `docs/specs/08-health-and-status.md` (stale-docs audit: no other doc names the link pattern)

## Public Surface
- none

## Gate log
- 2026-11-05 Stage 1: pass
- 2026-11-05 Stage 2: open — code and test written; not run (see Deviations)
- 2026-11-05 Stage 2: pass — red recorded for AC-001/AC-002 against the base `doctor.py` (exit 1); `verify.py` PASS; full suite 403 run, 397 pass, 6 env failures (`jq` missing, `test_ralph_stop`), 5 skipped
- 2026-11-05 Stage 2: pass — S, low risk; no review trigger fired

## Deviations
- 2026-11-05 Whole run What: no Python could run in this session (`python`, `py`, the plugin's `brief.py`/`state.py`/`verify.py` all needed a permission nobody could grant in the unattended run). Why: permission mode. Effect: this state file was written by hand, not by `state.py new`; the failing test was not watched to fail and the suite, `verify.py` and `ship.py` have not run. Next session: run `py -3.10 -m unittest discover -s tests -t tests`, then `verify.py`, then ship.
- 2026-11-05 Resume What: Python 3.10 isn't installed on this runner (`py -3.10` exits 103, "No suitable Python runtime found"), so the suite and the AC run commands use `python3` (3.15) instead of the CLAUDE.md 3.10 run. Why: no 3.10 available. Effect: the cp1252/3.9-syntax guard that the 3.10 run gives was not exercised; the change adds no new syntax and reads files as UTF-8 explicitly, as before.
- 2026-11-05 Suite What: 6 tests in `tests/test_ralph_stop.py` fail with `jq: command not found` (exit 127 from `plugins/sdlc-extras/hooks/stop-hook.sh`). Why: `jq` isn't installed on this runner; the tests don't touch `doctor.py`. Effect: none on this change; same failures without it.
- 2026-11-05 scripts/doctor.py What: adds a module-level helper `knowledge_links(text)`. Why: keeps the link parsing testable and out of `check_repo()`. Effect: internal to `doctor.py`, a script not imported by other code; no public surface.
- 2026-11-05 Branch What: work is on `tohe/je9fb8368cd401684`, not a branch named after the feature. Why: the tohe daemon owns the branch. Effect: none.
- 2026-11-05 Ship What: not pushed, no PR. Why: `git push -u origin HEAD` failed: origin `C:\ProgramData\tohe\data\git\tammai\sdlc.git` "does not appear to be a git repository" from this session. Effect: the work is committed on `tohe/je9fb8368cd401684`; push and PR are left to the tohe daemon or a person.
- 2026-11-05 Owner What: `git config user.email` is unset here; Owner is the session user's email. Effect: none.

## Open questions
-
