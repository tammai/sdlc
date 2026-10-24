# Spec 11: Claude Code, Codex, Cursor and Antigravity

The plugin installs and runs on its own in Claude Code, Codex, Cursor and Antigravity. Setup knows which agent is running it and writes that agent's files without asking. When a second agent opens a repo another agent already set up, its setup adds only its own layer and carries over what the first team wrote. [Issue #1](https://github.com/tammai/sdlc/issues/1); the design is in [ADR 0007](../adr/0007-multi-tool-adapters.md).

**Entry points:** `/sdlc:setup` (or the `setting-up-projects` skill), `/sdlc:upgrade`, `/sdlc:eject`, `/sdlc:doctor` · **Source:** `scripts/scaffold.py host`, `add-host` and `agents`, `scripts/hosts.py`, `templates/project/agents/workflow.md`, the Codex, Cursor and Antigravity manifests, `hosts/`

## Install

| Agent | Install | Reads |
|---|---|---|
| Claude Code | `/plugin marketplace add tammai/sdlc`, then `/plugin install sdlc@sdlc` | `.claude-plugin/` |
| Codex | `codex plugin marketplace add tammai/sdlc`, then `codex plugin add sdlc@sdlc` | `.agents/plugins/marketplace.json`, then one of the root `plugin.json`, `.codex-plugin/plugin.json` or `.claude-plugin/plugin.json` (precedence unverified) |
| Cursor | Customize → Import from Repo, or put a clone in `~/.cursor/plugins/local` | `.cursor-plugin/`; agents from `hosts/cursor/agents/` |
| Antigravity | `agy plugin install https://github.com/tammai/sdlc` (CLI), or a clone in `~/.gemini/config/plugins/` | root `plugin.json`, `skills/`, `agents/` |

## User scenarios

1. **Setup in Codex.** Given the plugin is installed in Codex, when the user asks to set up sdlc in a new repo, then setup records `hosts: ["codex"]` without asking which agent this is. The shared setup runs, and `AGENTS.md` gets the sdlc block with the workflow and the policy rules. Nothing is written under `.claude/`.
2. **Claude Code joins.** Given that repo, when a Claude Code user runs `/sdlc:setup`, then setup sees it's joining, so it runs only the Claude Code layer (rules, guardrails, allowlist) and `scaffold.py agents`. The team's own `AGENTS.md` text reaches Claude Code through `.claude/rules/sdlc-agents-md.md`. The commands, baseline and constitution are not redone.
3. **Codex joins a Claude Code repo.** Given a repo Claude Code set up, when a Codex user runs setup, then `AGENTS.md` gains the block, built from `CLAUDE.md`, the team's `.claude/rules/` and the plugin's policy rules. The team's own text outside the block is untouched.
4. **Can't tell.** Given Codex was started from a Claude Code shell and the plugin was loaded from a checkout, when setup runs, then it asks which agent this is: the only question it asks about hosts.
5. **Drift.** Given a teammate edits `CLAUDE.md`, when anyone runs `/sdlc:doctor`, then the `AGENTS.md` check warns and names `scaffold.py agents`.

## Requirements

| ID | Requirement | Guarantee |
|---|---|---|
| AGT-FR-001 | `scaffold.py host` names the running agent (`claude-code`, `codex`, `cursor`, `antigravity`). The plugin's install folder decides (`.claude/plugins`, `.codex/plugins`, `.cursor`, `.gemini` or `.agents/plugins`, or a folder inside `CLAUDE_CONFIG_DIR` or `CODEX_HOME`); if it names none, exactly one agent's environment markers decide; otherwise the host is `null` and `init` refuses without `--host`. | `[enforced]` test_scaffold › test_host_comes_from_the_install_folder_then_the_environment |
| AGT-FR-002 | `init` records the host in the lock (`hosts`). In a set-up repo, `host` reports `joining: true` for an agent not yet recorded, and `add-host` records it; an unknown host is an error. Locks without `hosts` count as Claude Code's. | `[enforced]` test_scaffold › test_a_second_agent_joins_and_gets_one_block_with_the_users_text_kept, test_a_repo_without_claude_code_gets_no_claude_files |
| AGT-FR-003 | With any host besides Claude Code recorded, `scaffold.py agents` writes one `<!-- sdlc:begin … -->`…`<!-- sdlc:end -->` block in the root `AGENTS.md`, which Codex, Cursor and Antigravity all read, so nothing loads twice. It holds the workflow section, `CLAUDE.md`, the plugin's policy rules (rendered from its templates) and the team's own `.claude/rules/`. A rebuild with unchanged sources changes no byte. Text outside the block is kept byte for byte, CRLF included. | `[enforced]` test_scaffold › test_a_second_agent_joins_and_gets_one_block_with_the_users_text_kept |
| AGT-FR-004 | Claude-only constructs are mapped: an `@path` import line becomes "Also read `path`." (not inside code fences), and `/sdlc:<cmd>` is marked "(Claude Code)". One with no mapping (`${CLAUDE_PLUGIN_ROOT}`, `scaffold.py`) stops the build, which writes nothing and names the file and line. | `[enforced]` test_scaffold › test_a_second_agent_joins_and_gets_one_block_with_the_users_text_kept, test_agents_stops_at_a_claude_only_line |
| AGT-FR-005 | With Claude Code and at least one other host recorded, and team text in `AGENTS.md` outside the block, `agents` writes `.claude/rules/sdlc-agents-md.md` (generated, in the lock) with that text, and removes it when the text is gone. | `[enforced]` test_scaffold › test_a_second_agent_joins_and_gets_one_block_with_the_users_text_kept, test_a_repo_without_claude_code_gets_no_claude_files |
| AGT-FR-006 | `agents --check` exits 1 when the block or the mirror differs from a fresh build; `upgrade-plan` reports `agents: stale`; doctor warns, and fails on a Claude-only line. Upgrade adds the Claude Code rules and guardrails only when Claude Code is a recorded host. Eject removes the block, and `AGENTS.md` too if the plugin created it. | `[enforced]` test_scaffold › test_agents_check_and_upgrade_plan_report_drift, test_a_repo_without_claude_code_gets_no_claude_files, test_eject_removes_the_block_and_a_file_it_created; test_doctor › test_agents_md_out_of_date_warns |
| AGT-FR-007 | Each area rule in the block keeps its scope: "Applies when working on files matching" its `paths:` globs, or "Applies to all files". | `[enforced]` test_scaffold › test_a_second_agent_joins_and_gets_one_block_with_the_users_text_kept |
| AGT-FR-008 | `scripts/hosts.py build` writes the Codex, Cursor and Antigravity manifests from `.claude-plugin/` (same name, version and description), and Cursor's agents with `model: inherit`, plus `readonly: true` when an agent's listed tools include no edit tool. `check` exits 1 when any differs; CI runs it. | `[enforced]` test_hosts › test_build_writes_every_host_and_check_catches_drift |
| AGT-FR-009 | Setup runs the Claude Code steps (rules, guardrails, allowlist, plugin enablement) only on Claude Code. A joining agent skips the shared steps and adds only its layer. Every skill, command and agent that names `${CLAUDE_PLUGIN_ROOT}` says how to find the plugin folder where it isn't filled in. | `[instructed]` setting-up-projects (Which flow, Join), the note in each file |
| AGT-FR-011 | The workflow section names this repo's document and state locations, and says to start work through the plugin. It forbids hand edits to feature state files, `test-report.md` and the baseline, and uses no script calls. | `[instructed]` `templates/project/agents/workflow.md`; rendering `[enforced]` test_project_templates › test_every_template_renders_without_leftover_placeholders |

## Guarantees per agent

Every `[enforced]` requirement in specs 02–06 rests on one of these mechanisms, and the mechanism decides what each agent gets.

| Mechanism | Examples | Claude Code | Codex | Cursor | Antigravity |
|---|---|---|---|---|---|
| Plugin hook | role guard, freshness, model router, trust anchor, hookify guardrails, security hooks | enforced | instructed: no hooks yet | instructed: no hooks yet | instructed: no hooks yet |
| Plugin script run by a skill | scaffold, doctor, `diff_stats.py` | enforced | enforced, if the agent finds the plugin folder | same | same |
| Subagent roles | fresh verifier, read-only reviewers | enforced (tools per agent) | instructed: Codex agents can't be made read-only, and plugin agents aren't loaded | reviewers `readonly`; the verifier instructed | instructed: agents load from `agents/` in Claude's format, untested |
| Generated CI (`sdlc-verify`) | the full test suite on the merged code | enforced | enforced | enforced | enforced |
| Policy rules | code style, tests, migrations, sensitive areas, CI, UI | `.claude/rules/`, glob-scoped | `AGENTS.md` block, always loaded | same | same |

## Known gaps

- **Not run in the real tools yet.** Codex loaded a Claude-format plugin in a probe: it namespaced the skills as `sdlcprobe:…` and turned `commands/` into skills. The probe's commands were blocked by the sandbox, though, and the plugin hadn't been installed from this repo. Cursor and Antigravity aren't installed here. Each needs the smoke test in the runbook.
- **Which Codex manifest wins.** The probe had only `.claude-plugin/`. The shipped repo has three manifests Codex might read: the root `plugin.json` (Antigravity's, without a `hooks` key), `.codex-plugin/` and `.claude-plugin/`. Two things depend on which one wins. One is whether `commands/` still become skills, since `.codex-plugin` names only `skills`. The other is whether the empty hooks file applies, or Codex finds the Claude-format `hooks/hooks.json`. This is the first thing the Codex probe checks.
- **Codex on Windows runs commands in PowerShell.** The skills are written for bash (`S="python3 …"`, `$S status`, heredocs), and `${CLAUDE_PLUGIN_ROOT}` means something else in PowerShell. Expect this to fail first in a Windows smoke test.
- **Finding the plugin folder outside Claude Code** relies on the agent knowing where the file it loaded lives. Codex showed that it knows its `SKILL.md` path; Cursor and Antigravity are unverified.
- **Antigravity reads `agents/` in Claude's format** (`tools: Glob, Grep`, `model: sonnet`), and its plugin format can't point elsewhere. If it rejects them, the agents need a generated copy and a separate install root.
- **Codex and the root `plugin.json`.** The root `plugin.json` is Antigravity's, but Codex treats a root `plugin.json` as its portable manifest. It has no Agent Plugins `$schema`, so Codex should fall back to `.codex-plugin/`; this is unverified.
- **No hooks outside Claude Code.** Each non-Claude manifest points its hooks at an empty file, because the hook scripts read Claude Code payloads only. The tool-neutral `decide(event)` refactor with an adapter per agent is the next phase.
- **No glob scoping outside Claude Code.** Policy rules sit in `AGENTS.md`, so they always load. Writing `.cursor/rules/*.mdc` or `.agents/rules/*.md` would duplicate them, because those agents read `AGENTS.md` too.
- **Codex's 32 KiB cap** on the combined `AGENTS.md` text: the block is about 10 KB with every policy rule, and nothing checks the total yet.
- **`AGENTS.override.md`** at the root makes Codex skip `AGENTS.md`, and with it the block.
- **Enabling the plugin for the team** exists only for Claude Code (`.claude/settings.json`). Other agents' users install it themselves.
- **Ownership and the CI checks for the shared invariants** (`Owner:` and `Tool:` in `state.md`, the report and baseline checks) are still to come. Until then, the protected files rely on instructions in every agent except Claude Code.
