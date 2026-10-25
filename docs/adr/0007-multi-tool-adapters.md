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
- **Detecting the host.** The plugin's install folder decides when it is recognizable (`.claude/plugins`, `.codex/plugins`, `.cursor`, `.gemini`, or inside `CLAUDE_CONFIG_DIR` or `CODEX_HOME`). It is the strongest signal, but not a contract either. Environment markers decide only when exactly one agent's markers are present. Setup asks only when neither works.
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
- **Claude Code's files stay as they are; the other agents get extra generated files** (amended 2026-10-24, after the first smoke test):
  - `hosts/skills/` holds the commands as skills, because Codex and Antigravity drop commands that take arguments.
  - Antigravity installs from `hosts.py dist antigravity`, a copy with agents it accepts. It reads `agents/` itself and rejects Claude's model tiers, and changing the source would have changed which model Claude Code's agents run on. The copy is built from the same commit, so it can't drift the way a separate branch would.
- **Hooks outside Claude Code run through a wrapper, not a refactor** (amended 2026-10-25). `hosts/hook.py <host> <event>` turns the agent's payload into Claude Code's, runs the same hook scripts unchanged as child processes, and turns their output back into the agent's format. The scripts stay as they are, because changing them would change Claude Code. It runs hookify, the freshness hook and the trust anchor. It leaves out the role guard, because no agent names the plugin's agents on tool calls. It leaves out the model router, because dispatches carry no model. It also leaves out the security review and the Ralph loop, which need bash launchers and model calls. Codex, Cursor and Antigravity are wired. Antigravity reads a `hooks.json` at the plugin root, which `hosts.py build` writes; Claude Code reads only `hooks/hooks.json`.

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
  - outside Claude Code, the policy rules always load, and only some of the hooks run (Codex and Cursor, for now);
  - Cursor and Antigravity are untested until someone runs the smoke test in them.
- **Guards:**
  - `hosts.py check` in CI;
  - `agents --check` and the doctor check;
  - the Claude-only mapping table, which stops the build on a line no other agent can follow.
