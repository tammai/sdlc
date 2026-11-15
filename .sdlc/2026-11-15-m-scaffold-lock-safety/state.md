# 2026-11-15-m-scaffold-lock-safety
Status: done
Process: 3
Change: .sdlc/2026-11-15-m-scaffold-lock-safety/change.md   (this feature's record for people)
Track: M   (sized up because: scaffold.py, tests and two docs; footprint: 4 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-15
Base: e0ed8b0
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: e0ed8b0 tree 3fc445f9a9c2fc32bf2784ab753cc64af86c6c4f
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [x] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline

## Handoff
- Project scripts/scaffold.py:122 (lock read at __init__, require_lock :131, save :144); main :2350 runs a.fn(Project(a.root), a); cmd_init reads p.lock :160; run-commands saves at the end :822
- doctor.check_repo and hooks/session_status.py call cmd_status directly; both catch exceptions (doctor ValueError, the hook Exception)

## Tasks
1. **Lock file, run-commands re-read, lock shape on read, atomic fallback, shared temp helper** — AC-001 AC-002 AC-003 AC-004 AC-005
   - Files: `scripts/scaffold.py`, `tests/test_stack_blueprints.py`
2. **Docs** — AC-001
   - Files: `CHANGELOG.md`, `docs/specs/01-setup-upgrade-eject.md`

## Public Surface
- none

## Gate log
- 2026-11-15 Stage 1: pass — plan not stopped for approval: low-risk M
- 2026-11-15 Stage 2: pass — verify PASS; suite 599 OK
- 2026-11-15 review: ran code (failure modes: concurrent use, crash mid-write), not asked: low risk
- 2026-11-15 Stage 2: pass — OS-lock rework; suite OK
- 2026-11-15 Stage 2: pass — review cap: mutex and atomic save removed; suite OK
- 2026-11-15 Stage 2: pass — r3 in-passing fixes; verify PASS
- 2026-11-15 Stage 3: pass — r3 PASS; Review recorded

## Deviations
- 2026-11-15 test-change tests/test_stack_blueprints.py test_malformed_lock_is_refused_before_any_write, test_failed_write_without_hard_links_leaves_no_file What: the first calls convention_updates only for a bad conventions (a bad declined now fails Project.lock); the second fails the fallback's rename instead of a second fsync. Why: AC-005 checks the lock on first read; AC-004 replaces the exclusive create with a rename. Effect: same guarantees on the new paths.
- 2026-11-15 test-change tests/test_doctor.py test_gitignore_in_a_git_repo_not_ignoring_warns What: removes .sdlc/.work/.gitignore before checking. Why: the scaffold lock now makes .sdlc/.work ignore itself, so the warning only shows in a repo from before this change. Effect: doctor's check unchanged.
- 2026-11-15 scripts/scaffold.py check_lock scaffold_lock _temp_copy What: module-level helpers (shape check, the lock file, the shared temp write) plus .sdlc/.work/.gitignore written by the lock. Why: one check for every reader (AC-005), the mutex (AC-001-003), R2-10's shared temp write; the gitignore because the lock file made relocate's clean-tree check refuse in repos without setup's ignore line. Effect: none outside scaffold.py except the self-ignoring scratch folder.
- 2026-11-15 AC-002 AC-004 What: AC-002 now reads 'a holder killed mid-command, then the next command runs without waiting' (OS locks have no stale file to take over; test test_killed_holder_lets_the_next_run); AC-004's no-hard-link fallback can leave an empty file if a kill lands between the placeholder and the replace, never a partial one. Why: Review r1 replaced the lock-file design with OS locks (LS-01..04, 12) and the check-then-rename fallback with placeholder-then-replace (LS-05). Effect: Decisions rows and the AC-002 test row rewritten.
- 2026-11-15 review r1 fix scripts/scaffold.py, tests/test_stack_blueprints.py, docs What: OS lock (flock/msvcrt) on a never-deleted file, every wait pass sleeps and checks the deadline; .sdlc gone mid-wait runs unlocked without recreating it (LS-09); a first init takes no lock (LS-08); eject keeps the held lock file and main removes it after release; write_json atomic with a Windows retry (LS-06); check_lock covers every key read (LOCK_SHAPE, LOCK_NESTED, files sha256/template, merged values) and direct indexes became .get (LS-07); contract, commands, migrations, guardrails unlocked (LS-11); kill test asserts the file arrives whole (LS-13); a Python path with a space skips the run-commands test (LS-14); dead variable (LS-15). Why: Review round 1. Effect: AC-002 test replaced.
- 2026-11-15 test-change tests/test_stack_blueprints.py test_waits_for_the_holder test_killed_holder_lets_the_next_run test_killed_fallback_write_leaves_no_partial_file test_failed_write_without_hard_links_leaves_no_file What: holders take the real OS lock (in-process, or a child process killed); the kill test cuts the second rule-text write and asserts a whole file; the failed-write test fails os.replace on the rule only. Why: the OS-lock and placeholder designs (Review r1). Effect: same guarantees on the new mechanism.
- 2026-11-15 review cap scripts/scaffold.py, hooks/session_status.py, tests/test_stack_blueprints.py, tests/test_doctor.py, CHANGELOG.md, docs/specs/01-setup-upgrade-eject.md, .sdlc/2026-11-15-m-scaffold-lock-safety/change.md What: the OS-lock mutex and the atomic write_json removed (LS2-01..03 gone with them); AC-001/AC-002 moved to out of scope; the doctor test change reverted; command_runs items checked (LS2-04); the kill test cuts the second rule-text write in str or bytes, so it fails against the old fallback (LS2-05); the session hook reports an unreadable lock (LS2-10); changelog and spec rewritten (LS2-14). Why: the user's answer at the review cap, 'Drop mutex, ship the rest'. Effect: concurrency stays a ticket; LS2-07/08/09/11/12/13 went with the mutex or are tickets.

## Open questions
-
