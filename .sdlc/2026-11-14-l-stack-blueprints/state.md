# 2026-11-14-l-stack-blueprints
Status: active
Process: 3
Change: .sdlc/2026-11-14-l-stack-blueprints/change.md   (this feature's record for people)
Track: L   (sized up because: five distinct parts: setup references, scaffold.py render, orchestrator Define, platform references, constitution; footprint: 25 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-14
Base: 5628df6
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: cc17992 tree e79fd3a7ad809f87b1eb501e134f029a0a23a976
Slice: B3   Slice base: cc17992   Slice gates: none
Current: Stage 2 – Build

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [ ] 2 Build
- [ ] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
parts in fresh sessions, because the user builds one part per session (backlog.md); one growing draft PR

## Handoff
- Source (read-only): %USERPROFILE%/Downloads/stack-blueprints/stack-blueprints (VERSION 0.3.0); docs/SDLC-MAPPING.md maps each piece; init/selection.json holds the rules and warnings; catalog/<layer>/<id>/entry.json the packages and commands; modules/ the guidance
- tests/test_workbench.py:591 PreferredStacks picks stacks.md sections by heading prefix (Nuxt, React, Node, Go) and checks five command rows: a new ## heading must not start with those words
- scaffold.py:526 cmd_render writes LF/UTF-8 and records {class, sha256, template} in the lock; FILE_CLASSES is generated/seeded (scaffold.py:44); forget (scaffold.py:2064) untracks; shipped_files (scaffold.py:317) names plugin rules sdlc-<name>
- eject keeps area rules (references/eject.md:13); brownfield writes area rules as .claude/rules/<area>.md user-owned (references/brownfield.md:38)
- No .sdlc/config.json in this repo: verify.py runs only the AC tests; run the full suite by hand: py -3.10 -m unittest discover -s tests -t tests
- Stale-docs for setup text: greenfield.md:10, workbench.md:31, monorepo.md stack step, docs/specs/01-setup-upgrade-eject.md SET-FR-053, docs/wiki/Project-setup.md:9, CHANGELOG ## Unreleased above ## 3.8.0, CONTRIBUTING.md:24

## Tasks
1. **B1 Selection table, warnings, stack interview, ADR 0026** — AC-001 AC-002 AC-003
   - Files: `skills/setting-up-projects/references/stacks.md`, `skills/setting-up-projects/references/greenfield.md`, `skills/setting-up-projects/references/monorepo.md`, `skills/setting-up-projects/references/workbench.md`, `docs/adr/0026-stack-blueprints-in-setup.md`, `docs/adr/README.md`, `docs/specs/01-setup-upgrade-eject.md`, `docs/wiki/Project-setup.md`, `CHANGELOG.md`, `tests/test_stack_blueprints.py`
2. **B2 Stack sections and CI toolchains** — AC-004 AC-005 AC-006 AC-009
   - Files: `skills/setting-up-projects/references/stacks.md`, `scripts/scaffold.py`, `tests/test_stack_blueprints.py`, `tests/test_workbench.py`
3. **B3 Convention templates and scaffold.py conventions** — AC-007 AC-008 AC-009
   - Files: `templates/project/conventions/`, `scripts/scaffold.py`, `skills/orchestrator/references/flow.md`, `skills/orchestrator/references/s-track.md`, `skills/setting-up-projects/SKILL.md`, `skills/setting-up-projects/references/upgrade.md`, `skills/setting-up-projects/references/eject.md`, `tests/test_stack_blueprints.py`
4. **B4 Platform references** — AC-010
   - Files: `skills/orchestrator/references/platforms/cloudflare.md`, `skills/orchestrator/references/platforms/vercel.md`, `skills/orchestrator/references/platforms/docker-compose.md`, `scripts/brief.py`, `tests/test_stack_blueprints.py`
5. **B5 Constitution per stack, scaling roadmap** — AC-011
   - Files: `skills/project-constitution/references/stack-principles.md`, `skills/project-constitution/SKILL.md`, `templates/knowledge/scaling-roadmap.md`, `skills/setting-up-projects/references/greenfield.md`, `tests/test_stack_blueprints.py`

## Public Surface
- command `scaffold.py conventions` — AC-007

## Gate log
- 2026-11-14 Stage 1: pass — plan self-approved (L): (1) parts 1-5 map to AC-001-011, constraints to must-never-break; (2) open questions answered by the user (7 decisions confirmed, user-owned + rendered list, one growing PR); (3) every decision is the user's answer or the mapping doc's; (4) no unasked proposal, nothing irreversible
- 2026-11-14 handoff B1: stacks.md has ## Choosing a stack (web, mobile, backend language, shape) and ### Warnings (shape, language, mobile, deploy; Vercel Hobby non-commercial and Workers background limits checked against vercel.com and developers.cloudflare.com on 2026-11-14). The table names Vue, Next.js, Flutter, iOS, Android, FastAPI and the one-deployable Nuxt/Next shape, which have no sections yet: B2 adds them (the fallback line covers the gap until then). Auth, data and tenancy warnings from init/selection.json (supabase-auth token storage, better-auth password hashing on Workers free, self-hosted DB at medium scale, internal + multi-tenant) go to B3's templates and B4's platform references. ADR 0026 written.
- 2026-11-14 handoff B2: stacks.md now has Vue, Next.js, Flutter, iOS, Android, FastAPI sections and a Config stack line per section; Node picks @hono/zod-openapi (consumer + contract) else @hono/zod-validator; Nuxt bridge server/api/[...].ts (toWebRequest, Nuxt 4; nuxi build), Next.js bridge app/api/[[...route]]/route.ts (@hono/vercel). scaffold.py CI_SETUP has swift (setup-xcode@v1) and a Swift stack defaults the runner to macos-latest when the repo config has no ci.os (scaffold.py generate_ci). Sources in plan-B2.md. B3 templates: Nuxt 5 changes the bridge to event.req; auth libraries go only in the auth template.
- 2026-11-14 handoff B3: scaffold.py conventions <stack> <area> [--package] writes .claude/rules/<stack>-<area>.md (user-owned: in declined, never files; lock 'conventions' keeps stack, area, package, root, template, version, render sha256); upgrade-plan 'conventions' lists changed templates as a diff, 'conventions --seen <path>' takes the new baseline. 29 templates in templates/project/conventions/<stack>/<area>.md (node, go, fastapi: layers schema data-access contract auth; nuxt vue react nextjs: layers ui; flutter ios android: layers auth); prose, no placeholders. Define's stack is read from the manifest (flow.md, s-track.md). Better Auth on Workers free CPU limit is in node/auth.md marked (verify); B4's platform refs carry the data-layer driver notes (neon, cloud-sql, self-hosted) and Supabase/Workers limits. Sources in plan-B3.md.

## Deviations
- 2026-11-14 setup What: went on with setup none (no .sdlc/config.json). Why: the plugin's own repo runs sdlc without setup (as 2026-11-13-l-workbench). Effect: verify.py runs the AC tests; the full suite is run by hand with py -3.10 -m unittest discover -s tests -t tests.
- 2026-11-14 parts What: a draft PR opens after B1 and grows with each part. Why: the user's answer in Define (one growing PR). Effect: Review and Ship stay once, after B5.
- 2026-11-14 B1 docs/adr/0026-stack-blueprints-in-setup.md, docs/adr/README.md, docs/specs/01-setup-upgrade-eject.md, docs/wiki/Project-setup.md, CHANGELOG.md What: ADR 0026, SET-FR-055, the wiki greenfield line, an Unreleased changelog entry. Why: the stale-docs audit and the ADR the request asked for. Effect: docs only.
- 2026-11-14 B2 red runs What: verify.py red for AC-004-006 was recorded after the code, by stashing stacks.md and scaffold.py and running it on the base. Why: the tests were run red by hand first, without verify.py. Effect: the red record is genuine (base code); no change to the tests.
- 2026-11-14 B2 docs/specs/01-setup-upgrade-eject.md, docs/wiki/Project-setup.md, skills/setting-up-projects/references/greenfield.md, CHANGELOG.md What: SET-FR-011 and SET-FR-053, the wiki stack list, the ci step's macOS line, the Unreleased entry. Why: the stale-docs audit. Effect: docs only.
- 2026-11-14 B3 naming What: convention files are .claude/rules/<stack>-<area>.md, not <area>.md; AC-007 and its decision row reworded. Why: the user's answer in B3 (a web + API monorepo's second package would be refused on layers, contract, auth). Effect: dest name only; same allowlists and refusals.
- 2026-11-14 B3 CHANGELOG.md, docs/specs/01-setup-upgrade-eject.md, docs/wiki/Project-setup.md, CONTRIBUTING.md What: Unreleased entry, SET-FR-056, the wiki greenfield line, the templates/project tree line. Why: the stale-docs audit. Effect: docs only.
- 2026-11-14 B3 scripts/scaffold.py cmd_conventions convention_areas convention_root convention_template convention_text convention_updates What: module-level functions behind the conventions command and upgrade-plan's conventions list. Why: scaffold.py's style, one function per step; the public surface is the command (AC-007). Effect: none outside scaffold.py.
- 2026-11-14 B3 fix scripts/scaffold.py convention_entry, tests/test_stack_blueprints.py, docs/adr/0026-stack-blueprints-in-setup.md, docs/wiki/Where-things-live.md, flow.md, s-track.md What: the rule header no longer carries the plugin version (every release would have re-offered every convention); lock entries are used only when their path is their own stack-area name; a test for the upgrade path; ADR and wiki name <stack>-<area>.md; Define says --root <repo> in a workbench. Why: self-check after the B3 commit. Effect: second B3 commit.

## Open questions
-
