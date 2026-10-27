# Spec 08: Health and status

Tell the user what state their machine, the plugin and the repo are in, and what to do about anything wrong, without changing anything. On request, also clean up the working files of finished features, and trim what Claude Code loads into every call for a project.

**Entry points:** `/sdlc:doctor`, `/sdlc:status`, `/sdlc:prune`, `/sdlc:context-diet` · **Source:** `scripts/doctor.py`, `commands/doctor.md`, `commands/status.md`, `scripts/scaffold.py status`, `scripts/prune.py`, `commands/prune.md`, `scripts/context_diet.py`, `skills/setting-up-projects/references/trimming-context.md`, `commands/context-diet.md`

## User scenarios

1. **After install.** When the user runs `/sdlc:doctor` in a repo that isn't set up, then machine and plugin checks are shown and the repo check says "not set up" with `/sdlc:setup` as the fix; nothing fails.
2. **Something broke.** Given a hookify rule with a broken regex, when `/sdlc:doctor` runs, then that check fails, naming the file and the runbook procedure, and the exit code is 1.
3. **Where am I.** When the user runs `/sdlc:status`, then they see setup state and drift, then one line per feature.
4. **Clean up.** Given a feature marked done on main 60 days ago, when the user runs `/sdlc:prune` and approves, then its plan, reports, review and checklists are deleted in one commit and its spec and state stay.
5. **Context diet.** Given a project with no Figma files and the Figma plugin enabled for the user, when the user runs `/sdlc:context-diet` and approves, then `.claude/settings.local.json` turns Figma off for this project only, the user's other keys stay, and nothing is committed.

## Requirements

### Doctor

| ID | Requirement | Guarantee |
|---|---|---|
| HLT-FR-001 | Read-only: running doctor changes no files. | `[enforced]` test_doctor › test_doctor_changes_nothing |
| HLT-FR-002 | Every check is ok, warn, fail or skip with a one-line detail and, if not ok, a fix (a command or a runbook procedure). Exit 1 if any check fails. JSON or Markdown table output. | `[enforced]` test_doctor › test_markdown_output, test_repo_not_set_up_is_a_warning_not_a_failure |
| HLT-FR-003 | Environment: Python ≥ 3.9, "hook python": `hooks/sg-python.sh`, which finds the Python every hook in `hooks.json` starts (directly once remembered), run under Git Bash finds a working Python 3 (fail otherwise: the hooks fail open without it; System32's WSL bash doesn't count), git (fail if missing), gh (warn), jq (warn: the `sdlc-extras` Ralph loop's stop hook needs it), the security reviewer environment (via the security hooks' own lookup; skip if model reviews are switched off; when not built, explains that it needs credentials reaching the hooks). | `[enforced]` test_doctor › test_environment_and_plugin_checks_always_run, test_hook_python_that_does_not_run_fails |
| HLT-FR-004 | Plugin: version; every script referenced in `hooks.json` exists. | `[enforced]` test_doctor › test_environment_and_plugin_checks_always_run |
| HLT-FR-005 | Repo setup: not set up (warn, `/sdlc:setup`), in progress (warn, with steps done), complete; version drift (behind → warn with pending migrations; plugin too old → fail); corrupt config or lock → fail. | `[enforced]` test_doctor › test_healthy_set_up_repo, test_setup_in_progress, test_version_drift, test_corrupt_lock_fails |
| HLT-FR-006 | Plugin files missing or generated files hand-edited → warn (upgrade restores or regenerates); seeded files the user edited are listed as info. | `[enforced]` test_doctor › test_missing_and_hand_edited_plugin_files |
| HLT-FR-007 | Commands: missing required commands, missing package paths or duplicate names → fail; tools not on PATH → warn, per package. | `[enforced]` test_doctor › test_missing_commands_fail, test_command_tools_not_installed_warn, test_monorepo_commands_per_package |
| HLT-FR-008 | Brownfield without a baseline → warn; `.sdlc/.work/` not git-ignored → warn; the control contract's files (`.sdlc/state/*.json`, `*.events.jsonl`, `*.commands/`) not git-ignored → warn, fix `/sdlc:upgrade`. | `[enforced]` test_doctor › test_brownfield_without_baseline, test_gitignore, test_gitignore_set_up_before_the_control_contract_warns |
| HLT-FR-009 | Your rules whose `paths:` match no files → warn (the plugin's own `sdlc-*` policy rules are skipped: they wait for files to exist); hookify rules that don't parse or have a bad regex → fail. | `[enforced]` test_doctor › test_rules_whose_paths_match_nothing, test_hookify_rules_parse |
| HLT-FR-010 | `CLAUDE.md` over 60 lines → warn; `knowledge/` without an index or with broken links → warn. | `[enforced]` test_doctor › test_claude_md_budget, test_knowledge_index_links |
| HLT-FR-012 | A stale `AGENTS.md` block or Claude Code mirror → warn; a Claude-only line in its sources → fail ([spec 11](11-multi-agent.md) AGT-FR-005). | `[enforced]` test_doctor › test_agents_md_out_of_date_warns |
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
| HLT-FR-031 | It deletes the working files: `plan.md`, the parts' `plan-B<n>.md` files, `qa-report.md` and `checklists/` (and a 1.x feature's `test-report.md`). It keeps the record: `intent.md`, `spec.md` and state, and `review.md` on a 2.0 feature (`Process: 2`: it is the review's record) or on `Risk: high` (its `## Security` section), with an older `security.md`; on a 1.x feature at `Risk: low` it deletes `review.md` and `security.md`. Everything else in the folder stays. | `[enforced]` test_prune › test_a_2_0_feature_keeps_its_review_and_drops_its_working_plans, test_done_merged_feature_keeps_only_its_record, test_done_feature_in_the_new_layout_keeps_only_its_record (part plans), test_a_high_risk_feature_keeps_its_review_with_the_security_section |
| HLT-FR-032 | The command lists first, asks which features to prune, and commits the deletions in one commit without pushing. | `[instructed]` commands/prune.md |

### Context diet

| ID | Requirement | Guarantee |
|---|---|---|
| HLT-FR-040 | `context_diet.py` reports each source (enabled plugin, personal skill, command or agent, claude.ai-synced plugin or skills) with its estimated tokens per call (listed name and description, chars/4), item count and MCP servers. Enabled is the user's `enabledPlugins` overridden by the project's `.claude/settings.json`, then `.claude/settings.local.json`. A disabled plugin costs 0, and `~/.claude/skills/synced/` counts as synced, not personal. | `[enforced]` test_context_diet › test_fixture_home_gives_sources_costs_and_duplicate_verdicts |
| HLT-FR-041 | When sdlc is enabled for the project, the standalone `security-guidance` and `code-review` get verdict `duplicate` (`code-simplifier` is no longer bundled: it moved to `sdlc-extras`). A known LSP plugin gets `keep` or `off` by whether its language is in the project. Every other verdict is `null`, left to the session. | `[enforced]` test_context_diet › test_fixture_home_gives_sources_costs_and_duplicate_verdicts |
| HLT-FR-042 | A missing or malformed settings file or `installed_plugins.json`, or an enabled plugin with no install folder, is listed in `problems`. The script still prints JSON and exits 0. It writes nothing; `--home` and `--root` point it at another home and project. | `[enforced]` test_context_diet › test_malformed_installed_plugins_is_reported_not_a_crash |
| HLT-FR-043 | The context diet shows one row per source (est. tokens/call, verdict, one-line reason). It proposes only `enabledPlugins` keys set to `false` in `.claude/settings.local.json`, merged with what's there, and shows the saving per call. It writes only after approval. If the file isn't ignored by git, it offers `.git/info/exclude`, never `.gitignore`. It never stages the file, and never adds a `true`, sdlc's own key included (a session that loaded sdlc with `--plugin-dir` would load a second copy). | `[instructed]` skills/setting-up-projects/references/trimming-context.md |
| HLT-FR-044 | Personal skills that look unrelated are listed with "move them into the projects that use them", and synced plugins are reported only. It never edits `~/.claude/settings.json` or moves skills unless asked. It ends with "new sessions only; check `/context`". | `[instructed]` skills/setting-up-projects/references/trimming-context.md |
| HLT-FR-045 | `/sdlc:context-diet` works without `.sdlc/`. It's Claude Code only: it isn't built into the Codex or Antigravity skills, and on another agent the reference tells it to stop. Setup offers it as the `context-diet` step ([spec 01](01-setup-upgrade-eject.md)). | `[instructed]` commands/context-diet.md, skills/setting-up-projects/SKILL.md |

## Non-goals

- Measuring real token counts or MCP tool-definition size: the context diet's numbers are estimates, and `/context` is the ground truth. Doctor doesn't check the floor, which would mean scanning `~/.claude` from doctor. MCP servers declared only in a marketplace entry (not in the plugin's `.mcp.json` or `plugin.json`) aren't flagged.
- Fixing problems automatically; checking whether the plugin is enabled in `/plugin` (not visible to a script).
