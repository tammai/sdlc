# 2026-11-24-s-gh-92-s-test-lock
Status: done
Process: 3
Track: S   (footprint: 12 files)
Risk: low
Top model: opus
Base: 968519a
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: 968519a tree 7241e18979fef7ac526e9215d36d2d4466bd69e0
Current: Stage 4 – Ship

## Tasks
1. **Guards config, acceptance and setup** — AC-002 AC-003
   - Files: `hooks/sdlc_scopes.py`, `hooks/trust_anchor.py`, `hooks/session_status.py`, `scripts/scaffold.py`, `commands/setup.md`, `hosts/skills/setup/SKILL.md`, `tests/test_guards.py`
2. **S lock with the guard on** — AC-001
   - Files: `scripts/verify.py`, `tests/test_test_lock.py`, `skills/orchestrator/references/s-track.md`
3. **Docs** — AC-003
   - Files: `docs/adr/0032-opt-in-guards.md`, `docs/adr/README.md`, `docs/wiki/Configuration.md`, `docs/specs/03-scope-and-review.md`, `CHANGELOG.md`, `.sdlc/todo.md`

## Public Surface
- config `guards.s_tests` — AC-003
- command `scaffold.py guard` — AC-003

## Gate log
- 2026-11-24 Stage 1: pass
- 2026-11-24 Stage 2: pass — code review: r1 built-in FAIL (CR1-CR6 fixed), r2 opus PASS (follow-ups fixed)

## Deviations
- 2026-11-24 docs/specs/04-verification.md, docs/wiki/Verification.md, docs/wiki/Where-things-live.md, skills/orchestrator/references/s-track.md, docs/wiki/Limitations.md What: docs that name where the test lock applies, found by the stale-docs audit; spec 03 named in the plan holds no test-lock line. Why: they said M and L only. Effect: docs only. Sizing: S by its code (5 files), the rest is docs.
- 2026-11-24 internal helpers What: guard_name, _guards, guards_configured, guards_committed, guards_accepted, guards (hooks/sdlc_scopes.py), cmd_guard (scripts/scaffold.py). Why: the guard config read like mode, skip and approval. Effect: module-internal; the public surface is the config key and the scaffold command.
- 2026-11-24 code review r1 fixes What: scripts/verify.py red_at also re-reds a lock already written (CR1), scripts/spec_lock.py docstring, hooks/plan_approval.py reads asked questions at the project root and matches a typed name case-insensitively without a trailing stop (CR2, CR3), sdlc_scopes/trust_anchor skip guard names this version doesn't know (CR4), tests run hooks with sys.executable and PYTHONUTF8 (CR6), tests/test_approval.py. Why: code review r1. Effect: CR2 has no test of its own (a workbench app-repo session); AC-002's tests cover the unchanged path.
- 2026-11-24 code review r2 fixes What: hooks/trust_anchor.py keeps guard names it doesn't know in the record and compares only its own (R2-2, tested in tests/test_guards.py with the CR4 case), hooks/plan_approval.py matches an exact typed name first and a case-insensitive one only when unique (R2-4), and four docs and comments that said S never locks (R2-5). Why: code review r2. Effect: the workbench case of CR2 is ticketed in .sdlc/todo.md.
- 2026-11-24 output/ What: untracked files (output/medal-lineart/*.svg) another session wrote into this shared worktree during the build. Why: not this change's; left untouched. Effect: none; kept out of the commit.

## Open questions
-
