# 2026-11-17-l-domain-objects
Status: done
Process: 3
Change: .sdlc/2026-11-17-l-domain-objects/change.md   (this feature's record for people)
Track: L   (sized up because: several distinct parts: a new script, brief, doctor, three instruction files, docs; footprint: 18 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-17
Base: de19fb2
Owner: tammai.it@gmail.com
Tool: claude-code
Verified: de19fb2 tree 9d9ca5762bcc076b5973600b462a59c3dcf87930
Current: Stage 4 – Ship

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [x] 2 Build
- [x] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline, one part (B1+B2 of the spec); B3/B4 out of scope

## Handoff
- spec: docs/specs/13-domain-model.md (copy of the signed-off proposal, D1-D8 decided 2026-11-17)
- pattern to follow: scripts/capabilities.py (config switch, spec-backed off, problems.py JSON); brief.py living_spec() at scripts/brief.py:125
- UI files: doctor.glob_matches (scripts/doctor.py:162) over config areas.ui via scaffold.effective_config; import doctor lazily to avoid a cycle
- rspec domain file: <lock spec>/domain.md for each lock in spec_lock.lock_paths (scripts/spec_lock.py:28)

## Tasks
1. **objects.py check and its template** — AC-001 AC-002 AC-003 AC-004 AC-005
   - Files: `scripts/objects.py`, `templates/objects-template.md`, `tests/test_objects.py`
2. **brief section and rspec pointer** — AC-005 AC-006
   - Files: `scripts/brief.py`, `tests/test_brief.py`
3. **doctor objects row** — AC-007
   - Files: `scripts/doctor.py`, `tests/test_doctor.py`
4. **Define and gate wiring** — AC-008
   - Files: `skills/orchestrator/references/flow.md`
5. **Review and Learn wiring** — AC-009
   - Files: `skills/orchestrator/references/review-brief.md`, `skills/managing-knowledge/SKILL.md`
6. **Docs: spec, ADR, wiki, changelog** — AC-001
   - Files: `docs/specs/13-domain-model.md`, `docs/specs/README.md`, `docs/adr/0028-domain-model-objects-md.md`, `docs/adr/README.md`, `docs/wiki/Configuration.md`, `docs/wiki/How-it-works.md`, `CHANGELOG.md`

## Public Surface
- config `objects` — AC-001
- command `objects.py check` — AC-001

## Test lock
- `tests/test_brief.py` sha256:145ace280556608fefef3466f36af3fa84f7659b3743fde239978299a95727a7
- `tests/test_doctor.py` sha256:811c16d3aae9a79766bec99d51a189204d5fa36ad380e491fb17412bd18e4afb
- `tests/test_objects.py` sha256:9c9c10508fa3abc3a8b2da1985777ddfd0ac7de20774a68fc72748cf02d539de

## Gate log
- 2026-11-17 Stage 1: pass — plan self-approved (L): every B1/B2 requirement maps to an AC; no open questions; decisions settled by the signed-off spec; nothing beyond the request, nothing irreversible
- 2026-11-17 Stage 2: pass
- 2026-11-17 review: ran code (L, Public Surface not none), security (repo config value becomes a file path read by objects.py), self-chosen: L
- 2026-11-17 Stage 2: pass
- 2026-11-17 Stage 2: pass
- 2026-11-17 Stage 2: pass
- 2026-11-17 Stage 2: pass
- 2026-11-17 Stage 3: pass

## Deviations
- 2026-11-17 setup What: the plugin repo isn't set up for sdlc (no .sdlc/config.json). Why: it's the plugin itself, as for every earlier feature here. Effect: verify.py runs only the AC tests; the full suite is run by hand before Ship.
- 2026-11-17 test-change tests/test_objects.py What: the long-file case pads with 200 text lines, not 200 newlines. Why: brief.py's cut drops trailing blank lines, so the check counts lines the same way; a file of trailing newlines isn't long.
- 2026-11-17 scripts/objects.py setting, path, rspec_domain, sections, parse, avoided, ui_files, file_problems, feature_problems, check, unused_code_names, main; scripts/brief.py domain What: module-level helpers. Why: objects.py's check, shared with brief.py and doctor.py. Effect: internal to the plugin's scripts; the public surface is the config key and objects.py check.
- 2026-11-17 tests/test_objects_review.py CONTRIBUTING.md docs/wiki/Where-things-live.md What: round-1 fix tests in a new file; the new script and template listed in the CONTRIBUTING tree and Where-things-live. Why: review r1 (H1, H2, M1-M3, S1-S3, L1, L2, L4, FP1). Effect: tests and docs only.
- 2026-11-17 docs/runbook.md What: smoke test part E gains a domain-model item (8). Why: the stale-docs audit; a release checks the new switch. Effect: docs only.

## Open questions
-
