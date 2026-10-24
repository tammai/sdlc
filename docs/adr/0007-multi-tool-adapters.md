# ADR 0007: One plugin for Claude Code, Codex, Cursor and Antigravity

- **Status:** Accepted, 2026-10-24. Amends [ADR 0001](0001-project-setup-upgrade-eject.md): the lock records hosts, and `AGENTS.md` gets a keyed-merge block.
- **Deciders:** Tâm Mai.

## Context

Teams mix coding agents. Before this change, sdlc ran only in Claude Code, and setup wrote only Claude's files. [Issue #1](https://github.com/tammai/sdlc/issues/1) proposed per-tool adapters generated into each project. The decision changed twice:
- **Plugin formats.** The docs (checked 2026-10-24) show that Codex, Cursor and Antigravity now all install plugins that use `skills/<name>/SKILL.md`. A probe showed Codex installing a plugin that has only a Claude-format manifest.
- **What the owner asked for.** The plugin must install and run on each agent by itself; setup must know which agent is running it, without asking; and a second agent opening a set-up repo must adapt to what is already there.

The constraints:
- `${CLAUDE_PLUGIN_ROOT}` is filled in only by Claude Code, and 25 skills, commands and agents use it.
- Codex, Cursor and Antigravity all read the root `AGENTS.md`. Claude Code doesn't.
- Codex caps the combined `AGENTS.md` text at 32 KiB.
- The environment variables that mark each agent are unofficial and change between releases.

## Decision

- **One source, built for each agent.** The Claude Code plugin stays the source. `scripts/hosts.py` writes, and CI checks:
  - the Codex manifest (`.codex-plugin/`, plus `.agents/plugins/marketplace.json`);
  - the Cursor manifest (`.cursor-plugin/`, with agents in `hosts/cursor/agents/`: `model: inherit`, read-only reviewers `readonly`);
  - Antigravity's root `plugin.json`.

  The skills are shared as they are. Skill text keeps `${CLAUDE_PLUGIN_ROOT}`, with a note telling other agents to use the plugin folder above the file.
- **Detecting the host.** The plugin's install folder decides (`.claude/plugins`, `.codex/plugins`, `.cursor`, `.gemini`). Environment markers decide only when exactly one agent's markers are present. Setup asks only when neither works.
- **Hosts are recorded in the lock.** Shared setup (config, commands, baseline, constitution, design system, CI, knowledge) happens once. Each host adds a layer:
  - **Claude Code:** `.claude/rules`, hookify guardrails, the allowlist and plugin enablement.
  - **Every other host:** the single sdlc block in `AGENTS.md`.
- **A joining agent** runs `add-host`, its own layer and `agents`, and nothing else.
- **What crosses between agents is copied, never pointed to.** The `AGENTS.md` block copies:
  - `CLAUDE.md`;
  - the team's `.claude/rules`;
  - the plugin's policy rules, rendered from the templates.

  Every line passes the Claude-only mapping table. For Claude Code, the team's own `AGENTS.md` text is mirrored into a generated `.claude/rules/sdlc-agents-md.md`.
- **The mirror replaces the `@AGENTS.md` import that was considered.** The import would have pulled the sdlc block, with its copy of `CLAUDE.md` and the policy rules, back into Claude Code: everything twice, and a cycle.
- **No hooks outside Claude Code yet.** The other manifests point their hooks at an empty file until the hook logic is tool-neutral.

### Alternatives considered

| Option | Why not |
|---|---|
| Per-project adapters only (the issue's first design) | users of the other agents still couldn't run the workflow |
| A separate repo or branch per agent | releases drift apart; the build plus a CI check keeps one commit true for all four |
| Native glob-scoped rule files per agent (`.mdc`, `.agents/rules`) | Cursor and Antigravity read `AGENTS.md` as well, so every rule would load twice |
| Detection by environment variables only | unofficial markers that come and go; a nested agent sets two sets of them |
| `@AGENTS.md` in `CLAUDE.md` | loads the sdlc block into Claude Code: duplicated rules and a copy cycle |
| Ask the user which agent this is | the owner ruled it out; it stays only as the last resort |

## Consequences

- **Good:**
  - one install per agent, and setup that fits the agent running it;
  - a repo can be shared by several agents without redoing setup or overwriting another team's files;
  - a release ships to all four agents from one commit.
- **Costs:**
  - CI checks that the generated files match the Claude Code sources;
  - outside Claude Code, the policy rules always load, and hooks don't run yet;
  - Cursor and Antigravity are untested until someone runs the smoke test in them.
- **Guards:**
  - `hosts.py check` in CI;
  - `agents --check` and the doctor check;
  - the Claude-only mapping table, which stops the build on a line no other agent can follow.
