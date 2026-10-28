# 2026-10-28-l-impeccable-pairing
Status: active
Process: 2
Change: .sdlc/2026-10-28-l-impeccable-pairing/change.md   (this feature's record for people)
Track: L   (sized up because: several distinct parts (setup, Define, Build guardrail, Review, model router, doctor, migration, docs); footprint: ~22 files)
Risk: low   (no auth, payments, secrets, PII, migration or public API; third-party engine handled by never installing it)
Top model: opus
Commands: test: `py -3.10 -m unittest discover -s tests -t tests`
Started: 2026-10-28
Base: b899e51
Owner: tammai.it@gmail.com
Tool: claude-code
Verified:
Current: Stage 4 – Build

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [ ] 4 Build
- [ ] 5 Review   — the change file's ## Review
- [ ] 8 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline, because one session holds it: mostly instruction text plus four small script changes.

## Handoff
- impeccable facts come from its skill files at v4.8.0 (`.claude/skills/impeccable/SKILL.md`, `reference/init.md`, `shape.md`, `audit.md`, `critique.md`, `hooks.md`, `new-work.md`), not its README; the change file's Why lists them.
- Model router: `hooks/model_router.py:37-39` denies any dispatch with no `model` while a feature is active; impeccable's agents (`.claude/agents/impeccable-*.md`) declare `model: inherit` and are spawned without one. Match on `subagent_type` (line 34 takes the part after `:`).
- `scaffold.py` already has the pattern to copy: `cmd_prd` (`scripts/scaffold.py:1130`) reads/records one config key; its parser at line 1424.
- Setup renders every `templates/project/hookify/sdlc-*.md` in the `guardrails` step (`skills/setting-up-projects/SKILL.md` Common steps); AC-002 needs a scaffold helper that lists them by mode, so the skill and upgrade both use it.
- Detecting impeccable for doctor: its `SKILL.md` under `.claude/skills/impeccable/`, `~/.claude/skills/impeccable/`, `.agents/skills/impeccable/`, `.cursor/…`, or an installed `impeccable` plugin in the Claude plugin cache. Keep the check to file existence.
- The launcher is `<skill dir>/scripts/impeccable` (`impeccable.cmd` on Windows), not `npx`; ui-reviewer finds it from the skill dir.
- This repo isn't set up for sdlc; tests run with the command above, from the repo root.

## Tasks
1. **Config key and command** — AC-001
   - Files: `scripts/scaffold.py`, `templates/project/config.defaults.json`, `tests/test_scaffold.py`
2. **Guardrails by mode** — AC-002
   - Files: `scripts/scaffold.py`, `tests/test_scaffold.py`
3. **Model router lets impeccable agents through** — AC-003
   - Files: `hooks/model_router.py`, `tests/test_model_router.py`
4. **Doctor warning** — AC-004
   - Files: `scripts/doctor.py`, `tests/test_doctor.py`
5. **Setup step: recommend, choose, init/document, pointer file** — AC-005
   - Files: `skills/setting-up-projects/SKILL.md`, `templates/design-system-template.md`
6. **Upgrade migration for set-up UI repos** — AC-002, AC-005
   - Files: `migrations/2.1.0-design-tool.md`
7. **Define and Build in impeccable mode, run-time fallback** — AC-006, AC-008
   - Files: `skills/orchestrator/references/ui-work.md`, `skills/orchestrator/references/flow.md`, `skills/orchestrator/references/s-track.md`
8. **Review in impeccable mode** — AC-007, AC-008
   - Files: `agents/ui-reviewer.md`, `hosts/cursor/agents/ui-reviewer.md`, `commands/review-pr.md`, `hosts/skills/review-pr/SKILL.md`
9. **Docs and decision record** — all
   - Files: `docs/specs/10-ui-design-system.md`, `docs/specs/01-setup-upgrade-eject.md`, `docs/specs/08-health-and-status.md`, `docs/adr/0021-impeccable-for-ui-design.md`, `docs/adr/README.md`, `README.md`, `docs/guidebook.md`, `docs/runbook.md`, `CHANGELOG.md`; then the stale-docs audit in `CONTRIBUTING.md`

## Public Surface
- config key `design` (`"impeccable"` | `"builtin"`, default builtin) — AC-001
- `scaffold.py design [<mode>]` subcommand — AC-001
- a scaffold helper/subcommand listing guardrails for the mode (name settled in Build) — AC-002
- no new dependency: impeccable stays an optional, user-installed tool

## UI mapping
- none: this change edits the plugin, not a UI

## Gate log
- 2026-10-28 Stage 1: open — record written; stopped before Build at the user's request ("run the define stage … and stop"); one question open (below)
- 2026-10-28 Greenfield before DESIGN.md: user approved the recommendation (map against the shape brief; first UI feature's Build writes DESIGN.md; no High for a missing system on that feature)
- 2026-10-28 Stage 1: pass — plan approved by the user

## Deviations
- 2026-10-28 Repo not set up for sdlc (`scaffold.py status`: setup none, layout legacy); the plugin repo runs its features this way (as the slim feature did). Paths follow `scaffold.py paths` (`.sdlc/<feature>/`), not `docs/sdlc/intents/` where the slim feature's files are.
- 2026-10-28 Run with the repo's 2.0 orchestrator (`skills/orchestrator/references/flow.md`) and scripts, not the installed 1.8.1 plugin's.
- 2026-10-28 Base What: moved from 1eaaeab to b899e51 (sdlc 2.0.1). Why: the user waited for 2.0.1 before building. Effect: Build reads 2.0.1's companions and settings.local.json changes first.

## Open questions
-
