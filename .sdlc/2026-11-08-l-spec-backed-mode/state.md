# 2026-11-08-l-spec-backed-mode
Status: active
Process: 3
Change: .sdlc/2026-11-08-l-spec-backed-mode/change.md   (this feature's record for people)
Track: L   (sized up because: several distinct parts: contracts, spec-backed trace and questions, recorded tests, test lock, setup keys; footprint: 30 files)
Risk: low
Top model: opus   (fable only if the user chose it)
Commands: test: (none recorded)
Started: 2026-11-08
Base: 03a25e3
Owner: tammai.it@gmail.com
Tool: claude-code
Current: Stage 2 – Build

## Stages
- [x] 1 Define   — the change file, the plan sections below
- [ ] 2 Build
- [ ] 3 Review   — the change file's ## Review
- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)

## How the build runs
inline: a port from the rc commits onto sdlc--v3.4.0

## Handoff
- rc commits: 5ecc109 (rc.1), ff2ac10 (rc.2), 4e7a911 (rc.3), aa83fbb (contracts 1.1.1)

## Tasks
1. **Contracts 1.1.1 vendored** — AC-010
   - Files: `.gitattributes`, `scripts/contracts/v1/MANIFEST`, `scripts/contracts/v1/contracts.py`, `tests/test_contracts_vendor.py`
2. **Spec-backed switch and test lock** — AC-001 AC-002 AC-004
   - Files: `scripts/spec_lock.py`, `scripts/verify.py`, `scripts/state.py`, `tests/test_spec_backed_mode.py`
3. **Recorded acceptance tests and guard** — AC-005 AC-006
   - Files: `scripts/verify.py`, `hooks/role_guard.py`, `hooks/hooks.json`, `hosts/hook.py`, `tests/test_recorded_tests.py`
4. **Spec-backed change files and spec questions** — AC-007 AC-008
   - Files: `scripts/brief.py`, `scripts/autopilot.py`, `scripts/state.py`, `tests/test_spec_backed.py`, `tests/test_spec_backed_fixes.py`
5. **Accept keys and doctor** — AC-003 AC-009
   - Files: `scripts/scaffold.py`, `scripts/doctor.py`, `migrations/3.5.0-accept-keys.md`, `tests/test_spec_backed_mode.py`
6. **Docs and release 3.5.0-rc.6**
   - Files: `skills/orchestrator/references/flow.md`, `skills/orchestrator/references/backlog-slices.md`, `templates/change-template.md`, `skills/setting-up-projects/references/brownfield.md`, `skills/setting-up-projects/references/greenfield.md`, `docs/specs/rebuild-upgrade/03-sdlc.md`, `docs/specs/rebuild-upgrade/01-shared-contracts.md`, `CHANGELOG.md`, `plugin.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json`, `plugins/sdlc-extras/.claude-plugin/plugin.json`, `plugins/sdlc-stepper/.claude-plugin/plugin.json`

## Public Surface
- command `state.py cite` — AC-007
- command `state.py question` — AC-008
- command `state.py questions` — AC-008
- command `state.py lock` — AC-004
- command `verify.py red --at` — AC-004
- command `scaffold.py add-config-keys` — AC-009
- config `accept.start` — AC-005
- config `accept.base_url` — AC-005
- config `spec_lock` — AC-004

## Gate log
- 2026-11-08 orchestrator rule msg_39845068ffdb: review capped at 2 rounds; past it only a high security or privacy finding is fixed, the rest are tickets ('waived round 3: tickets')
- 2026-11-08 Stage 1: pass — plan self-approved (L): (1) every kept item and the standalone guarantee map to AC-001..010, removed items under Out of scope; (2) no open questions; (3) decisions settled by the brief, the revised Scope and the rc code; (4) no proposals kept, nothing irreversible

## Deviations
- 2026-11-08 red step What: AC-004..AC-010 were recorded red against 3.4.0's code (the ported files and contracts set aside), AC-001..AC-003 against rc.5's code (aa83fbb), then the port was restored; rc.5's red wrote a ## Test lock that was removed. Why: the code is a port that existed before its tests, and the standalone ACs assert 3.4.0 behaviour, which only the rc code breaks. Effect: every AC was seen failing on the code it guards against.
- 2026-11-08 port scripts/contracts/v1/acceptance-manifest.schema.json scripts/contracts/v1/cost-line.schema.json scripts/contracts/v1/criteria-lock.schema.json scripts/contracts/v1/departures.schema.json scripts/contracts/v1/finding.schema.json scripts/contracts/v1/fixtures/bundle/invalid/seed-outside-bundle/http/F-ISS-01.AC2.yaml scripts/contracts/v1/fixtures/bundle/invalid/seed-outside-bundle/manifest.json scripts/contracts/v1/fixtures/bundle/invalid/seed-outside-bundle/seed/team-eng-11-issues.yaml scripts/contracts/v1/fixtures/bundle/invalid/sha256-mismatch/http/F-ISS-01.AC2.yaml scripts/contracts/v1/fixtures/bundle/invalid/sha256-mismatch/manifest.json scripts/contracts/v1/fixtures/bundle/invalid/sha256-mismatch/seed/team-eng-11-issues.yaml scripts/contracts/v1/fixtures/bundle/invalid/url-in-test/http/F-ISS-01.AC2.yaml scripts/contracts/v1/fixtures/bundle/invalid/url-in-test/manifest.json scripts/contracts/v1/fixtures/bundle/invalid/url-in-test/seed/team-eng-11-issues.yaml scripts/contracts/v1/fixtures/bundle/valid/trackr/http/F-ISS-01.AC2.yaml scripts/contracts/v1/fixtures/bundle/valid/trackr/manifest.json scripts/contracts/v1/fixtures/bundle/valid/trackr/seed/team-eng-11-issues.yaml scripts/contracts/v1/fixtures/cost/invalid/negative-wall-s.jsonl scripts/contracts/v1/fixtures/cost/valid/cost.jsonl scripts/contracts/v1/fixtures/departures/invalid/no-decided-by.yaml scripts/contracts/v1/fixtures/departures/invalid/proposed-blocks.yaml scripts/contracts/v1/fixtures/departures/valid/departures.yaml scripts/contracts/v1/fixtures/finding/invalid/borrowed-question-shape.json scripts/contracts/v1/fixtures/finding/invalid/no-verified-by.json scripts/contracts/v1/fixtures/finding/invalid/route-mismatch.json scripts/contracts/v1/fixtures/finding/valid/BH-0007.json scripts/contracts/v1/fixtures/finding/valid/BH-0008-not-reproduced.json scripts/contracts/v1/fixtures/finding/valid/SQ-0001-spec-question.json scripts/contracts/v1/fixtures/http/invalid/capture-used-before-taken.yaml scripts/contracts/v1/fixtures/http/invalid/json-not-a-list.yaml scripts/contracts/v1/fixtures/http/invalid/no-steps.yaml scripts/contracts/v1/fixtures/http/valid/F-ISS-01.AC2.yaml scripts/contracts/v1/fixtures/lock/invalid/level-2-without-test.json scripts/contracts/v1/fixtures/lock/invalid/tag-with-brackets.json scripts/contracts/v1/fixtures/lock/valid/trackr/criteria.lock.json scripts/contracts/v1/fixtures/yaml/invalid/anchor.yaml scripts/contracts/v1/fixtures/yaml/invalid/block-scalar.yaml scripts/contracts/v1/fixtures/yaml/invalid/duplicate-key.yaml scripts/contracts/v1/fixtures/yaml/invalid/empty-key.yaml scripts/contracts/v1/fixtures/yaml/invalid/unclosed-flow-value.yaml scripts/contracts/v1/fixtures/yaml/valid/scalars.yaml scripts/contracts/v1/test_contracts.py tests/test_autopilot_spec_questions.py tests/test_pre_release.py tests/test_test_lock.py Build SchemaUnsupported YamlError accept_keys accept_target answers backlog_status brief bundle_check bundle_problem canon check_bundle check_cost check_criteria check_departures check_finding check_http_test check_id check_lock check_story cited cmd_add_config_keys commit_of criteria_hashes criteria_text criterion_line criterion_text_sha256 entries feature_bases file_sha finding_route header_for hits inside load lock_failures lock_paths lock_problem main parse_yaml protected_paths question_line red_at red_one resolve run run_fixtures run_http run_once schema_errors seal section_lines segments set_section shell_write spec_backed spec_backed_repo sum_cost test_lock vendor_check What: the vendored contracts files and fixtures, the ported rc tests in new files, and the functions the port brings (contracts.py, spec_lock.py, verify.py, state.py, role_guard.py, scaffold.py, doctor.py, brief.py, autopilot.py). Why: a port of rc.1-rc.3 and contracts 1.1.1 onto 3.4.0; internal functions, not a public surface. Effect: none beyond the spec-backed mode the ACs cover.

## Open questions
-
