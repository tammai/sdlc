<!-- Read by /sdlc:context-diet and setup's context-diet step (was the trimming-context skill). -->

`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder. Claude Code fills it in.

# Trimming context

Every main-session call carries the name and description of every enabled skill, agent and command, plus MCP tool definitions. Plugins unrelated to the project pay that on every call. This skill finds them and turns them off **for this project only**, in `.claude/settings.local.json` (which overrides the user's settings key by key and is never committed). It works in any repo, with or without sdlc set up.

**Claude Code only.** On any other agent, say that this reads Claude Code's plugin config and has nothing to trim there, then stop.

## 1. Gather

Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/context_diet.py" --root .`. It prints JSON facts and writes nothing:
- `sources`: each plugin (`enabled`, `set_by`, `tokens`, `items`, `mcp`, `hooks`, `about`, `names`, and `verdict`/`rule` when a rule decided it), each personal skill, command and agent, and each claude.ai-synced plugin.
- `project`: languages, manifests, dependencies, design files, `sdlc`.
- `local_settings`: whether `.claude/settings.local.json` exists and is ignored by git.
- `problems`: files it couldn't read. Mention them in one line each; they don't stop you.

## 2. Decide, per enabled plugin

- A `verdict` from the script stands:
  - `duplicate`: sdlc is enabled here and bundles that plugin. The standalone copy doubles the hooks, and its same-name skill bypasses sdlc's routing. Turn it off.
  - `keep` or `off`: an LSP whose language is or isn't in the project.
- Every other plugin is your call from `about`, `names` and the project signals. Give one line of reason.
  - **Keep** it when the project uses what it is for (a Figma plugin in a repo with design files or a Figma dependency, Cloudflare tooling with `wrangler.*`).
  - Also **keep** it when it's cheap and broadly useful (`context7`, a code-review or docs helper the user runs anywhere).
  - **Turn it off here** when it's unrelated to this project and costs tokens or ships MCP servers. A plugin with `mcp` costs more than its `tokens`, since tool definitions aren't counted. Say so.
  - When unsure, keep it and say why. A wrong "off" hides a tool the user expected.
- Keep sdlc in an sdlc repo (`project.sdlc`) or while running setup. If you'd propose turning sdlc itself off, say that the `duplicate` verdicts then no longer hold, and keep those plugins as they are.

## 3. Show

One table, plugins first and then the rest, sorted by tokens:

| Source | Est. tokens/call | Verdict | Reason |
|---|---|---|---|

Then show:
- The proposed `.claude/settings.local.json`. It is the file's current content with each "off" plugin added under `enabledPlugins` as `"<key>": false`. Keep every key already there, the user's own `true`s included, and every other setting. Never add a `true` yourself, the sdlc plugin's own key included: a session that loaded sdlc with `--plugin-dir` would then load a second, installed copy.
- The estimated saving per call: the sum of the "off" plugins' `tokens`, plus "and N MCP servers".
- **Personal skills, commands and agents** that look unrelated to this project, with their tokens. Remedy: move them into `.claude/skills/` of the projects that use them. They can't be switched off per project. Don't move them.
- **Synced plugins and claude.ai skills**, with their tokens. These are managed in claude.ai and can't be switched here. Report only.

Ask: write the file (all, some, none)?

## 4. Apply, only on approval

1. If `local_settings.ignored` is `false`, offer to add `.claude/settings.local.json` to `.git/info/exclude`, and do that before writing. Never edit the team's `.gitignore` for this, and never stage the file. If the repo isn't a git repo (`null`), just write it.
2. Write the merged file. Re-read it first if it exists, and edit only `enabledPlugins`.
3. Say that this applies to **new** sessions only, and to run `/context` in a new session for the real numbers. The estimates count listed names and descriptions only.

Never edit `~/.claude/settings.json`, move personal skills or touch synced plugins unless the user explicitly asks for that.
