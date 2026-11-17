# 2026-11-17-m-guardrails-render
Status: done
Process: 3
Change: .sdlc/2026-11-17-m-guardrails-render/change.md   (this feature's record for people)
Track: M   (sized up because: —; footprint: 6 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-17
Base: b997bce
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: b997bce tree 15b8769f20e7d29c88279fcdbb13af5a2e678a02
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
1. **guardrails --render and doctor's guardrails row** — AC-001 AC-002
   - Files: `scripts/scaffold.py`, `scripts/doctor.py`, `tests/test_guardrails_render.py`
2. **setup's guardrails step uses it** — AC-001
   - Files: `skills/setting-up-projects/SKILL.md`, `hosts/skills/setup/SKILL.md`, `docs/runbook.md`, `CHANGELOG.md`

## Public Surface
- command `scaffold.py guardrails --render` — AC-001

## Test lock
- `tests/test_guardrails_render.py` sha256:5856ed70474973dcd2f4519c59e7c66c754fb15ec2af7050c9a0258241a30b2e

## Gate log
- 2026-11-17 Stage 1: pass — plan not stopped for approval: low-risk M (the user chose the fix at the release stop)
- 2026-11-17 Stage 2: pass
- 2026-11-17 review: ran code (Public Surface not none), not asked: low risk
- 2026-11-17 Stage 2: pass
- 2026-11-17 Stage 2: pass
- 2026-11-17 Stage 3: pass

## Deviations
- 2026-11-17 setup What: the plugin repo isn't set up for sdlc. Why: it's the plugin itself. Effect: verify.py runs only the AC tests; the full suite is run by hand.
- 2026-11-17 scripts/scaffold.py guardrail_list What: a helper shared by cmd_guardrails and doctor. Why: one list of the guardrails setup writes. Effect: internal.
- 2026-11-17 test-change tests/test_guardrails_render.py What: the ok case also writes the seven rules; file handles closed. Why: review r1 F7 widened doctor's row to rules, which the test's repo never had; F11. Effect: the AC-002 test still fails without the feature.
- 2026-11-17 review r1 fixes What: --render reuses cmd_render per guardrail (recorded as it goes), leaves deleted, outside and declined ones, refuses without Claude Code, reports failures after writing the rest; doctor's row covers rules and guardrails, only on a current scaffold; tests/test_guardrails_render_review.py. Why: review r1 F1-F8, F11. Effect: as the change file says.
- 2026-11-17 review r2 fixes What: render strips a trailing \r or space from its template and dest; --render refuses a scaffold behind the plugin, reports every failure with the full result (exit 1), and tells a written-but-unrecorded file apart; doctor's fix names the render command for each missing rule and skips paths outside the repo; setup shows kept guardrails to the user. Why: review r2 R2-1 to R2-8, R2-13. Effect: as the change file says.

## Open questions
-
