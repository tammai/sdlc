# 2026-11-23-m-storybook-opt-in
Status: done
Process: 3
Change: .sdlc/2026-11-23-m-storybook-opt-in/change.md   (this feature's record for people)
Track: M   (sized up because: —; footprint: 11 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-23
Base: d0b5eb4
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: d0b5eb4 tree a18e02c1eb27a7430876142275603a93577078df
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
1. **storybook switch, verify step, doctor** — AC-001 AC-002 AC-003
   - Files: `scripts/scaffold.py`, `scripts/doctor.py`, `templates/project/config.defaults.json`, `tests/test_storybook.py`
2. **UI flow, review and setup text** — AC-004
   - Files: `skills/orchestrator/references/ui-work.md`, `agents/ui-reviewer.md`, `skills/setting-up-projects/references/design-mode.md`, `templates/design-system-template.md`
3. **Docs** — AC-004
   - Files: `docs/wiki/Configuration.md`, `CHANGELOG.md`, `.sdlc/todo.md`

## Public Surface
- command `storybook` — AC-001
- config `storybook` — AC-001
- config `commands.storybook` — AC-002

## Test lock
- `tests/test_storybook.py` sha256:8a08ccc7ef8ebd9e38f7cb90369990253c0e649fa487731a60d96d3da145c750

## Gate log
- 2026-11-23 Stage 1: pass — plan not stopped for approval: low-risk M
- 2026-11-23 Stage 2: pass
- 2026-11-23 review: ran code (Public Surface: command storybook, config storybook, commands.storybook), not asked: low risk
- 2026-11-23 Stage 2: pass
- 2026-11-23 Stage 2: pass
- 2026-11-23 Stage 3: pass

## Deviations
- 2026-11-23 test-change tests/test_storybook.py What: dropped a pointless assertion from AC-001's test. Why: it asserted nothing (any exit code passed). cmd_storybook: the command's function.
- 2026-11-23 cmd_storybook, hosts/cursor/agents/ui-reviewer.md What: the storybook command's function; the Cursor copy of the UI reviewer rebuilt (hosts.py build). Why: the declared command; the host copy must match. Effect: none beyond the declared surface.
- 2026-11-23 test-change tests/test_storybook.py What: AC-004 asserts the rules, not the word; four tests for code review r1 (impeccable, monorepo, custom order, build output). Why: code review r1 SB1-SB4, SB6, SB10. Files: scripts/verify.py (GENERATED), docs (spec 01, 10, ADR 0002, Configuration, the sdlc.md rule template). Helpers: storybook_found, storybook_on, storybook_unrun.
- 2026-11-23 storybook_found, storybook_on, storybook_unrun What: helpers of the r1 fixes (a package's catalog, off outside builtin, the custom-order warning). Why: code review r1 SB1, SB3, SB4. Effect: none beyond the declared surface.
- 2026-11-23 scripts/verify.py What: GENERATED also matches storybook-static/ (and its docstring names the storybook step). Why: code review r1 SB6, SB8. Effect: a Storybook build's output is never drift and ship.py never stages it.
- 2026-11-23 test-change tests/test_storybook.py What: tests for code review r2 (the hooks skip storybook-static/, doctor's hint per problem, the command map, the cleared switch said); the template assertion names the rule. Why: code review r2. Files: hooks/gitutil.py, docs (ADR 0002, spec 04, 10, Verification wiki, flow.md, setup.md, CHANGELOG), hosts copies.
- 2026-11-23 hooks/gitutil.py What: SKIP_PATH_PATTERNS lists storybook-static/. Why: code review r2 (a Storybook build reached the commit and turn-end reviews). Effect: that build output is skipped like dist/ and build/.

## Open questions
-
