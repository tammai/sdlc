# 2026-11-15-m-convention-hardening
Status: done
Process: 3
Change: .sdlc/2026-11-15-m-convention-hardening/change.md   (this feature's record for people)
Track: M   (sized up because: a few files: scaffold.py, tests and five docs; footprint: 8 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-15
Base: be88189
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: be88189 tree 773fbb82c0762d8c442e03f2aa9140df13cb6ea7
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [x] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline

## Handoff
- cmd_conventions scripts/scaffold.py:626; require_lock :131; _write_atomic :1352; main maps ValueError to error JSON exit 1 :2359
- stacks.md: the one-deployable API lives in backend/ (stacks.md:70,133)

## Tasks
1. **Lock shape, link refusal, lock-first exclusive publish, root check, --one-deployable** — AC-001 AC-002 AC-003 AC-004 AC-005 AC-006
   - Files: `scripts/scaffold.py`, `tests/test_stack_blueprints.py`
2. **Docs** — AC-007
   - Files: `skills/project-constitution/references/stack-principles.md`, `skills/setting-up-projects/references/upgrade.md`, `skills/orchestrator/references/flow.md`, `skills/orchestrator/references/s-track.md`, `CHANGELOG.md`, `docs/specs/01-setup-upgrade-eject.md`

## Public Surface
- command `scaffold.py conventions --one-deployable` — AC-006

## Gate log
- 2026-11-15 Stage 1: pass — plan not stopped for approval: low-risk M
- 2026-11-15 Stage 2: pass — verify PASS; full suite 592 OK
- 2026-11-15 review: ran code (Public Surface: --one-deployable), not asked: low risk
- 2026-11-15 Stage 2: pass — r1 fixes; suite 594 OK
- 2026-11-15 Stage 2: pass — r2 fixes; suite 594 OK
- 2026-11-15 Stage 3: pass — r2 PASS; Review recorded; one recurring defect added

## Deviations
- 2026-11-15 test-change tests/test_stack_blueprints.py test_malformed_lock_is_refused_before_any_write What: a malformed declined now expects require_lock's error JSON (exit 1) instead of a refusal (exit 2). Why: AC-004 moves the declined check into require_lock for every command. Effect: same guarantee, nothing written; different exit code.
- 2026-11-15 scripts/scaffold.py convention_text relative_root _publish_new What: convention_text takes backend_only; relative_root is the shared package-path check (config and the lock's root); _publish_new publishes without overwriting. Why: one check on every path (AC-005), the --one-deployable filter (AC-006), the exclusive publish (AC-002). Effect: none outside scaffold.py; the public surface is the command's flag.
- 2026-11-15 AC-006 --one-deployable What: drops the template's src/ globs (and refuses a template with no backend/ globs) instead of keeping only backend/ ones; AC-006's wording above Review stays as written. Why: Review r1 CR-04: node schema's drizzle/** and drizzle.config.ts sit at the app root, not the web app's. Effect: node layers still renders backend/** only; schema keeps its root-level globs.
- 2026-11-15 review r1 fix scripts/scaffold.py, tests/test_stack_blueprints.py, skills/orchestrator/references/flow.md, skills/orchestrator/references/s-track.md, CHANGELOG.md, docs/specs/01-setup-upgrade-eject.md What: null root refused (CR-02), another-drive link refused (CR-07), race rollback restores the earlier entry (CR-01), a bad one_deployable entry is one item's error (CR-03), fallback create removed on failure (CR-06), require_lock sets the empty value (CR-08), convention_lock's dead declined check dropped (CR-10), a.one_deployable (CR-11), flow.md names node for a one-deployable API (CR-09), changelog scope (CR-05), spec trace (CR-12), test matrices cut to one bad root plus null (CR-13). Why: Review round 1. Effect: two new tests, three extended.
- 2026-11-15 review r2 fix scripts/scaffold.py, tests/test_stack_blueprints.py, CHANGELOG.md, skills/setting-up-projects/references/upgrade.md What: any failure after the lock save rolls the lock back (R2-04, test extended); --one-deployable refused with --seen (R2-14); rule files 0644 on both publish paths (R2-07); changelog names design too (R2-02); upgrade.md's third error source (R2-08); a test line rewrapped (R2-12). R2-01 moved to tickets after the report said fixed: a concurrent writer's lock entry is already lost at the other's first save, so only a lock file can fix it. Why: Review round 2. Effect: closed by verify, no round 3.

## Open questions
-
