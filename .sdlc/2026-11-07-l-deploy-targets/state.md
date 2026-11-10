# 2026-11-07-l-deploy-targets
Status: done
Process: 3
Change: .sdlc/2026-11-07-l-deploy-targets/change.md   (this feature's record for people)
Track: L   (sized up because: several distinct parts (setup step, scaffold command, deploy command, platform reference, brief, templates, upgrade migration); footprint: 22 files)
Risk: low   (adds a config key, a scaffold command and instruction text; no auth, secrets code, migration or breaking change)
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-07
Base: de61977
Owner: 3235400+tammai@users.noreply.github.com
Tool: claude-code
Verified: de61977 tree 1ed5acd397eb0ec488fab62da6e19c08b811d3ec
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [x] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline, because one session holds it: mostly instruction text plus one scaffold command and a brief.py section

## Handoff
- Repo not set up for sdlc (setup none, layout legacy): the plugin repo runs its features this way; tests: python3.10 -m unittest discover -s tests -t tests
- scaffold.py cmd_design (scripts/scaffold.py:411) and its parser (~line 1777) are the pattern for cmd_deploy
- brief.py's plugin root is os.path.dirname(HERE); repo config is untrusted, so the target must match [a-z0-9-]+ before it names a file
- hosts/skills/{setup,deploy}/SKILL.md are generated: run python3 scripts/hosts.py build after editing commands/ or skills/

## Tasks
1. **Default migration globs** — AC-001
   - Files: `templates/project/config.defaults.json`, `tests/test_deploy_targets.py`
2. **scaffold.py deploy command** — AC-002
   - Files: `scripts/scaffold.py`, `tests/test_scaffold.py`
3. **Runbook template, setup step, upgrade migration** — AC-003 AC-004
   - Files: `templates/knowledge/deploy-runbook.md`, `skills/setting-up-projects/SKILL.md`, `migrations/3.3.0-deploy-target.md`, `hosts/skills/setup/SKILL.md`
4. **/sdlc:deploy follows config and runbook** — AC-005
   - Files: `commands/deploy.md`, `hosts/skills/deploy/SKILL.md`
5. **Platform reference and brief section** — AC-006 AC-007
   - Files: `skills/orchestrator/references/platforms/gcp-cloud-run.md`, `scripts/brief.py`, `tests/test_brief.py`
6. **Templates and integrations** — AC-008 AC-009
   - Files: `templates/change-template.md`, `skills/orchestrator/references/flow.md`, `templates/project/rules/migrations.md`, `templates/constitution-template.md`, `skills/orchestrator/references/integrations.md`
7. **Docs and stale-docs audit** — AC-004
   - Files: `CHANGELOG.md`, `docs/wiki/Configuration.md`, `docs/wiki/Commands.md`, `docs/wiki/Setup-and-upgrade.md`, `docs/specs/01-setup-upgrade-eject.md`, `CONTRIBUTING.md`

## Public Surface
- command `scaffold.py deploy` — AC-002
- config `deploy` — AC-002

## Gate log
- 2026-11-07 Stage 1: pass — plan self-approved (L): every request item maps to an AC (1→AC-002–004, 2→AC-005, 3→AC-006/007, 4→AC-008, 5→AC-009, bug→AC-001, stamp→Decisions, no fix needed); no open questions; decisions settled by the request, missue's change and the code; nothing beyond the request kept, nothing irreversible
- 2026-11-07 Stage 2: pass
- 2026-11-07 review: ran code default (Public Surface not none; L) and security (untrusted repo config reaches a file path in brief.py; diff touches migrations/), self-chosen: L
- 2026-11-07 Stage 3: fail — review r1: S-001 (high), S-002/M2, M1 bugs, L1; back to Build
- 2026-11-10 Stage 2: pass
- 2026-11-10 Stage 3: pass — review r2 passed (code, security): fixing its medium and low bugs test-first, closed by verify (no round 3)
- 2026-11-10 Stage 2: pass
- 2026-11-10 Stage 3: pass

## Deviations
- 2026-11-07 Define What: ran without sdlc setup. Why: the plugin repo isn't set up for sdlc (setup none, layout legacy) and runs its features this way, as earlier features did. Effect: no config-driven verify plan; tests run from the state's command.
- 2026-11-07 cmd_deploy What: the scaffold.py deploy command's function, named in Public Surface as the command. Why: drift lists new top-level functions by name. Effect: none; same surface.
- 2026-11-07 platform What: brief.py helper that prints the platform's Define checks (AC-006), internal to brief.py. Why: drift lists new top-level functions by name. Effect: none; no new public surface.
- 2026-11-07 Task 6/7 files What: also changed skills/project-constitution/SKILL.md (names the optional Release principle), docs/runbook.md, docs/wiki/Project-setup.md and docs/specs/02-orchestration.md. Why: the stale-docs audit found them listing setup steps, scaffold commands and the deploy rule. Effect: docs only.
- 2026-11-07 runbook_path, stored_deploy, PRODUCTION_ENVS What: scaffold.py helpers added in the r1 fix round. Why: S-001 (production never routine), S-002/M2 (stored values checked on read), M1 (--runbook refused with exit 2). Effect: internal to scaffold.py deploy; new tests in test_scaffold.py and test_deploy_targets.py.
- 2026-11-10 Rebase What: main moved from c486687 to de61977 (3.3.0, 3.4.0, 3.5.0 released) while this was in Review; the work was stashed, main fast-forwarded and the stash reapplied, with five conflicts resolved by keeping both sides (CHANGELOG, Project-setup tree, brief.py, scaffold.py, setup SKILL.md). Base set to de61977. Why: 3.3.0 is taken, so the upgrade migration is now migrations/3.6.0-deploy-target.md (change file, deploy.md, spec 01 and the AC-004 test follow), and setup now merges its branch locally without asking, so /sdlc:setup deploy does too. Effect: same behaviour; version numbers and one sentence.
- 2026-11-10 Review r2 fixes What: scaffold.py is_production, ENV_NAME, RUNBOOK_EXCLUDED and a stricter runbook_path; commands/setup.md takes deploy (hosts/skills/setup/SKILL.md regenerated); README.md and docs/wiki/Commands.md name /sdlc:setup deploy; docs/runbook.md, docs/wiki/Configuration.md and spec 01 SET-FR-050 describe the checks; Task 3's migration file is migrations/3.6.0-deploy-target.md, not 3.3.0. Why: round 2 (code M1, M2, F1, F2; security M-1, M-2, L-2, L-3), fixed test-first and closed by verify, no round 3. Effect: production is any name with a prod/production/live/prd part, names are plain ASCII, the runbook is a .md outside .git/.claude/.sdlc, setup writes it only at the printed path.

## Open questions
-
