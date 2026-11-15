# 2026-11-15-m-lock-merge-and-tickets
Status: done
Process: 3
Change: .sdlc/2026-11-15-m-lock-merge-and-tickets/change.md   (this feature's record for people)
Track: M   (sized up because: scaffold.py, the session hook, tests and two docs; footprint: 5 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-15
Base: 13d3fab
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: 13d3fab tree 80d1e7f34137790c08de897655b27b0fb653aa08
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [x] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline

## Handoff
- Project scripts/scaffold.py:170 (lock property, save :196); eject_plan :2213 and cmd_eject :2235 (os.remove per plan path, dir tidy loop); run-commands save :868; _temp_copy and _publish_new near :1460; cmd_conventions lexists refusal

## Tasks
1. **Merge at save, removed lock, path checks, eject outside, empty placeholder, config and null checks, temp sweep** — AC-001 AC-002 AC-003 AC-004 AC-005 AC-006
   - Files: `scripts/scaffold.py`, `hooks/session_status.py`, `tests/test_stack_blueprints.py`
2. **Docs** — AC-001
   - Files: `CHANGELOG.md`, `docs/specs/01-setup-upgrade-eject.md`

## Public Surface
- none

## Gate log
- 2026-11-15 Stage 1: pass — plan not stopped for approval: low-risk M
- 2026-11-15 Stage 2: pass — verify PASS; suite 603 OK
- 2026-11-15 review: ran code (failure modes: concurrent use, crash mid-write, untrusted paths), not asked: low risk
- 2026-11-15 Stage 2: pass — r1 fixes; suite 604 OK
- 2026-11-15 Stage 2: pass — targeted round; suite 604 OK
- 2026-11-15 Stage 2: pass — r3 mediums fixed; suite 604 OK
- 2026-11-15 Stage 3: pass — r3 PASS; Review recorded

## Deviations
- 2026-11-15 scripts/scaffold.py merge3 merged_lock lock_exists config _ABSENT What: module and Project helpers behind the merge, the null-lock check and the config check; the lock setter checks a new lock like any read (init's first save writes files and declined as it did in PR #58) but takes no merge base from it. Why: AC-001, AC-005 and the must-never-break on the lock format. Effect: none outside scaffold.py.
- 2026-11-15 test-change tests/test_stack_blueprints.py test_run_commands_keeps_a_concurrent_change What: its helper script uses setdefault('declined', []). Why: it assumed the key on disk; it crashed (KeyError) when a lock had none, so the test checked nothing then. Effect: the test now proves the merge.
- 2026-11-15 CHANGELOG.md docs/specs/01-setup-upgrade-eject.md What: the Unreleased lock entry and SET-FR-058 describe the merge, the path checks and eject's outside list. Why: the stale-docs audit. Effect: docs only.
- 2026-11-15 review r1 fix scripts/scaffold.py merge_into write_json _write_atomic TEMP_PREFIX eject_plan cmd_init, tests/test_stack_blueprints.py, CHANGELOG.md, docs/specs/01-setup-upgrade-eject.md What: the merge applies the other command's changes into this command's own objects in place (LM-01) and starts a key both added from empty (LM-02); scaffold's temp files are .sdlc-tmp-* and only those are swept (LM-05); config.json written only when changed (LM-03, LM-08); write_json atomic, keeping the file's mode and writing through links, with a Windows retry (LM-04); a lock broken meanwhile raises instead of being overwritten (LM-07); eject doesn't read outside files (LM-09); init --force restarts over a non-object config (LM-11). Why: Review round 1. Effect: tests extended; one new test (save keeps mode and links).
- 2026-11-15 test-change tests/test_stack_blueprints.py test_stale_temp_files_are_swept What: names scaffold's temp files .sdlc-tmp-* and adds a user's .tmp-notes that must survive. Why: LM-05 narrowed the sweep to scaffold's own prefix. Effect: the user's file is now proven kept.
- 2026-11-15 review r2 fix scripts/scaffold.py save merged_lock merge_into cmd_init write_json _temp_copy cmd_run_commands, tests/test_stack_blueprints.py, CHANGELOG.md What: the lock is written only when this command set it or read and changed it (LM2-03); plain init refuses a non-object config (LM2-04); the merge stops at whole entries below the lock's sections (LM2-10); the merge base moves only after a successful write (LM2-07); run-commands keeps results on OSError too (LM2-05); a read-only target is refused before any temp file (LM2-02); _temp_copy's close can't mask the error (LM2-06); docstring (LM2-15). Why: the user's answer at the review cap, one more targeted round. Effect: tests extended.
- 2026-11-15 review r3 fix scripts/scaffold.py merge_into LOCK_RECORDS _temp_copy, tests/test_stack_blueprints.py What: only entries of files, conventions and command_runs merge whole; every other section (setup.pending, migrations.skipped) merges key by key (LM3-02, test extended); _temp_copy's cleanup can't mask the original error (LM3-06). Why: Review round 3 mediums and lows, fixed without another round. Effect: closed by verify.
- 2026-11-15 AC-006 What: the sweep removes scaffold's own temp files (.sdlc-tmp-*), not every .tmp- file as AC-006's wording says; old .tmp- leftovers from earlier versions stay. Why: Review r1 LM-05: a user's own .tmp- file at the repo root was deleted. Effect: AC-006's test names .sdlc-tmp- and proves a user's .tmp-notes is kept.

## Open questions
-
