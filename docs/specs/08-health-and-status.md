# Spec 08: Health and status

Tell the user what state their machine, the plugin and the repo are in, and what to do about anything wrong, without changing anything.

**Entry points:** `/sdlc:doctor`, `/sdlc:status` · **Source:** `scripts/doctor.py`, `commands/doctor.md`, `commands/status.md`, `scripts/scaffold.py status`

## User scenarios

1. **After install.** When the user runs `/sdlc:doctor` in a repo that isn't set up, then machine and plugin checks are shown and the repo check says "not set up" with `/sdlc:setup` as the fix; nothing fails.
2. **Something broke.** Given a hookify rule with a broken regex, when `/sdlc:doctor` runs, then that check fails, naming the file and the runbook procedure, and the exit code is 1.
3. **Where am I.** When the user runs `/sdlc:status`, then they see setup state and drift, then one line per feature.

## Requirements

### Doctor

| ID | Requirement | Guarantee |
|---|---|---|
| HLT-FR-001 | Read-only: running doctor changes no files. | `[enforced]` test_doctor › test_doctor_changes_nothing |
| HLT-FR-002 | Every check is ok, warn, fail or skip with a one-line detail and, if not ok, a fix (a command or a runbook procedure). Exit 1 if any check fails. JSON or Markdown table output. | `[enforced]` test_doctor › test_markdown_output, test_repo_not_set_up_is_a_warning_not_a_failure |
| HLT-FR-003 | Environment: Python ≥ 3.9, git (fail if missing), gh (warn), the security reviewer environment (via the security hooks' own lookup; skip if model reviews are switched off; when not built, explains that it needs credentials reaching the hooks). | `[enforced]` test_doctor › test_environment_and_plugin_checks_always_run |
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

## Non-goals

- Fixing problems automatically; checking whether the plugin is enabled in `/plugin` (not visible to a script).
