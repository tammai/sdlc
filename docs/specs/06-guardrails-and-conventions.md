# Spec 06: Guardrails and conventions

Conventions apply while code is written (policy rules), are checked as it happens (hookify guardrails, lint snippets), and repeated corrections become rules.

**Entry points:** setup (installs them), `/sdlc:hookify`, `/sdlc:hookify-list`, `/sdlc:hookify-configure`, `/sdlc:hookify-help` · **Source:** `templates/project/rules/`, `templates/project/hookify/`, `templates/project/lint/`, `core/`, `hooks/pretooluse.py`, `stop.py`, `userpromptsubmit.py`, `skills/writing-hook-rules` · **Decision:** [ADR 0003](../adr/0003-guard-against-over-engineering.md)

## User scenarios

1. **Narrating comment.** Given the guardrails are installed, when Claude writes `// Step 1: load the user` in a `.ts` file, then a warning reaches Claude's context and the user, and the write goes ahead.
2. **Force-push.** When Claude runs `git push --force origin main`, then it's blocked and Claude sees why.
3. **Team rule.** Given a rule committed to `.claude/hookify/no-rm.md`, when anyone on the team runs a matching command, then it applies; personal rules in `.claude/hookify.*.local.md` apply only locally.

## Requirements

### Policy rules (generated)

| ID | Requirement | Guarantee |
|---|---|---|
| GRD-FR-001 | Setup renders `sdlc.md` (always loaded) and `sdlc-code-style.md`, `sdlc-tests.md`, `sdlc-migrations.md`, `sdlc-sensitive.md`, `sdlc-ci.md`, `sdlc-ui.md` (see [spec 10](10-ui-design-system.md)), each scoped by `paths:` from `areas.*` in config; each ≤ 30 lines and marked as plugin-managed. | `[enforced]` test_project_templates › test_area_rules_have_paths_frontmatter_and_stay_short, test_defaults_file_is_valid_json_with_every_area |
| GRD-FR-002 | Code style: comments say why only (no narration, restated code or change history); doc comments on exported API, one line by default; smallest diff; no unrequested abstraction, option, file, export or dependency. The same lines are in the subagent implementer prompt. | `[instructed]` rules/code-style.md, implementer-prompt.md |
| GRD-FR-003 | Tests rule: test first, behavior not implementation, no committed `.only`/`.skip`, never weaken assertions without the user's OK, full suite via the configured command. Migrations rule: hard stop, never edit applied migrations, tested rollback. Sensitive rule: at least M, full Stage 7, no secrets or PII in code or logs, fail closed. CI rule: user go-ahead, never weaken checks, same commands as config, pinned actions. | `[instructed]` rules/*.md |

### Hookify engine

| ID | Requirement | Guarantee |
|---|---|---|
| GRD-FR-010 | Rules load from `.claude/hookify.*.local.md` (personal) and `.claude/hookify/*.md` (team) under the project root (`CLAUDE_PROJECT_DIR`, else the nearest parent of the cwd that has rules), so a hook started in a subdirectory still finds them; disabled rules are ignored; no rules → everything allowed. | `[enforced]` test_hookify › test_committed_team_rules_are_loaded, test_disabled_rule_is_ignored, test_no_rules_allows_everything; test_guardrails › test_rules_load_when_the_hook_starts_in_a_subdirectory, test_stop_and_prompt_hooks_also_find_rules_from_a_subdirectory |
| GRD-FR-011 | Rules are evaluated before tool use (bash and file events), on prompt submit and on stop; not again after tool use. | `[enforced]` test_hookify › test_posttooluse_is_not_registered, test_every_hookify_entry_point_runs_clean |
| GRD-FR-012 | Events and fields: bash rules match `command`; file rules match `file_path`, `new_text` (falls back to content on Write), `old_text`, `content`; all conditions must match; operators are `regex_match`, `not_regex_match`, `contains`, `not_contains`, `equals`, `starts_with`, `ends_with`; regexes are case-insensitive, the other operators are exact; `event`, `action` and `operator` values are case-insensitive; `NotebookEdit` is a file event (`file_path` = notebook path, `new_text` = new cell source). | `[enforced]` test_hookify › test_bash_rule_ignores_file_tools, test_condition_rule_on_file_path, test_enabled_stop_rule_blocks; test_hookify › test_notebook_cells_are_a_file_event |
| GRD-FR-013 | `block` denies the tool call (or the prompt, or the stop) with the reason visible to Claude; `warn` allows it and puts the message in Claude's context and the user's view. | `[enforced]` test_hookify › test_dangerous_rm_is_blocked, test_safe_bash_is_allowed, test_block_tells_claude_why, test_file_rule_warns_without_blocking; test_hookify › test_block_on_prompt_blocks_the_prompt |
| GRD-FR-014 | Bad input or an engine error never blocks. | `[enforced]` test_hookify › test_bad_input_never_blocks |
| GRD-FR-015 | A rule that would silently not work (no frontmatter, no conditions, unknown event/action/operator, invalid regex, or a regex that takes over 1 s and is skipped) is reported in the hook's `systemMessage` and by `/sdlc:doctor`, not ignored; a BOM or leading blank line doesn't hide a rule. Rule messages are capped at 2000 characters. | `[enforced]` test_hookify › test_broken_rules_are_reported_not_silent, test_formatting_slips_do_not_disarm_a_rule, test_catastrophic_regex_is_skipped, test_long_rule_messages_are_capped; test_doctor › test_hookify_rules_that_would_never_fire_are_flagged |

### Guardrails (seeded)

| ID | Requirement | Guarantee |
|---|---|---|
| GRD-FR-020 | **Block:** recursive delete of root, home, parent, wildcard or `.git` (not of a named folder like `dist`); force-push (including `--force-with-lease`, `+branch`, `-fu`, and after `git -C`/`-c` options), branch deletion (`:main`, `--delete`) and `--mirror` pushes to main/master; writing real-looking secrets (Anthropic, OpenAI, GitHub, Stripe, Google, AWS, Slack keys, private keys) through file tools, notebook cells or shell commands; editing, moving or deleting the plugin's own `.claude/hookify/sdlc-*.md` rules through file tools or Bash. Recursive delete covers `/*`, `~/*`, `./*`, `../..`, quoted and `${HOME}` forms, and split or long flags. | `[enforced]` test_guardrails › test_bash_guardrails, test_file_guardrails_on_write, test_actions; test_guardrails › test_secrets_are_blocked_in_notebook_cells |
| GRD-FR-021 | **Warn:** `git reset --hard`, `git clean -f`, `checkout -- .`; sensitive files (`.env*`, credentials, keys); `console.log`/`console.debug` in JS/TS; focused or skipped tests; type and lint suppressions; narrating comments; change-history comments; long doc blocks (over ~7 lines) in source files. | `[enforced]` test_guardrails › test_bash_guardrails, test_file_guardrails_on_write, test_file_guardrails_on_edit |
| GRD-FR-022 | Comment guardrails fire only on source files, and stay quiet on legitimate *why* comments (tested negative cases for each rule). | `[enforced]` test_guardrails › test_file_guardrails_on_write |

### Lint snippets and correction loop

| ID | Requirement | Guarantee |
|---|---|---|
| GRD-FR-030 | Setup seeds `.sdlc/lint/eslint.sdlc.mjs` (complexity, depth, params, function length, TODOs, console; relaxed for tests) and `ruff.sdlc.toml` (complexity, branches, args, nesting, commented-out code, print, TODOs); the user's config imports them with an approved diff. | `[instructed]` setting-up-projects; templates render `[enforced]` test_project_templates › test_every_template_renders_without_leftover_placeholders |
| GRD-FR-031 | A correction made twice and mechanically checkable becomes a hookify rule, not more text. | `[instructed]` managing-knowledge, orchestrator §11 |

## Edge cases

- The rule frontmatter parser is minimal: a pattern containing `---` ends the frontmatter (write `-{3}`); inline `- field: x, pattern: y` items are split on commas.

## Non-goals

- Replacing linters or formatters; perfect comment classification (guardrails warn, they don't block, on comment style).

## Known gaps

- Not covered by the regex guardrails: `find / -delete` and other non-`rm` deletes, `git push --force` with no branch named while on main, secrets written by a script the agent runs, and any guardrail edit that goes through a program rather than a file tool or a shell redirect.
- Rules committed to `.claude/hookify/` are repo content: a `warn` message reaches Claude's context. Review changes under that folder like code.
- Whether `additionalContext` warnings and `permissionDecisionReason` reach Claude has been verified against the hook output format, not yet in a live session.
- The Ruff snippet hasn't been run against Ruff (the ESLint snippet has).
