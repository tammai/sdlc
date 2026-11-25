# 2026-11-25-m-approval-hardening
Status: done
Process: 3
Change: .sdlc/2026-11-25-m-approval-hardening/change.md   (this feature's record for people)
Track: M   (sized up because: —; footprint: 6 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-25
Base: 455d245
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: 455d245 tree 46bba124a9763bd3b979f8a2d9ea0882b5912485
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [x] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline: this session builds it, one part

## Handoff
- approval check: scripts/state.py plan_approval_by (~335); store: hooks/plan_approval.py; shell/file write matcher: hooks/role_guard.py written() (754)

## Tasks
1. **Created track floor and re-creation reset** — AC-001 AC-003
   - Files: `hooks/plan_approval.py`, `scripts/state.py`
2. **Guard the answer records** — AC-002
   - Files: `hooks/role_guard.py`, `hooks/pretooluse.py`
3. **Record questions when the gate root has the feature** — AC-004
   - Files: `hooks/user_answer.py`
4. **Report from the session's gate** — AC-005
   - Files: `scripts/scaffold.py`
5. **Tests, docs and todo** — AC-001 AC-002 AC-003 AC-004 AC-005
   - Files: `tests/test_approval.py`, `docs/wiki/Limitations.md`, `docs/adr/0031-approval-policy.md`, `CHANGELOG.md`, `.sdlc/todo.md`

## Public Surface
- none

## Test lock
- `tests/test_approval.py` sha256:88d4b56814c7b269076deebc006c25e846a02642957362ed0e32b9b576aa3d93

## Gate log
- 2026-11-25 Stage 1: pass — plan not stopped for approval: low-risk M
- 2026-11-25 Stage 2: pass
- 2026-11-25 review: ran code (diff over 5 source files), not asked: low risk; full suite 911 OK on 3.10
- 2026-11-25 Stage 3: fail — code review r1: H1 H2 M1-M4 L1
- 2026-11-25 Stage 2: pass
- 2026-11-25 Stage 3: fail — code review r2: R2-1..R2-5 high; user chose one more fix round
- 2026-11-25 Stage 2: pass
- 2026-11-25 Stage 3: fail — code review r3: R3-1..R3-4 high; user chose one more full fix round
- 2026-11-25 Stage 2: pass
- 2026-11-25 Stage 3: fail — code review r4: R4-1..R4-4 high; user chose to drop the record guard (AC-002) and fix R4-1, R4-3, R4-6
- 2026-11-25 Stage 2: pass
- 2026-11-25 Stage 3: fail — code review r5: R5-1..R5-4 high; user chose a fix round and a closing check
- 2026-11-25 Stage 2: pass
- 2026-11-25 Stage 3: fail — code review r6: R6-1..R6-4 high; user chose to cut back to the core (3.16 keys and typed approve)
- 2026-11-25 Stage 2: pass
- 2026-11-25 Stage 3: pass — code review r7 PASS; fixing its low bugs R7-1 R7-2 R7-4 in passing
- 2026-11-25 Stage 2: pass — r7 low bugs fixed; full suite 933 OK on 3.10
- 2026-11-25 Stage 3: pass — code review round 7 PASS (rounds 3-7 allowed by the user)

## Deviations
- 2026-11-25 test-change tests/test_approval.py What: AC-002's test also checks guarded.json. Why: the guarded-changes Allow record is the same class as approvals.json (a record of the user's answer that lifts a gate).
- 2026-11-25 hooks/role_guard.py answer_record_problem What: new helper for the answer-record guard. Why: AC-002, called from pretooluse.py. Effect: internal to the hooks, no public surface.
- 2026-11-25 hooks/plan_approval.py created_track, started What: new helpers for the created track and the re-creation reset. Why: AC-001, AC-003, called from state.py. Effect: internal, no public surface.
- 2026-11-25 scripts/scaffold.py report_gate What: one resolver for every config report. Why: AC-005; gating_report already had this logic, now shared. Effect: internal.
- 2026-11-25 test-change tests/test_approval.py What: adds ApprovalHardeningReviewTest (one test per code review r1 finding class: H1 H2 M1-M4 L1); the AC tests are unchanged. Why: review fixes start with a failing test.
- 2026-11-25 test-change tests/test_approval.py What: helpers moved into a HardeningHelpers mixin so the round-1 tests stop re-running the AC tests (R2-7); the junction test removes its link before its folder (R2-8); adds ApprovalHardeningRound2Test (R2-1..R2-5). The AC tests' bodies are unchanged. Why: code review r2.
- 2026-11-25 hooks/plan_approval.py raised, Namesake What: new helper and exception. Why: R2-3, R2-4. Effect: internal.
- 2026-11-25 test-change tests/test_approval.py What: R2-4's test now checks that namesakes keep their own approval instead of expecting a refusal; ApprovalHardeningRound3Test added. Why: code review r3 moved the floor into the state file and keyed approvals by repo. The round 3 tests were written after the redesign, so their red step is the AC rerun at Base, not each one.
- 2026-11-25 scripts/state.py, hooks/plan_approval.py, hosts/hook.py, skills/orchestrator/references/flow.md, docs/wiki/Where-things-live.md What: Approval floor line in the state file (state.py approval_floor, with_floor, approval_key); plan_approval keyed by repo (key()), created_track/raised/Namesake removed; hosts/hook.py sets SDLC_HOST_HOOK for its scripts. Why: code review r3. Effect: new optional state header line; no Process bump since no existing field changes meaning.
- 2026-11-25 hooks/plan_approval.py approved, forget, waiting What: approved/forget take the store key instead of the feature name (waiting only moved). Why: code review r3, namesakes keyed by repo. Effect: internal to plan_approval.py and state.py.
- 2026-11-25 AC-002 removed, with its guard: hooks/role_guard.py, hooks/pretooluse.py, hosts/hook.py reverted to Base. What: the answer-record guard and its tests (AC-002, H1, M4, R2-1, R2-5, R3-2, R3-3) are gone. Why: the user chose to drop it after review round 4. Effect: the records stay agent-writable as in 3.16; Limitations and ADR 0031 say so.
- 2026-11-25 test-change tests/test_approval.py What: guard tests removed; ApprovalHardeningRound4Test added (R4-1, R4-3, R4-6); R3-1's test now expects set Track S below the floor to be refused (a downsize from the floor needs approval). Why: code review r4.
- 2026-11-25 task 2 (Guard the answer records) What: dropped with AC-002. Why: the user's call after review round 4. Effect: hooks/role_guard.py and hooks/pretooluse.py unchanged from Base.
- 2026-11-25 hooks/plan_approval.py pick, scripts/state.py set_floor What: new helpers. Why: R4-3 (a key or bare name picks the waiting feature) and R4-6 (an approved downsize lowers the floor). Effect: internal.
- 2026-11-25 test-change tests/test_approval.py What: ApprovalHardeningRound5Test added (R5-1..R5-6, R5-9); ask() takes a question; M1 and R2-2 tests no longer assume new creates the store (it now writes only to clear a namesake's entry). Why: code review r5.
- 2026-11-25 scripts/scaffold.py script_gate, hooks/plan_approval.py _read What: approval/checks/guard report through gate_root(root) or root as the scripts read; started() leaves an unreadable store alone and refuses new. Why: R5-1, R5-5. Effect: internal.
- 2026-11-25 hooks/plan_approval.py back to Base plus started(), _read() and a no-write forget(); state.py approval_store; per-repo keys removed. What: cut back to 3.16's keys and typed approve. Why: the user's call after review round 6. Effect: nested-repo namesakes share an approval as in 3.16 (todo).
- 2026-11-25 test-change tests/test_approval.py What: key tests removed (R2-4/R3-5, R4-3, R5-2, R5-9); ApprovalHardeningRound6Test added (R6-1, R6-3, R6-5, R6-7). Why: code review r6 and the cut-back.
- 2026-11-25 test-change tests/test_approval.py What: R7-1, R7-2, R7-4 tests added to ApprovalHardeningRound6Test. Why: code review r7 low bugs, fixed in passing.

## Open questions
-
