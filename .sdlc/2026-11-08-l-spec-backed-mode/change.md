# sdlc 3.5.0: spec-backed mode only (rebuilt from 3.4.0)

## Why

**Request (verbatim):** Rebuild sdlc 3.5.0 to the revised scope (user decision 2026-11-08). Read the new 'Scope (revised 2026-11-08)' section at the top of C:/Users/Admin/orca/rebuild-upgrade/03-sdlc.md first and re-copy that file. sdlc 3.5.0 keeps 3.4.0's behaviour unchanged and adds only spec-backed items, each active only when the repo holds an rspec criteria.lock.json (or spec_lock in config) or an acceptance/manifest.json:
- contracts 1.1.1 vendored (scripts/contracts/v1/, MANIFEST e385f9810ee4bd7e4640d5ab4d5b4204ea18730a5a741a237fd68bd3e96de30b, .gitattributes -text);
- S2 spec-backed change files; S3 external acceptance tests + read-only hook on manifest paths; S4 test lock in spec-backed mode only; S10 spec questions; S12 accept.start/accept.base_url keys (doctor warns only when a lock or manifest exists; no mutation key).
Removed: S1, S5 (test-auditor), S6, S7, S8 (QA row), S9, S11.
How: a fresh branch off sdlc--v3.4.0 (e.g. 2026-11-08-l-sdlc-3.5-spec-backed), porting only the kept code from the rc branches (part1 5ecc109, part2 ff2ac10, part3 4e7a911, contracts 1.1.1 aa83fbb), not deleting from rc.5. Discard the WIP branch 2026-11-08-m-qa-cost (nothing on it is needed). Proof: 3.4.0's existing tests pass unchanged (any test you must touch, ask me first), plus tests for each kept spec-backed path, including that a repo without a lock or manifest gets 3.4.0 behaviour (no C1 lint, no test lock, no new doctor warnings). Through sdlc (L), with the review the track calls for. CHANGELOG 3.5.0 states plainly: no standalone behaviour change; spec-backed mode for product-rebuild; rc.1-rc.5 items withdrawn and why. Version 3.5.0-rc.6, local annotated tag, nothing pushed.

Spec: [docs/specs/rebuild-upgrade/03-sdlc.md](../../docs/specs/rebuild-upgrade/03-sdlc.md), "Scope (revised 2026-11-08)". The 3.5.0-rc.5 eval measured M-low tokens +97% and S +62% against 3.4.0 with no quality change; this rebuild keeps only what product-rebuild needs.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| One switch, `spec_lock.spec_backed_repo(root)`: config `spec_lock`, a tracked `criteria.lock.json` outside the contracts fixtures, or `acceptance/manifest.json`; the test lock, `red --at`, `add-config-keys` and doctor's accept row all ask it | a check per feature (cited IDs) | the brief and the revised Scope say the repo holding a lock or manifest turns the mode on |
| Ported file by file from the rc commits: contracts and `spec_lock.py` from aa83fbb; `brief.py`, `autopilot.py`, `state.py` from 4e7a911; `role_guard.py`, `hosts/hook.py`, `hooks.json` from ff2ac10; `scaffold.py`, `doctor.py` from 5ecc109; `verify.py` from 4e7a911 with S1 and S11 cut | rc.5 minus the removed parts | the brief: port the kept code, not delete from rc.5; rc.4 and rc.5 only refactored kept code (no fixes to carry) |
| `verify.py` keeps 3.4.0's three-column table parser | the Level-column parser | S11 is removed; 3.4.0 tables read as before |
| A runner's `not run: ` output counts as "did not run" only for a recorded test | for every test | the vendored runner prints it; a project's own test output may contain the words |
| `add-config-keys` and the 3.5.0 migration add `accept.start`/`accept.base_url` only in a spec-backed repo; no `commands.mutation` key | rc.1's keys everywhere | standalone repos stay as 3.4.0 (no new keys, no doctor rows) |
| New tests go in new files only | appending to 3.4.0's test files | 3.4.0's tests pass unchanged, untouched |

**Proposals not asked for:** None

## Acceptance criteria

- **AC-001** Given a repo with no criteria lock and no acceptance manifest, when `verify.py red AC-001` records a test and the test is then edited, then the state file has no "## Test lock" and `verify.py` passes.
- **AC-002** Given a repo with no lock or manifest and an M feature whose AC breaks the C1 grammar, when `verify.py` runs, then its output holds no "criteria:" line and the run passes.
- **AC-003** Given a set-up repo with no lock or manifest, when `doctor.py` and `scaffold.py add-config-keys` run, then doctor has no "accept keys" or "mutation command" row and add-config-keys adds nothing.
- **AC-004** Given a repo with a tracked criteria.lock.json, when `verify.py red` records a test and the test is then edited, then `verify.py` fails with "test lock:", and passes after a "test-change" deviation and `red --at <Base>`.
- **AC-005** Given a repo with acceptance/manifest.json listing an open HTTP test, when `verify.py red` and `verify.py` run its row, then the build from "accept.start" is started with ACCEPT_BASE_URL and the test runs through the vendored runner.
- **AC-006** Given a repo with acceptance/manifest.json, when a Write or a shell command targets a test the manifest lists, then the role guard answers "deny"; in a repo without the manifest a Bash write gets no answer.
- **AC-007** Given a spec-backed change citing "F-ISS-01.AC2", when the lock's text hash changes after `state.py cite`, then `verify.py trace` reports "stale criterion".
- **AC-008** Given a spec-backed feature, when `state.py question` runs on a cited criterion, then a finding-v1 file with "source": "sdlc-question" is written and the running part is blocked until `state.py questions` sees the amended lock.
- **AC-009** Given a spec-backed repo with empty accept keys, when `doctor.py` runs, then it warns "accept keys", and `add-config-keys` adds "accept.start" and "accept.base_url".
- **AC-010** Given the vendored contracts, when `contracts.py vendor-check` runs, then it prints "matches MANIFEST (contracts 1.1.1)".

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_spec_backed_mode.py › test_a_standalone_repo_has_no_test_lock | `python3 -m unittest discover -s tests -t tests -p test_spec_backed_mode.py -k test_a_standalone_repo_has_no_test_lock` |
| AC-002 | tests/test_spec_backed_mode.py › test_a_standalone_repo_gets_no_criteria_lint | `python3 -m unittest discover -s tests -t tests -p test_spec_backed_mode.py -k test_a_standalone_repo_gets_no_criteria_lint` |
| AC-003 | tests/test_spec_backed_mode.py › test_a_standalone_repo_gets_no_new_keys_or_rows | `python3 -m unittest discover -s tests -t tests -p test_spec_backed_mode.py -k test_a_standalone_repo_gets_no_new_keys_or_rows` |
| AC-004 | tests/test_spec_backed_mode.py › test_a_spec_backed_repo_locks_its_tests | `python3 -m unittest discover -s tests -t tests -p test_spec_backed_mode.py -k test_a_spec_backed_repo_locks_its_tests` |
| AC-005 | tests/test_recorded_tests.py › test_a_recorded_http_test_runs_against_the_started_build | `python3 -m unittest discover -s tests -t tests -p test_recorded_tests.py -k test_a_recorded_http_test_runs_against_the_started_build` |
| AC-006 | tests/test_recorded_tests.py › test_recorded_tests_are_read_only | `python3 -m unittest discover -s tests -t tests -p test_recorded_tests.py -k test_recorded_tests_are_read_only` |
| AC-007 | tests/test_spec_backed.py › test_a_changed_criterion_is_stale | `python3 -m unittest discover -s tests -t tests -p test_spec_backed.py -k test_a_changed_criterion_is_stale` |
| AC-008 | tests/test_spec_backed.py › test_a_spec_question_is_a_finding_and_blocks_the_part | `python3 -m unittest discover -s tests -t tests -p test_spec_backed.py -k test_a_spec_question_is_a_finding_and_blocks_the_part` |
| AC-009 | tests/test_spec_backed_mode.py › test_a_spec_backed_repo_gets_the_accept_keys | `python3 -m unittest discover -s tests -t tests -p test_spec_backed_mode.py -k test_a_spec_backed_repo_gets_the_accept_keys` |
| AC-010 | tests/test_contracts_vendor.py › test_vendored_copy_matches_its_manifest | `python3 -m unittest discover -s tests -t tests -p test_contracts_vendor.py -k test_vendored_copy_matches_its_manifest` |

## Must never break

- 3.4.0's test files pass unchanged and are not edited (`git diff --diff-filter=M sdlc--v3.4.0 -- tests` is empty).
- The vendored folder stays byte-identical to its MANIFEST.
- A repo without a lock or manifest behaves as 3.4.0: no test lock, no criteria lint, no new config keys, no new doctor rows, no deny from the recorded-test guard.

## Out of scope

- S1 criterion lint, S5 test-auditor, S6 mutation probe, S7 test-writer, S8 QA row, S9 UI render, S11 Level column: withdrawn by the user (revised Scope).
- The eval set and token delta: the eval is run by the orchestrator against this build.

## Review
