# 2026-11-24-m-gh-92-approval-policy
Status: done
Process: 3
Change: .sdlc/2026-11-24-m-gh-92-approval-policy/change.md   (this feature's record for people)
Track: M   (sized up because: config key, trust anchor, new hook, state.py check, flow docs; footprint: 26 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-24
Base: 7e5583e
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: 7e5583e tree 1e049b26e5e96df6f940a28c83fdf736ee02eda8
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [x] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline: this session builds it, one part

## Handoff
-

## Tasks
1. **Policy, its acceptance and setup** — AC-006 AC-007
   - Files: `hooks/sdlc_scopes.py`, `hooks/trust_anchor.py`, `hooks/session_status.py`, `scripts/scaffold.py`, `scripts/brief.py`, `commands/setup.md`, `hosts/skills/setup/SKILL.md`
2. **Approval record and the refusal** — AC-001 AC-002 AC-003 AC-004 AC-005
   - Files: `hooks/plan_approval.py`, `hooks/hooks.json`, `hosts/codex/hooks.json`, `hosts/cursor/hooks.json`, `hooks.json`, `scripts/state.py`, `tests/test_approval.py`
3. **Flow and docs** — AC-001
   - Files: `skills/orchestrator/SKILL.md`, `commands/start.md`, `hosts/skills/start/SKILL.md`, `skills/orchestrator/references/flow.md`, `skills/orchestrator/references/s-track.md`, `docs/adr/0031-approval-policy.md`, `docs/adr/README.md`, `docs/specs/02-orchestration.md`, `docs/wiki/Configuration.md`, `docs/wiki/Hooks.md`, `docs/wiki/Limitations.md`, `CHANGELOG.md`

## Public Surface
- config `approval` — AC-007
- command `scaffold.py approval` — AC-007

## Test lock
- `tests/test_approval.py` sha256:b325e10ed9110fb1d193625b2116b51524b0c12ba4e80e60b81159eaceef05ee

## Gate log
- 2026-11-24 Stage 1: pass — plan not stopped for approval: low-risk M
- 2026-11-24 Stage 2: pass
- 2026-11-24 Stage 3: fail — code review r1 FAIL: M1-M6 fixed test first in this round
- 2026-11-24 Stage 2: pass
- 2026-11-24 Stage 3: pass — code review r2 PASS; its N1-N3, N5, F4, F5 fixed test first, N4 ticketed
- 2026-11-24 Stage 2: pass
- 2026-11-24 Stage 3: pass — code review on opus: r1 FAIL (M1-M6 fixed), r2 PASS (N1-N3 fixed)

## Deviations
- 2026-11-24 hosts/hook.py What: added plan_approval.py to the UserPromptSubmit scripts other agents run. Why: a typed approve <feature> must reach Codex, Cursor and Antigravity too. Effect: one more file than the plan named.
- 2026-11-24 test-change tests/test_approval.py What: AC-007's test now records the accepted ml before asking for high-risk. Why: with no trust-anchor record the committed config decides, so an unrecorded ml was never the accepted value; the test assumed it was. Effect: same behaviour checked, from a realistic accepted state.
- 2026-11-24 internal helpers What: approval_configured, approval_committed, approval_accepted, needs_approval (hooks/sdlc_scopes.py), cmd_approval (scripts/scaffold.py), plan_approval_problem (scripts/state.py), and load, approved, waiting, record, main (hooks/plan_approval.py). Why: module-internal functions the policy, the record and the refusal need; not an API other code is promised. Effect: none outside these modules; the public surface stays the config key and the scaffold command.
- 2026-11-24 scripts/brief.py, hosts/codex/hooks.json, hosts/cursor/hooks.json, hooks.json What: planned, left unchanged. Why: the session status line already names the policy, which brief.py would only repeat; the host configs call hosts/hook.py, whose script list took plan_approval.py instead. Effect: none.
- 2026-11-24 test-change tests/test_approval.py What: AC-003's test gained an 'Approve with changes' answer and a question naming a feature that isn't waiting; AC-008's test is new. Why: code review r1 M1, M2, M4, M6. Effect: the tests now pin the stricter rules.
- 2026-11-24 AC-008 red What: its red step was recorded with this change's state.py and plan_approval.py set aside (HEAD's state.py, no hook), after the fix was written. Why: the test was written and seen failing before the fix, but the red run wasn't recorded then. Effect: the record shows it failing without the feature, as red --at 7e5583e also does.
- 2026-11-24 internal helpers r2 What: approval_policy, plan_approval_by (renamed from plan_approval_problem) in scripts/state.py, forget in hooks/plan_approval.py. Why: code review r1 F1, M6, L2. Effect: module-internal only.
- 2026-11-24 test-change tests/test_approval.py What: AC-001's test also refuses advance 3 from Define; AC-008's test also takes the approval back on a typed change. Why: code review r2 N1, N3. Effect: the tests pin every way out of Define and both kinds of change request.

## Open questions
-
