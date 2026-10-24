# Spec 11: Teammates on Cursor and Codex

Give teammates on Cursor or Codex the repo's conventions, document locations and the rules that protect the sdlc workflow, without copying anything by hand. Say plainly which guarantees their tool can and can't give. Phase 1 of [issue #1](https://github.com/tammai/sdlc/issues/1); the design is in [ADR 0007](../adr/0007-multi-tool-adapters.md).

**Entry points:** setup's `other-tools` step, `/sdlc:upgrade`, `/sdlc:eject`, `/sdlc:doctor` · **Source:** `scripts/scaffold.py agents`, `templates/project/agents/workflow.md`, `scripts/doctor.py`, `skills/setting-up-projects/`

## User scenarios

1. **Mixed team setup.** Given a brownfield repo with its own `AGENTS.md`, when the lead runs `/sdlc:setup` and picks Cursor and Codex, then `AGENTS.md` gains one sdlc block: the workflow rules, `CLAUDE.md` and every area rule with its file globs. The lead's own text is untouched.
2. **Convention drift.** Given a teammate edits `.claude/rules/tests.md`, when anyone runs `/sdlc:doctor`, then the `AGENTS.md` check warns and names `/sdlc:upgrade` as the fix.
3. **Claude-only line.** Given `CLAUDE.md` tells Claude to run `${CLAUDE_PLUGIN_ROOT}/scripts/x`, when the block is built, then nothing is written and the error names `CLAUDE.md:<line>`.
4. **Protected files.** Given a Codex teammate's agent works on a feature, when it reads `AGENTS.md`, then it's told never to edit the feature's state file, `test-report.md` or the baseline, and to ask a Claude Code teammate to run the stage instead.

## Requirements

| ID | Requirement | Guarantee |
|---|---|---|
| AGT-FR-001 | `tools.targets` in `.sdlc/config.json` lists the team's tools from `claude-code`, `cursor` and `codex`; the default is `["claude-code"]`, which writes nothing. An unknown value is a config error. | `[enforced]` test_scaffold › test_agents_off_for_claude_only_and_unknown_target_is_an_error |
| AGT-FR-002 | With `cursor` or `codex` targeted, `scaffold.py agents` writes one `<!-- sdlc:begin … -->`…`<!-- sdlc:end -->` block in the root `AGENTS.md`, which both tools read, so nothing loads twice. The block holds the workflow rules, `CLAUDE.md` and each `.claude/rules/*.md` except `sdlc.md`. Its header names the plugin version and the sources. A rebuild with unchanged sources changes no byte, and the block has no timestamps. | `[enforced]` test_scaffold › test_agents_writes_one_block_and_keeps_the_users_text |
| AGT-FR-003 | Text outside the block is kept byte for byte, including CRLF line endings; the block follows the file's line endings. | `[enforced]` test_scaffold › test_agents_writes_one_block_and_keeps_the_users_text |
| AGT-FR-004 | Claude-only constructs are mapped: an `@path` import line becomes "Also read `path`.", and `/sdlc:<cmd>` is marked "(Claude Code)". One with no mapping (`${CLAUDE_PLUGIN_ROOT}`, `scaffold.py`) stops the build, which writes nothing and names the file and line. | `[enforced]` test_scaffold › test_agents_writes_one_block_and_keeps_the_users_text, test_agents_stops_at_a_claude_only_line |
| AGT-FR-005 | `scaffold.py agents --check` exits 1 when the block differs from a fresh build (line endings ignored), or when it is present but no longer targeted. Doctor warns on a stale block, and fails on a Claude-only line. | `[enforced]` test_scaffold › test_agents_check_and_upgrade_plan_report_drift; test_doctor › test_agents_md_out_of_date_warns |
| AGT-FR-006 | The block is a keyed merge in the lock (`merged["AGENTS.md#sdlc"]`, plus `file` when the plugin created `AGENTS.md`). `upgrade-plan` reports `agents: stale` so upgrade rebuilds it. Eject removes the block, and the file too if the plugin created it and nothing else is left. | `[enforced]` test_scaffold › test_agents_check_and_upgrade_plan_report_drift, test_eject_removes_the_block_and_a_file_it_created |
| AGT-FR-007 | Each area rule keeps its scope: its section opens with "Applies when working on files matching" and its `paths:` globs, or "Applies to all files" when it has none. | `[enforced]` test_scaffold › test_agents_writes_one_block_and_keeps_the_users_text |
| AGT-FR-011 | The workflow section names the documents and state locations for this repo's layout. It forbids editing feature state files, `test-report.md` and the baseline, and says to ask a Claude Code teammate to run the stage instead. It uses no script calls. | `[instructed]` `templates/project/agents/workflow.md`; rendering `[enforced]` test_project_templates › test_every_template_renders_without_leftover_placeholders |
| AGT-FR-012 | Setup asks which other tools the team uses (a hard stop), records `tools.targets` and builds the block. Changing `CLAUDE.md` or a rule through `sdlc:managing-knowledge` rebuilds it. | `[instructed]` setting-up-projects `other-tools`, managing-knowledge step 8 |

## Guarantees per tool

Every `[enforced]` requirement in specs 02–06 is enforced by one of the mechanisms below, and the mechanism decides what a teammate's tool gets.

| Mechanism | Examples | Claude Code | Cursor | Codex |
|---|---|---|---|---|
| Plugin hook (`hooks/hooks.json`) | role guard, freshness, model router, trust anchor, hookify guardrails, security hooks | enforced | instructed: the block carries the rule; plugin hooks don't run | instructed |
| Plugin script run by a skill | scaffold, diff_stats Public Surface check, doctor | enforced | n/a: run by a Claude Code teammate | n/a |
| Subagent isolation | fresh verifier, read-only reviewers | enforced | n/a in phase 1 | n/a |
| Generated CI (`sdlc-verify`) | the full test suite on the merged code | enforced | enforced | enforced |
| Policy rules (`.claude/rules/`) | code style, tests, migrations, sensitive areas, CI, UI | instructed | instructed, through the block | instructed, through the block |

## Known gaps

- **Cursor rules with glob scoping.** Cursor's `.cursor/rules/*.mdc` files would load area rules only for matching files. Phase 1 writes only `AGENTS.md`, so in Cursor every area rule is always loaded. It also avoids loading the same rule twice when a team uses both tools.
- **Whether Cursor reads `CLAUDE.md` on its own.** The sources disagree and no official page says. If it does, a Cursor user sees the `CLAUDE.md` content twice: once directly, once in the block. This is a smoke-test item.
- **Codex's 32 KiB cap** on the combined `AGENTS.md` text. The block (workflow rules, `CLAUDE.md` within its 60-line budget, and the policy rules) is about 10 KB, but repos with many area rules should watch it. Nothing checks it yet.
- **The check in CI** (`agents --check`) needs the plugin's scripts on the CI runner. That waits for phase 2 and the open question of vendoring `scripts/` into `.sdlc/bin/`.
- **Packaging the plugin for Cursor and Codex** (their plugin formats with skills, agents and hooks) needs a mapping for `${CLAUDE_PLUGIN_ROOT}` in skill text, and testing in the real tools. It isn't part of phase 1.
- **Ownership fields and the CI checks for the shared invariants** (`Owner:` and `Tool:` in `state.md`, the report and baseline checks) are phase 2. Until then, the protected files are `instructed` only on Cursor and Codex.
