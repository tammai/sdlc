# Spec: context diet (trim what Claude Code loads into every call)

Status: draft for approval · 2026-10-25

## Why

Every main-session call in Claude Code carries the name and description of every enabled skill, agent and command, plus MCP tool definitions. On the maintainer's machine that floor was 58-64k tokens per call in every project, sdlc or not. Most of it came from plugins and personal skills unrelated to the project: about 20k per call, over 72 calls in one feature. Separately, the standalone `security-guidance`, `code-review` and `code-simplifier` plugins load next to sdlc's bundled copies. That doubles the hooks, and two skills with the same name (`code-review:code-review` and `sdlc:code-review`) let the model pick the one without sdlc's routing.

## What

- **`scripts/context_diet.py`** (stdlib, read-only) prints JSON facts.
  - It reads the user's `enabledPlugins` and the project's `.claude/settings.json` and `.claude/settings.local.json`, merged key by key in that order.
  - It reads each plugin's install folder from `installed_plugins.json`.
  - It lists personal skills (`~/.claude/skills`, except `synced/`) and claude.ai-synced plugins and skills.
  - Each source gets its estimated tokens per call (listed name + description, chars/4), item count, MCP flag, a short "about" and its effective enabled state.
  - It also reports the project's signals (languages, manifests, key dependencies, `.sdlc/` present) and whether `.claude/settings.local.json` is ignored by git.
- **Skill `sdlc:trimming-context`** and **command `/sdlc:context-diet`.**
  - They run the script and show a table (source, est. tokens/call, verdict, reason).
  - They propose an `enabledPlugins` block for `.claude/settings.local.json` and write it only after the user approves.
  - They list personal and synced items they can't switch, as advice.
  - They are Claude Code only, and they work in a repo with no sdlc setup.
- **Setup:** a Claude Code-only `context-diet` step right after `enable-plugin`, asked first.

## Acceptance criteria

1. **Sources and costs.** Given a home with two enabled plugins and a personal skill, the script reports each one as a source. Each source has its item count, an estimated token cost from the listed names and descriptions, and its MCP flag. Plugins that are effectively disabled cost 0. `[enforced]`
2. **Duplicates of sdlc.** When sdlc is effectively enabled for the project, the standalone `security-guidance`, `code-review` and `code-simplifier` plugins get verdict `duplicate`, whatever marketplace they come from. `[enforced]`
3. **LSPs by language.** A known LSP plugin gets `keep` when its language is present in the project and `off` when it isn't. Every other plugin's verdict is `null`, left to the skill's judgement. `[enforced]`
4. **Bad input degrades.** A missing or malformed `installed_plugins.json` or settings file is reported in `problems`, and the script still prints JSON and exits 0. The same holds for an enabled plugin with no install record or folder. `[enforced]`
5. **Testable home.** `--home` and `--root` point the script at a fixture home and project. It never writes anything. `[enforced]`
6. **The proposal.** The skill shows one table row per enabled plugin, with a one-line reason for every judgement call. It proposes only `enabledPlugins` keys set to `false` in `.claude/settings.local.json`, merged with the keys already there, and shows the estimated saving per call. `[instructed]`
7. **Approval and scope.** The skill writes the file only after the user approves. It never edits `~/.claude/settings.json`, moves personal skills or touches synced plugins unless the user explicitly asks. Personal skills that look unrelated are listed with "move them into the projects that use them". Synced ones are reported only, since they are managed in claude.ai. `[instructed]`
8. **Never committed.** Before writing, the skill checks that `.claude/settings.local.json` is ignored by git. If it isn't, the skill offers `.git/info/exclude`. It never edits the team's `.gitignore` and never stages the file. `[instructed]`
9. **Any project, Claude Code only.** `/sdlc:context-diet` works in a repo with no `.sdlc/`. The command is not built into the Codex or Antigravity skills. On another agent, the skill says it reads Claude Code's config and stops. It ends by saying that changes apply to new sessions and that `/context` shows the real numbers. `[instructed]`
10. **Setup offers it.** `/sdlc:setup` (and Join on Claude Code) has a `context-diet` step right after `enable-plugin`. It asks first. If declined, the step is recorded and the user is told. Setup's commits are unchanged. `[instructed]`

## Non-goals

- Measuring real token counts. The numbers are estimates; `/context` is the ground truth.
- Estimating MCP tool-definition size. Sources with MCP are flagged only.
- A `/sdlc:doctor` check. It would need doctor to scan `~/.claude` and add a test, which isn't cheap.
- Turning plugins off at user scope, or moving skills.

## Calls made (mine, open to change)

- Names: the script is `context_diet.py`, the skill `trimming-context`, the command `/sdlc:context-diet`. I avoided `/sdlc:context`, which sits next to the built-in `/context`.
- The script stays facts-only, with no `apply` subcommand. The skill edits `settings.local.json` itself, after approval.
- If the skill proposes turning sdlc itself off in a non-sdlc project, it says so. The `duplicate` verdicts then no longer apply.
