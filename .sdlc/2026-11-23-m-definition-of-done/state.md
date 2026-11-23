# 2026-11-23-m-definition-of-done
Status: done
Process: 3
Change: .sdlc/2026-11-23-m-definition-of-done/change.md   (this feature's record for people)
Track: M   (sized up because: —; footprint: 12 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-23
Base: 6642397
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: 6642397 tree d9c2ffdbd6f627f07dc9cdd2a2768d731f14dec2
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
1. **done list and its checks** — AC-001 AC-002 AC-003 AC-004
   - Files: `scripts/scaffold.py`, `scripts/brief.py`, `scripts/ship.py`, `hooks/trust_anchor.py`, `tests/test_definition_of_done.py`
2. **Flow and setup text** — AC-005
   - Files: `skills/orchestrator/references/flow.md`, `skills/orchestrator/references/s-track.md`, `templates/change-template.md`, `skills/setting-up-projects/SKILL.md`, `skills/setting-up-projects/references/definition-of-done.md`, `commands/setup.md`
3. **Docs** — AC-005
   - Files: `docs/wiki/Configuration.md`, `CHANGELOG.md`, `.sdlc/todo.md`, `hosts/skills/setup/SKILL.md`

## Public Surface
- command `done` — AC-001
- config `done` — AC-001

## Test lock
- `tests/test_definition_of_done.py` sha256:b0ab4db6ee6abbf5a69d4e960ab0a4ec14297911104324883eadbf3e73da4fa6

## Gate log
- 2026-11-23 Stage 1: pass — plan not stopped for approval: low-risk M
- 2026-11-23 Stage 2: pass
- 2026-11-23 review: ran code (Public Surface: command done, config done), not asked: low risk
- 2026-11-23 Stage 2: pass
- 2026-11-23 Stage 2: pass
- 2026-11-23 Stage 3: pass

## Deviations
- 2026-11-23 test-change tests/test_definition_of_done.py What: AC-003 asserts the refusal's message, not its code. Why: ship.py prints the message in text output; the code is in --json output.
- 2026-11-23 sdlc_scopes.py, done_problem, definition_of_done, check_done, DONE_LINE, cmd_done, DONE_MOST, DONE_LONGEST, skills/setting-up-projects/SKILL.md (one row, the hard-stop list, two phrases trimmed to stay under 20000 characters) What: shared reader and validator in hooks/sdlc_scopes.py (scripts and hooks both read it). Why: one rule for scaffold, brief, ship and the trust anchor. Effect: none beyond the declared surface.
- 2026-11-23 test-change tests/test_definition_of_done.py What: tests for code review r1 (the bar held from Base, an invalid list, weak evidence, a refusal writing nothing, the anchor's section and shape, setup routing); AC-001 also refuses ' — ' and --clear with items; AC-004 asserts the notice wording. Why: code review r1 DOD1-DOD13. Docs: README.md, docs/wiki/Commands.md, docs/wiki/Shipping-and-gates.md, docs/specs/02-orchestration.md. Helpers: done_config, done_items, DONE_FORMAT.
- 2026-11-23 done_config, done_items, DONE_FORMAT What: helpers of the r1 fixes (an invalid list's reason; the bar held from Base; the format in the refusal). Why: code review r1 DOD3, DOD4, DOD10. Effect: none beyond the declared surface.
- 2026-11-23 test-change tests/test_definition_of_done.py What: tests for code review r2 (the last accepted list, odd configs, one heading rule, a set-up repo, more weak evidence and line breaks). Why: code review r2. Helpers: accepted_done, DONE_HEADING. Docs: docs/wiki/How-it-works.md, skills/setting-up-projects/references/definition-of-done.md.
- 2026-11-23 accepted_done What: reads the list the user last accepted (trust anchor commands_ok, else Base). Why: code review r2 R2-1, R2-2. Effect: an item leaves the bar only through the user's reply.

## Open questions
-
