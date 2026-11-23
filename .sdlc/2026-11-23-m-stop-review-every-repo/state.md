# 2026-11-23-m-stop-review-every-repo
Status: done
Process: 3
Change: .sdlc/2026-11-23-m-stop-review-every-repo/change.md   (this feature's record for people)
Track: M   (sized up because: —; footprint: 6 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-23
Base: 24f3f68
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: 24f3f68 tree 638a4cc5e9be68a66784c0e8577562319c53a16d
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [x] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline: this session builds it, one part

## Handoff
- Plan and lane C design: .sdlc/.work/stop-repos-plan.md

## Tasks
1. **Other repos' diffs** — AC-001 AC-002 AC-003 AC-004 AC-005
   - Files: `hooks/stop_repos.py`, `tests/test_workbench.py`
2. **Stop handler reaches them** — AC-001 AC-002 AC-003
   - Files: `hooks/security_reminder_hook.py`
3. **Docs** — AC-001
   - Files: `NOTICE.md`, `CHANGELOG.md`, `.sdlc/todo.md`

## Public Surface
- none

## Test lock
- `tests/test_workbench.py` sha256:70e579a0053625f450ab3140a4997924b357a8651e780f976ad08288a01e074d

## Gate log
- 2026-11-23 Stage 1: pass — plan not stopped for approval: low-risk M
- 2026-11-23 review: ran code (diff large: more than 300 added lines), not asked: low risk
- 2026-11-23 Stage 2: pass
- 2026-11-23 Stage 2: pass
- 2026-11-23 Stage 2: pass
- 2026-11-23 Stage 2: pass
- 2026-11-23 Stage 2: pass
- 2026-11-23 Stage 3: pass

## Deviations
- 2026-11-23 other_repos, repo_diff_files, other_repo_diff_files What: new functions of the new hooks/stop_repos.py, not listed as surface in Define. Why: an internal module of the Stop hook, imported only by security_reminder_hook.py and the tests. Effect: none; the code review covers them.
- 2026-11-23 hooks/diffstate.py, stored_path What: consume_stop_state also returns other_reviewed_at; stop_repos gains stored_path. Why: code review r1 CR1-1 and CR1-2 fixes. Effect: a rewake skips other-repo files unchanged since the last review; findings are stored repo-relative.
- 2026-11-23 test-change tests/test_workbench.py What: AC-001 no longer asks for the first repo's folder prefix; the fake API answers with the schema's hasVulnerabilities and can return a finding; three tests added for the review fixes. Why: code review r1 CR1-1 (the first repo keeps its bare names) and CR1-2..5.
- 2026-11-23 test-change tests/test_workbench.py What: AC-001 and AC-002 expect the first repo's files labelled too; the stored-name test expects the label; the diff tests drop the cwd argument; three tests added (same name in two repos, labels and subfolder, commit before the last review, reviewable-source limit). Why: code review r2 CR2-1, CR2-4, CR2-6, CR2-10.
- 2026-11-23 label What: stop_repos.label replaces stored_path and the cwd-relative prefix. Why: code review r2 CR2-1 (one name per file, workbench-relative). Effect: every file of a multi-repo review carries its repo's folder; findings are stored under those names.
- 2026-11-23 test-change tests/test_workbench.py What: names are paths from the session's cwd (AC-001's description, AC-002 expects ../web/b.py), the diff test drops since, three tests added (cwd paths, ranking by repo-relative path, a session in a subfolder through the hooks). Why: code review r3 CR3-1..CR3-8, the simplified design the user chose.
- 2026-11-23 name_prefix, pick, other_repo_files, read_totals What: stop_repos API after round 3 (replaces label, other_repo_diff_files). Why: code review r3, simplified design. Effect: cwd-relative names; the first repo first under the cap; other repos re-diffed from the turn's start.
- 2026-11-23 test-change tests/test_workbench.py What: three tests added (a rewake, the first repo's priority under the cap, turn_touched trimming). Why: code review r4 CR4-2, CR4-6.
- 2026-11-23 CONTRIBUTING.md What: stop_repos.py added to the layout tree and the Original list. Why: code review r4 CR4-7 (stale-docs audit). Effect: docs only.

## Open questions
-
