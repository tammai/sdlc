# 2026-11-17-l-objects-ui-and-setup
Status: done
Process: 3
Change: .sdlc/2026-11-17-l-objects-ui-and-setup/change.md   (this feature's record for people)
Track: L   (sized up because: two distinct parts (UI layer, setup step) across a script, a command, a skill, a reference, an agent and host copies; footprint: 14 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-17
Base: 7c6fdf5
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: 7c6fdf5 tree a4274d446fb2a4b5544c6bdcbe7a159ab2b412e4
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [x] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline, one part

## Handoff
- spec: docs/specs/13-domain-model.md (B3, B4, D7); D7 read against impeccable 4.9.2 skills/impeccable/reference/init.md
- mirror cmd_deploy (scripts/scaffold.py:2353) and its parser (scripts/scaffold.py:2724); Refused exits 2, a missing lock 1
- SKILL.md is at 19,030 of 20,000 characters: the step's detail goes in references/objects.md
- eject keep list: scripts/scaffold.py eject_plan

## Tasks
1. **scaffold.py objects: report, inputs, --enable; eject keeps the file** — AC-001 AC-002 AC-003 AC-004
   - Files: `scripts/scaffold.py`, `tests/test_objects_setup.py`
2. **/sdlc:setup objects** — AC-005
   - Files: `commands/setup.md`, `skills/setting-up-projects/SKILL.md`, `skills/setting-up-projects/references/objects.md`
3. **UI mapping and impeccable note** — AC-006
   - Files: `skills/orchestrator/references/ui-work.md`
4. **ui-reviewer reads the objects file, and host copies** — AC-007
   - Files: `agents/ui-reviewer.md`, `hosts/`
5. **Docs** — AC-005
   - Files: `docs/specs/13-domain-model.md`, `docs/wiki/Setup-and-upgrade.md`, `docs/wiki/Commands.md`, `README.md`, `CHANGELOG.md`

## Public Surface
- command `scaffold.py objects` — AC-001
- command `/sdlc:setup objects` — AC-005

## Test lock
- `tests/test_objects_setup.py` sha256:e95e5f5f7c737e5bfb58d98b7b3f4564eb61544069d26068cb990280008f6982

## Gate log
- 2026-11-17 Stage 1: pass — plan self-approved (L): every B3/B4 item maps to an AC; no open questions; D7 settled by impeccable's init reference; nothing irreversible or beyond the request
- 2026-11-17 Stage 2: pass
- 2026-11-17 review: ran code (L, Public Surface not none), security (repo config objects reaches a file path through scaffold.py objects), self-chosen: L
- 2026-11-17 Stage 2: pass
- 2026-11-17 Stage 2: pass
- 2026-11-17 Stage 2: pass
- 2026-11-17 Stage 3: pass

## Deviations
- 2026-11-17 setup What: the plugin repo isn't set up for sdlc. Why: it's the plugin itself, as for earlier features. Effect: verify.py runs only the AC tests; the full suite is run by hand before Ship.
- 2026-11-17 scripts/objects.py What: check_file(), the file rules on a given path whether or not the switch is on. Why: setup checks the draft before it turns the switch on. Effect: check() calls it; no behaviour change. scripts/scaffold.py object_inputs, cmd_objects, OBJECT_INPUTS: internal helpers of the new command. Docs: README.md, docs/wiki/Commands.md, docs/wiki/Configuration.md, docs/wiki/How-it-works.md, hosts/ rebuilt by hosts.py.
- 2026-11-17 tests/test_deploy_targets.py What: the argument-hint regex matches deploy anywhere in the list, not only last. Why: setup's hint now ends with objects; the test checks that deploy is listed. Effect: test only.
- 2026-11-17 round-1 fixes What: objects.target() (one path rule, switch on or off); scaffold.py object_kind, tracked_regular_files, OBJECT_SOURCE, OBJECT_SKIP_DIRS, OBJECT_KINDS replace the OBJECT_INPUTS regex; eject keeps a config-named objects path; review-brief.md and ui-reviewer read the path scaffold.py objects prints; tests/test_objects_setup_review.py; docs/runbook.md, docs/wiki/Setup-and-upgrade.md. Why: review r1 SEC-1, SEC-2, F1-F6, F8-F14, FP1-FP3. Effect: as the change file says; S unaffected.
- 2026-11-17 round-2 fixes What: flow.md Review step 2 names the objects file in each review prompt (the brief's objects section, or none), review-brief.md, ui-reviewer and managing-knowledge read that, not config; cmd_objects reads off as objects.path() does; inputs drop seeds and dumps, rank other .sql/.graphql with routes, list an unmerged path once; the old layout's place only when written as itself. Why: review r2 R2-1 to R2-4, security r2 R2-1 and R2-6. Effect: as the change file says.
- 2026-11-17 round-3 lows What: schema.* modules rank with models; the seed/dump/fixture filter matches whole name parts; flow.md and managing-knowledge say to rerun brief.py when its output isn't in context, and that an objects: invalid section means none. Why: review r3 R3-1, R3-3, R3-4, FP-1. Effect: as the change file says.

## Open questions
-
