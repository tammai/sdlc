# 2026-11-22-m-watch-guard-reads
Status: done
Process: 3
Change: .sdlc/2026-11-22-m-watch-guard-reads/change.md   (this feature's record for people)
Track: M   (sized up because: —; footprint: 3 files)
Risk: high   (narrows a guard against untrusted command text)
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-22
Base: 82430d9
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: 82430d9 tree 94a422d39e293d95b4703f3551aee47044a5b030
Current: Stage 3 – Review

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [ ] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline: this session builds it, one part

## Handoff
- read_only_problem's token check: hooks/role_guard.py:617; lex() splits simple commands and substitutions: hooks/role_guard.py:208
- tests: tests/test_workbench.py ReadOnlyBackstop, pre_hook() runs pretooluse.py

## Tasks
1. **Reader allowlist for watch names** — AC-001
   - Files: `hooks/role_guard.py`, `tests/test_workbench.py`
2. **Spec line** — AC-001
   - Files: `docs/specs/06-guardrails-and-conventions.md`

## Public Surface
- none

## Test lock
- `tests/test_workbench.py` sha256:f3f5c72e901174529669bc7c3eed481521090dce71387e56b593a969a55016f4

## Gate log
- 2026-11-22 Stage 1: pass — change file approved by the user (high-risk M)
- 2026-11-22 Stage 2: pass
- 2026-11-22 review: ran security and code (Risk: high), chosen by the user

## Deviations
- 2026-11-22 setup What: the repo isn't set up for sdlc (the plugin's own repo). Why: as earlier features here. Effect: the full suite runs by hand on Python 3.10.
- 2026-11-22 hooks/role_guard.py names_watch, _reads_only, watch_problem, WATCH_READERS, FIND_ACTIONS, GIT_READS; hooks/read_only_watch.py docstring What: module helpers behind the reader allowlist; the watch's docstring restates the narrowed rule. Why: AC-001 and the must-never-break line. Effect: internal to the hooks; no public surface.
- 2026-11-22 test-change tests/test_workbench.py What: more cases in both tests (git commit -am, cd then grep, a here-doc before a read; xargs rm, a substituted program, a here-doc before rm, --output, rg --pre, git grep -O, sudo). Why: three bugs found in self-review before the reviews. Effect: same AC.
- 2026-11-22 hooks/role_guard.py hooks/read_only_watch.py docs/specs/06-guardrails-and-conventions.md tests/test_workbench.py What: the narrowing is dropped and the three files are back at Base; AC-001's test is removed; the deny test stays. Why: both reviews failed with 9 high bypasses and the change breaks .claude/rules/hooks.md; the user chose to drop it. Effect: no code change ships, only the regression test, the record and the todos.

## Open questions
-
