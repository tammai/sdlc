# Spec 01: Setup, upgrade and eject

Prepare a repo once (new or existing), keep it current with the plugin, and remove the plugin cleanly, with every plugin-written file tracked by ownership.

**Entry points:** `/sdlc:setup`, `/sdlc:upgrade [--dry-run] [--revisit]`, `/sdlc:eject` · **Source:** `skills/setting-up-projects/`, `scripts/scaffold.py`, `templates/project/` · **Decisions:** [ADR 0001](../adr/0001-project-setup-upgrade-eject.md), [ADR 0002](../adr/0002-record-the-repos-own-commands.md)

## User scenarios

1. **Existing repo.** Given a repo with code and no `.sdlc/config.json`, when the user runs `/sdlc:setup`, then on a `sdlc/setup` branch it records the repo's commands (user approves), runs them and writes `.sdlc/baseline.md`, drafts knowledge and area rules for batch approval, adds rules, guardrails, lint snippets, allowlist, CI, constitution and knowledge, and asks PR or local merge.
2. **New repo.** Given an empty repo, when the user runs `/sdlc:setup a REST API for invoices`, then it asks a few stack questions, proposes a stack and commands, generates the skeleton with official tools after approval, and every command passes before continuing.
3. **Interrupted.** Given setup stopped after some steps, when `/sdlc:setup` runs again, then it continues after the last completed step.
4. **Upgrade with an edited file.** Given the user edited `.github/workflows/sdlc-verify.yml` and the plugin's generator changed, when `/sdlc:upgrade` runs, then the file is not overwritten; the user chooses merge, skip, or keep theirs for good.
5. **Eject.** Given a set-up repo, when `/sdlc:eject` runs, then a dry run is shown; on approval, plugin files are removed, edited ones only if the user agrees, and the user's work stays.

## Requirements

### Setup

| ID | Requirement | Guarantee |
|---|---|---|
| SET-FR-001 | Greenfield when the repo has no source files (README, LICENSE, docs, dotfiles ignored); brownfield otherwise; ask when unclear. | `[instructed]` setting-up-projects |
| SET-FR-002 | Needs a clean working tree; works on branch `sdlc/setup`, one commit per step. | `[instructed]` setting-up-projects |
| SET-FR-003 | Progress is recorded per step and setup resumes from it. | `[enforced]` test_scaffold › test_steps_are_resumable |
| SET-FR-004 | `init` writes the lock and a minimal config holding only overrides; an existing config is kept; a second `init` is refused unless `--force`. | `[enforced]` test_scaffold › test_init_writes_config_and_lock, test_init_writes_overrides_only, test_init_keeps_existing_config, test_init_twice_refuses_unless_forced |
| SET-FR-005 | The repo's own `install`, `test`, `lint`, `typecheck`, `build` are recorded in config (`commands`, or `packages[]` with name, path, stack, commands); `null` = not applicable. Brownfield records existing commands without inventing new ones; the user approves. | `[instructed]` brownfield.md, greenfield.md |
| SET-FR-006 | `contract` checks per scope: required commands present, package path exists, names unique, tool resolvable on PATH or as a repo-relative path (after `VAR=value` prefixes). | `[enforced]` test_scaffold › test_contract_single_project, test_contract_reports_missing_commands, test_contract_skips_env_assignments_when_finding_the_tool, test_contract_monorepo_packages |
| SET-FR-007 | `commands` prints install steps and the verify plan (default order lint, typecheck, build, test) with each step's directory, skipping `null` steps. | `[enforced]` test_scaffold › test_commands_verify_plan |
| SET-FR-008 | Greenfield: stack interview, user approves, official generators build the skeleton; all commands must pass. | `[instructed]` greenfield.md |
| SET-FR-009 | Brownfield: run each command separately and record failures in `.sdlc/baseline.md` (tests by file › name; lint/type errors as counts per rule and file); a failing install or build stops setup. | `[instructed]` brownfield.md |
| SET-FR-010 | Brownfield audit: parallel explorer agents draft conventions, git-history gotchas, decisions and area rules; nothing is written without per-batch approval. Existing AI config is migrated one approved diff per source; originals kept unless the user says delete. | `[instructed]` brownfield.md |
| SET-FR-011 | CI is generated from the commands: one toolchain setup per distinct stack (unknown stacks get a `# TODO`), install and verify steps per package with `working-directory`, `shell: bash`, OS matrix from `ci.os`; fails if there are no commands. | `[enforced]` test_scaffold › test_builtin_ci_single_project, test_builtin_ci_polyglot, test_builtin_ci_needs_commands; test_project_templates › test_generated_ci_with_plugin_defaults |
| SET-FR-012 | Common steps: generated policy rules, seeded guardrails and lint snippets, allowlist from the commands, `.gitignore` entries, constitution (with the default Simplicity principle), knowledge folder; ends by asking PR or local merge. | `[instructed]` SKILL.md; allowlist `[enforced]` test_scaffold › test_allow_from_commands |
| SET-FR-013 | Templates render `{{config.…}}` and `{{plugin_version}}` (filters `yaml_list`, `json`); a missing value fails without writing; other `{{…}}` (e.g. GitHub expressions) pass through; unknown filters fail. | `[enforced]` test_scaffold › test_render_generated_fills_placeholders_and_records, test_render_missing_placeholder_writes_nothing, test_foreign_placeholders_pass_through, test_yaml_list_and_json_filters, test_unknown_filter_is_an_error |
| SET-FR-014 | Config = plugin defaults deep-merged with project overrides; lists replace, not append. | `[enforced]` test_scaffold › test_config_merges_defaults_with_project_overrides |
| SET-FR-015 | Every shipped template renders with the defaults; policy rules have `paths:` frontmatter and stay ≤ 30 lines. | `[enforced]` test_project_templates › test_every_template_renders_without_leftover_placeholders, test_area_rules_have_paths_frontmatter_and_stay_short, test_defaults_file_is_valid_json_with_every_area; test_scaffold › test_real_rules_template_renders_with_default_config |

### Ownership and keyed merges

| ID | Requirement | Guarantee |
|---|---|---|
| SET-FR-020 | Each plugin-written file is recorded with class (generated, seeded) and hash; state is `unchanged`, `modified` or `missing`. Paths outside the project are refused. | `[enforced]` test_scaffold › test_record_and_file_states, test_record_rejects_missing_and_outside_paths |
| SET-FR-021 | `render --if-unchanged` refuses (exit 2) to overwrite an edited file or one the plugin never wrote, and overwrites an unedited one. | `[enforced]` test_scaffold › test_render_if_unchanged_refuses_edited_or_foreign_files, test_render_if_unchanged_overwrites_untouched_file |
| SET-FR-022 | `forget` hands a file to the user for good. | `[enforced]` test_scaffold › test_forget_makes_a_file_user_owned |
| SET-FR-023 | Allowlist and `.gitignore` merges add entries, record only the ones they added, and remove only those; other settings keys are preserved. | `[enforced]` test_scaffold › test_allow_merges_and_only_removes_its_own_entries, test_allow_creates_settings_file, test_gitignore_merges_and_only_removes_its_own_lines |
| SET-FR-024 | `CLAUDE.md` is never written by the plugin. | `[instructed]` SKILL.md ownership table |

### Upgrade and versions

| ID | Requirement | Guarantee |
|---|---|---|
| SET-FR-030 | Drift: `current`, `behind`, `ahead`, or `plugin_too_old` (plugin below the repo's `min_plugin_version`); versions compare numerically. | `[enforced]` test_scaffold › test_drift, test_versions_compare_numerically |
| SET-FR-031 | `set-version` raises `min_plugin_version`, never lowers it. | `[enforced]` test_scaffold › test_min_plugin_version_never_lowers |
| SET-FR-032 | Upgrade plan classifies each tracked file: regenerate (generated), replace (seeded, unedited, template changed), review (edited), restore (deleted), template gone; files without a template are left alone. Generated CI is replaced when the commands change. | `[enforced]` test_scaffold › test_upgrade_plan_classifies_every_file, test_builtin_ci_is_upgradable |
| SET-FR-033 | Upgrade runs on `sdlc/upgrade-<from>-<to>`; edited files: merge, skip this time, or keep mine; warns if a feature is past Stage 3; `--dry-run` writes nothing. | `[instructed]` upgrade.md |
| SET-FR-034 | Pending migrations are those with scaffold version < migration version ≤ plugin version, not applied or skipped, ordered numerically; frontmatter version wins over the filename. | `[enforced]` test_scaffold › test_pending_migrations_window_and_order, test_status_lists_pending_migrations |
| SET-FR-035 | Migrations are recorded as applied or skipped with a reason; skipped ones aren't offered again unless `--revisit`; a skipped one can later be applied; unknown ids are errors. | `[enforced]` test_scaffold › test_applied_and_skipped_migrations_are_not_pending, test_unknown_migration_is_an_error |

### Eject

| ID | Requirement | Guarantee |
|---|---|---|
| SET-FR-040 | Eject is a dry run by default: delete (generated, unedited seeded), ask (edited), already gone, entries to unmerge. | `[enforced]` test_scaffold › test_eject_plan_is_dry_by_default |
| SET-FR-041 | Applying deletes plugin files, removes recorded entries and the lock, tidies emptied folders, and keeps the user's files and config. | `[enforced]` test_scaffold › test_eject_apply_keeps_user_work |
| SET-FR-042 | Edited files are deleted only when the user lists them (`--also`), and only from the ask list. | `[enforced]` test_scaffold › test_eject_also_deletes_edited_files_on_request_only |
| SET-FR-043 | Eject fixes imports left pointing at deleted files and reruns the verify commands. | `[instructed]` eject.md |

## Edge cases

- A corrupt lock or config is reported as an error, never a crash (test_scaffold › test_corrupt_lock_is_an_error_not_a_crash).
- Commands other than `init` and `status` need a lock (test_scaffold › test_commands_need_a_lock).
- A repo with a pre-setup `.sdlc/` has no lock, so it goes through brownfield setup, which keeps existing features.

## Non-goals

- Presets or stack templates maintained by the plugin; CI for systems other than GitHub Actions; installing tools without asking.

## Known gaps

- Not yet run end to end in a live session (setup → start → upgrade). No migration has shipped yet, so the migration path is exercised only by tests.
