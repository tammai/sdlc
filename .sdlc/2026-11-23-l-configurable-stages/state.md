# 2026-11-23-l-configurable-stages
Status: done
Process: 3
Change: .sdlc/2026-11-23-l-configurable-stages/change.md   (this feature's record for people)
Track: L   (sized up because: —; footprint: 22 files)
Risk: high   (config the agent edits switches safety hooks off)
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-23
Base: 2b03df5
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: 2b03df5 tree b9b5a6c4b27cf491fe2e1f3a8f765558f22eca63
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [x] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline, one part

## Handoff
- Inventory of every enforcement point: this session's Explore report, summarised in change.md Why; hooks read raw config via sdlc_scopes.read_repo_json
- trust_anchor must still report a relaxing mode/skip change in advisory (repo-level anchor key in .sdlc/.work/trust-anchor.json)

## Tasks
1. **Mode and skip readers and setters** — AC-001 AC-002
   - Files: `hooks/sdlc_scopes.py`, `scripts/scaffold.py`, `tests/test_modes.py`
2. **Advisory in every hook** — AC-003 AC-004 AC-005
   - Files: `hooks/model_router.py`, `hooks/review_rounds.py`, `hooks/trust_anchor.py`, `hooks/verify_freshness.py`, `hooks/prove_budget.py`, `hooks/stuck_turn.py`, `hooks/user_answer.py`, `hooks/role_guard.py`, `hooks/pretooluse.py`, `hooks/stop.py`, `hooks/userpromptsubmit.py`, `hooks/security_reminder_hook.py`, `hooks/session_status.py`
3. **Skip in the review gate** — AC-006
   - Files: `hooks/sdlc_review_gate.py`
4. **Trust anchor on relaxing changes** — AC-007
   - Files: `hooks/trust_anchor.py`
5. **Flow and setup text** — AC-008 AC-009
   - Files: `skills/orchestrator/SKILL.md`, `commands/start.md`, `skills/orchestrator/references/flow.md`, `skills/orchestrator/references/s-track.md`, `skills/setting-up-projects/SKILL.md`, `commands/setup.md`, `templates/project/rules/sdlc-advisory.md`
6. **Docs** — AC-008
   - Files: `docs/wiki/Configuration.md`, `docs/wiki/Hooks.md`, `docs/adr/0031-modes-and-skips.md`, `CHANGELOG.md`, `.sdlc/todo.md`

## Public Surface
- command `mode` — AC-001
- command `skip` — AC-002
- config `mode` — AC-001
- config `skip` — AC-002

## Test lock
- `tests/test_modes.py` sha256:45d9a1d5b4b9f42f4e50e163ad2de2244035df476f22081cda94b38a107b0a99

## Gate log
- 2026-11-23 Stage 1: pass — plan approved by the user (approach A, security silent in advisory, trust anchor protection)
- 2026-11-23 Stage 2: pass
- 2026-11-23 review: ran code and security (L, Risk: high), self-chosen: L
- 2026-11-23 Stage 2: pass
- 2026-11-23 Stage 2: pass
- 2026-11-23 Stage 2: pass
- 2026-11-23 Stage 2: pass
- 2026-11-23 Stage 3: pass

## Deviations
- 2026-11-23 cmd_mode, cmd_skip, mode, skipped, advisory, advisory_from, MODES, SKIPPABLE, config_notice, gate_config, sdlc_scopes_advisory, _review_skipped What: the helper functions behind the declared surface (the mode and skip commands and config keys), not listed one by one. Why: internal to scaffold and the hooks. Effect: none beyond the declared surface.
- 2026-11-23 test-change tests/test_modes.py What: added test_the_session_status_line_names_the_mode_and_skips; no AC test changed. Why: the orchestrator text says the status line names the mode, so that needs a test.
- 2026-11-23 test-change tests/test_modes.py What: AC-009 reads the steps advisory skips from skills/setting-up-projects/references/advisory.md, which SKILL.md points to. Why: the skill passed its 20000-character limit (test_plugin_files). Files moved: templates/project/rules/sdlc-advisory.md to templates/project/advisory/sdlc.md (doctor and the area-rule test read every rules/ template as a path-scoped rule).
- 2026-11-23 skills/setting-up-projects/SKILL.md, skills/setting-up-projects/references/advisory.md, templates/project/advisory/sdlc.md, docs/adr/README.md What: the advisory setup steps moved to a reference (SKILL.md held to 20000 characters by tightening three sentences), the advisory rule template lives outside rules/, the ADR index lists 0030 (numbered 0030, not 0031: 0030 was free). Why: skill size limit, doctor's rules check, the ADR index. Effect: none on behaviour.
- 2026-11-23 test-change tests/test_modes.py What: the config helper records the user's acceptance (a relaxation counts only once accepted); AC-001, AC-002 and AC-007 assert asked vs effective; tests added for each round-1 finding (reply accepts only what was shown, damaged or deleted record, nested or app-repo config, always in advisory, the host adapter, a FIFO config). Why: code review r1 and security review r1.
- 2026-11-23 hosts/skills/start/SKILL.md, hosts/skills/setup/SKILL.md, docs/track-matrix.md, README.md, docs/wiki/Quick-start.md, docs/wiki/Commands.md, docs/wiki/Everyday-work.md, docs/wiki/Where-things-live.md, docs/wiki/Limitations.md, hooks/diffstate.py What: host skill copies rebuilt (hosts.py build); docs that restated the fixed flow qualified. Why: code review r1 M1, M6. Effect: docs and generated copies only.
- 2026-11-23 gate_root, configured, committed, accepted, effective, gating_report, configured_advisory, role_guard_read_only, ANCHOR, CONFIG_KEY What: helpers of the round-1 fixes, not listed as surface. Why: internal to the hooks and scaffold. Effect: none beyond the declared mode/skip surface.
- 2026-11-23 test-change tests/test_modes.py What: tests added for round 2 (scaffold where the hooks read, no stray .sdlc and no reads without a relaxation, a malformed record, the rule switch); the status test covers a partly accepted skip list. Why: security review r2 R2-H1..H3, code review r2 R2-M1..M3, M7, M8.
- 2026-11-23 scripts/doctor.py, gate_of, rule_for_mode, valid_record, _unbranched_write What: doctor skips the PRD and design-system checks in advisory; scaffold helpers for the gate and the rule switch; one shape check; pretooluse's unbranched check split out. Why: round 2 findings. Effect: as the Decisions say.
- 2026-11-23 test-change tests/test_modes.py What: tests for round 3 (HEAD config read at the gate folder, scaffold vs the session's folder, the record never written through a FIFO or link). Why: security review r3 R3-H1, R3-H2, R3-M1. docs/specs/02-orchestration.md: ORC-FR-018 names the mode/skip anchor. write_record, session_gate: helpers.
- 2026-11-23 session_gate, write_record What: scaffold's session-folder check and the hooks' safe record write. Why: security review r3 R3-H2, R3-M1. Effect: scaffold refuses where the session's hooks read another folder; records are swapped in, never written through a FIFO or link.
- 2026-11-23 test-change tests/test_modes.py What: tests for round 4's lows (a session above the repo, a linked record folder). Why: security review r4 R4-L1, R4-L2.

## Open questions
-
