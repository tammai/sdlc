# Spec 08: Health and status

Tell the user what state their machine, the plugin and the repo are in, and what to do about anything wrong, without changing anything; and, on request, clean up the working files of finished features.

**Entry points:** `/sdlc:doctor`, `/sdlc:status`, `/sdlc:prune` · **Source:** `scripts/doctor.py`, `commands/doctor.md`, `commands/status.md`, `scripts/scaffold.py status`, `scripts/prune.py`, `commands/prune.md`

## User scenarios

1. **After install.** When the user runs `/sdlc:doctor` in a repo that isn't set up, then machine and plugin checks are shown and the repo check says "not set up" with `/sdlc:setup` as the fix; nothing fails.
2. **Something broke.** Given a hookify rule with a broken regex, when `/sdlc:doctor` runs, then that check fails, naming the file and the runbook procedure, and the exit code is 1.
3. **Where am I.** When the user runs `/sdlc:status`, then they see setup state and drift, then one line per feature.
4. **Clean up.** Given a feature marked done on main 60 days ago, when the user runs `/sdlc:prune` and approves, then its plan, reports, review and checklists are deleted in one commit and its spec and state stay.

## Requirements

### Doctor

| ID | Requirement | Guarantee |
|---|---|---|
| HLT-FR-001 | Read-only: running doctor changes no files. | `[enforced]` test_doctor › test_doctor_changes_nothing |
| HLT-FR-002 | Every check is ok, warn, fail or skip with a one-line detail and, if not ok, a fix (a command or a runbook procedure). Exit 1 if any check fails. JSON or Markdown table output. | `[enforced]` test_doctor › test_markdown_output, test_repo_not_set_up_is_a_warning_not_a_failure |
| HLT-FR-003 | Environment: Python ≥ 3.9, `python3` that runs (fail if missing or exits non-zero: the hooks start with it and fail open without it), git (fail if missing), gh (warn), jq (warn: the ralph-loop stop hook needs it), the security reviewer environment (via the security hooks' own lookup; skip if model reviews are switched off; when not built, explains that it needs credentials reaching the hooks). | `[enforced]` test_doctor › test_environment_and_plugin_checks_always_run |
| HLT-FR-004 | Plugin: version; every script referenced in `hooks.json` exists. | `[enforced]` test_doctor › test_environment_and_plugin_checks_always_run |
| HLT-FR-005 | Repo setup: not set up (warn, `/sdlc:setup`), in progress (warn, with steps done), complete; version drift (behind → warn with pending migrations; plugin too old → fail); corrupt config or lock → fail. | `[enforced]` test_doctor › test_healthy_set_up_repo, test_setup_in_progress, test_version_drift, test_corrupt_lock_fails |
| HLT-FR-006 | Plugin files missing or generated files hand-edited → warn (upgrade restores or regenerates); seeded files the user edited are listed as info. | `[enforced]` test_doctor › test_missing_and_hand_edited_plugin_files |
| HLT-FR-007 | Commands: missing required commands, missing package paths or duplicate names → fail; tools not on PATH → warn, per package. | `[enforced]` test_doctor › test_missing_commands_fail, test_command_tools_not_installed_warn, test_monorepo_commands_per_package |
| HLT-FR-008 | Brownfield without a baseline → warn; `.sdlc/.work/` not git-ignored → warn. | `[enforced]` test_doctor › test_brownfield_without_baseline, test_gitignore |
| HLT-FR-009 | Your rules whose `paths:` match no files → warn (the plugin's own `sdlc-*` policy rules are skipped: they wait for files to exist); hookify rules that don't parse or have a bad regex → fail. | `[enforced]` test_doctor › test_rules_whose_paths_match_nothing, test_hookify_rules_parse |
| HLT-FR-010 | `CLAUDE.md` over 60 lines → warn; `knowledge/` without an index or with broken links → warn. | `[enforced]` test_doctor › test_claude_md_budget, test_knowledge_index_links |
| HLT-FR-011 | Features: malformed `state.md` or several active → warn; freshness state shown, corrupt → warn. | `[enforced]` test_doctor › test_feature_state, test_freshness_state |
| HLT-FR-012 | The command presents the table, explains failures, groups warnings, and offers only safe local fixes, applying just the ones the user picks; never installs tools or changes the plugin without an explicit yes. | `[instructed]` commands/doctor.md |

### Status

| ID | Requirement | Guarantee |
|---|---|---|
| HLT-FR-020 | Setup state and scaffold vs plugin version first; suggests `/sdlc:setup`, `/sdlc:upgrade` (naming pending migrations) or a plugin update as needed; lists edited plugin files only if any. | `[instructed]` commands/status.md; data `[enforced]` test_scaffold › test_status_before_setup, test_drift, test_status_lists_pending_migrations |
| HLT-FR-021 | One line per feature: feature · track · current stage · last gate; then open questions and deviations for active features. Changes nothing. | `[instructed]` commands/status.md |

### Prune

| ID | Requirement | Guarantee |
|---|---|---|
| HLT-FR-030 | A feature qualifies only when its `state.md` on the main branch (`main`, else `master`, or `--main`) says `Status: done` and hasn't changed for `--older-than` days (default 45). It's also skipped when its folder has uncommitted changes or its working-tree `state.md` no longer says done, so only what git already holds is deleted. Anything else is skipped with the reason, and `apply` refuses it. | `[enforced]` test_prune › test_active_feature_is_never_pruned, test_uncommitted_work_is_never_pruned |
| HLT-FR-031 | It deletes `plan.md`, `test-report.md`, `qa-report.md`, `review.md`, `checklists/`, and `security.md` unless `Risk: high`; everything else in the folder stays. | `[enforced]` test_prune › test_done_merged_feature_keeps_only_its_record |
| HLT-FR-032 | The command lists first, asks which features to prune, and commits the deletions in one commit without pushing. | `[instructed]` commands/prune.md |

## Non-goals

- Fixing problems automatically; checking whether the plugin is enabled in `/plugin` (not visible to a script).
