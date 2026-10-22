# Spec 04: Verification

Stage 5 decides whether the work does what the spec says, using evidence that is fresh, independent and honest about pre-existing failures: tests that fail without the change, and a QA run of the feature that never looks at the code.

**Entry points:** Stage 5 of the orchestrator · **Source:** `skills/orchestrator/SKILL.md` §5, `agents/verifier.md`, `agents/qa-tester.md`, `hooks/verify_freshness.py`, `templates/project/baseline.md`

## User scenarios

1. **Pass on the first round.** Given Stage 5 with a fresh full test run, when a new verifier runs everything and proves each acceptance criterion, then the round is PASS and the gate passes.
2. **Stale results.** Given Stage 5 and a full test run, when code changes afterwards (by any tool, including a formatter or subagent), then finishing the turn is blocked with the reason and the exact command to rerun.
3. **Monorepo.** Given packages `api` and `web`, both fresh, when `services/api/handler.go` changes, then only `api` is stale and the block names `cd services/api && go test ./...`.
4. **Old failure.** Given a failure listed in `.sdlc/baseline.md`, when the verifier sees it, then it doesn't fail the round; if a listed failure now passes, the verifier removes it.
5. **Scenario broken in use.** Given an M feature whose tests all pass, when the `qa-tester` runs User Story 1 scenario 2 and doesn't see the spec's *Then*, then it reports the steps and observed output and the round fails.
6. **Test that proves nothing.** Given a bug fix whose repro test also passes with the fix reverted, then the verifier reports it doesn't prove the change and the round fails.
7. **Round cap.** Given three failed rounds, then the orchestrator stops and brings the user what still fails, what each round changed, and a root-cause hypothesis.

## Requirements

### Rounds and the verifier

| ID | Requirement | Guarantee |
|---|---|---|
| VER-FR-001 | Each round spawns a new `verifier` agent; never resume an earlier one, never verify inline. | `[instructed]` orchestrator §5 |
| VER-FR-002 | The verifier records commit, dirty state and time; runs build, lint, typecheck and the full suite fresh; proves every acceptance criterion with a named test (opened to confirm it asserts the behavior) or an observed command output, or reports none. | `[instructed]` verifier.md |
| VER-FR-003 | The verifier writes only `test-report.md` and may only remove passing items from the baseline. | `[instructed]` verifier.md |
| VER-FR-004 | Failures are classified new or baseline; only new failures fail the round; a lint/type count that rises counts as new; adding to the baseline needs the user and a Deviation. | `[instructed]` verifier.md, orchestrator §5 |
| VER-FR-005 | M and L: fresh `qa-tester`, `pr-test-analyzer` and `silent-failure-hunter` in parallel each round. S: verifier only, with the repro test among the evidence and failing on Base. | `[instructed]` orchestrator §5 |
| VER-FR-006 | Gate: latest round's verifier PASS on the current commit and (M, L) a qa-tester PASS on a commit with the same non-test files, every criterion evidenced, no test gap rated ≥ 8, no high-severity silent failure, no skipped or retried-until-green test touching the feature. On a pass, `Verified:` in `state.md` records the commit; Stage 8 goes back to Stage 5 if non-test code changed since. | `[instructed]` orchestrator §5, §8 |
| VER-FR-007 | At most 3 rounds, then stop and report to the user. Each round is logged in `state.md`. | `[instructed]` orchestrator §5 |

### Red-green and QA

| ID | Requirement | Guarantee |
|---|---|---|
| VER-FR-030 | The verifier makes a throwaway worktree at `Base:` under `.sdlc/.work/redgreen/`, runs `install` there, checks the environment with a control test that passes in the main worktree (if it doesn't, "red-green not run"; an environment error never counts as red), copies in the feature's new and changed test files (committed or not) and runs them there. A test that passes there doesn't count as evidence for a criterion. The main worktree is never touched; the worktree is removed afterwards; if it can't be made, "red-green not run: <reason>". | `[instructed]` verifier.md |
| VER-FR-031 | The `qa-tester` is briefed with the feature dir, round, commands and whether a browser tool exists, never the diff, plan or tests, and is told not to read source. | `[instructed]` orchestrator §5, qa-tester.md |
| VER-FR-032 | It runs every acceptance scenario and spec edge case against the running software (CLI, HTTP, browser, or a script against the public API) and up to five probes of its own, recording steps and observed output. | `[instructed]` qa-tester.md |
| VER-FR-033 | It writes only `qa-report.md` (a `## Round N` section) and scratch files under `.sdlc/.work/qa/`; never installs anything; reports "not run: <reason>" when it can't run a scenario. | `[instructed]` qa-tester.md |
| VER-FR-034 | Its verdict fails on a failed scenario or spec edge case, or a Blocker probe (crash, hang, data loss, leaked internals or wrong result, on an input the spec covers). Probes stay inside the spec's stated limits and never touch Non-Goals; a failure that needs a new requirement is Major and goes to the user. "Not run" doesn't fail the round but is named at the gate. Major findings go to `review.md`. | `[instructed]` qa-tester.md, orchestrator §5 |
| VER-FR-035 | The model router denies `qa-tester` below `opus` on `Risk: high`, like the verifier. | `[enforced]` test_model_router › test_qa_tester_below_opus_is_denied_on_high_risk |
| VER-FR-036 | The qa-tester leaves the working tree as it found it: files the running software created are removed, and any it couldn't remove are reported. | `[instructed]` qa-tester.md |
| VER-FR-037 | A later round reruns the qa-tester only when non-test files changed since its last PASS; otherwise that PASS carries over and the round's log line says so. | `[instructed]` orchestrator §5 |

### Freshness hook

| ID | Requirement | Guarantee |
|---|---|---|
| VER-FR-010 | Active only while a feature's `state.md` has `Status: active` and `Current: Stage 5`; otherwise a no-op. | `[enforced]` test_verify_freshness › test_no_sdlc_dir_is_noop, test_other_stage_is_noop, test_stage_5_but_not_active_is_noop, test_stage_50_is_not_stage_5 |
| VER-FR-011 | Entering Stage 5 without a full test run blocks the turn's end. | `[enforced]` › test_entering_stage_5_without_a_test_run_blocks |
| VER-FR-012 | Edit, Write, MultiEdit and NotebookEdit on a code file mark results stale; Markdown/text files and `.sdlc/`, `knowledge/`, `.claude/`, `docs/` don't; files outside the project are ignored. | `[enforced]` › test_code_edit_after_test_run_makes_stale, test_rerun_after_edit_makes_fresh_again, test_all_edit_tools_mark_stale, test_non_code_edits_keep_results_fresh, test_edit_outside_project_is_ignored |
| VER-FR-013 | In a git repo, changes made any other way (shell, formatter, subagent, new or deleted files) are detected at the turn's end by diffing the worktree against the tree recorded at the last full run; reverting makes results fresh again; committing tested code keeps them fresh; ignored files don't count; the real git index is never touched. | `[enforced]` › test_bash_edit_after_test_run_makes_stale, test_new_and_deleted_files_make_stale, test_reverting_an_edit_makes_fresh_again, test_committing_tested_code_keeps_fresh, test_non_code_and_ignored_changes_keep_fresh, test_real_git_index_is_untouched |
| VER-FR-014 | A full run is the configured test command (or, without setup, the `state.md` `test:` command, else a generic runner), matched as whole words; generic runners don't count once a command is configured. | `[enforced]` › test_full_test_run_makes_fresh, test_non_test_bash_does_not_make_fresh, test_generic_test_commands_count, test_config_test_command_counts_and_generic_runners_do_not, test_state_test_command_is_required_when_set, test_command_must_match_whole_words, test_state_test_command_still_counts_with_config |
| VER-FR-015 | Partial runs never count: name filters (`-t`, `-k`, `--grep`, `-run`, `--filter`, `.only`, `--bail`) added after the test command (flags inside the configured command, like unittest's `-t .`, are part of it), a test file, a pytest node id, a single Go package; shell redirects and pipes don't confuse detection; interrupted runs don't count. | `[enforced]` › test_filtered_runs_do_not_count, test_single_test_file_runs_do_not_count, test_whole_suite_arguments_still_count, test_state_test_command_with_a_test_file_does_not_count, test_state_test_command_still_rejects_filters, test_flags_inside_the_test_command_are_not_filters, test_interrupted_test_run_does_not_count |
| VER-FR-016 | A configured command counts only in its own directory (the last `cd` before it, else the session's cwd). | `[enforced]` › test_config_command_only_counts_in_its_own_directory, test_session_cwd_counts_as_the_run_directory |
| VER-FR-017 | Monorepo: freshness per package. All start stale (without a base, see VER-FR-022); a package goes fresh only from its own test command in its path; an edit marks its owning package stale, a file outside every package marks all; worktree changes are attributed per package; a root `commands.test` run from the root makes every package fresh. | `[enforced]` › test_every_package_starts_stale, test_each_package_goes_fresh_in_its_own_directory, test_edit_only_makes_its_own_package_stale, test_shared_root_file_makes_every_package_stale, test_package_filters_still_partial, test_root_test_command_covers_every_package, test_worktree_changes_are_attributed_per_package |
| VER-FR-018 | The block message names each stale scope, the reason (files, up to five plus a count) and the exact command to rerun. | `[enforced]` › test_block_message_names_the_test_command, test_block_message_names_the_config_command, test_lists_at_most_five_changed_files |
| VER-FR-019 | A second consecutive block only warns, to avoid loops. | `[enforced]` › test_second_consecutive_stop_only_warns |
| VER-FR-020 | Switching feature resets state; the full run records the commit; state lives in `.sdlc/.work/verify-freshness.json`. | `[enforced]` › test_switching_feature_resets_freshness, test_records_git_head_on_fresh_run |
| VER-FR-021 | Never fails the session: bad input, a corrupt state file or its own error exits 0 silently. Works from a subdirectory cwd. | `[enforced]` › test_bad_input_exits_zero_silently, test_corrupt_state_file_is_recovered, test_found_from_subdirectory_cwd |
| VER-FR-022 | Monorepo with a `Base:` commit in `state.md`: on entering Stage 5 only packages with changes since the base (committed, uncommitted or untracked) start stale; untouched ones start fresh from a worktree snapshot, so later changes to them still count. No base, or no changes detected: every package starts stale. | `[enforced]` › test_only_packages_changed_since_the_feature_base_start_stale, test_untouched_package_still_goes_stale_when_it_changes_later, test_without_a_base_every_package_starts_stale, test_no_changes_since_base_keeps_everything_stale |

## Edge cases

- Stop with no git repo: edit-tool tracking only (no worktree diff).
- A worktree diff that can't be computed (tree garbage-collected, slow repo over 5 s) leaves the state as it was rather than blocking.

## Non-goals

- Judging whether tests are good (that's the verifier and `pr-test-analyzer`); running tests itself.
- The qa-tester writing tests into the repo; e2e or visual-regression suites; load testing beyond a stated SC; mutation testing.
- QA on the S track.

## Known gaps

- The qa-tester's blindness to the code is instructed only: it has Read and Bash, which it needs to run the feature. Same for the verifier's "never edit source".
- Red-green runs `install` in a fresh worktree each round: it takes time and may use the network.
- Red-green on a refactor: tests that pass on Base are expected, and the verifier lists them; a criterion relying only on such a test has no evidence.
- `.only` inside a test file and unusual custom filters aren't detected by the hook (a guardrail warns on `.only` instead).
- Whether the hook fires for tool calls made inside subagents hasn't been checked in a live session; the worktree diff at the turn's end covers their edits regardless.
