# ADR 0007: One AGENTS.md block for teammates on Cursor and Codex

- **Status:** Accepted, 2026-10-24. Amends [ADR 0001](0001-project-setup-upgrade-eject.md): it adds a keyed merge on `AGENTS.md`.
- **Deciders:** Tâm Mai.

## Context

Teams mix tools. Claude Code reads `CLAUDE.md` and `.claude/rules/`, Codex reads `AGENTS.md`, and Cursor reads `.cursor/rules/` and also `AGENTS.md`. Setup wrote only the Claude files, so a teammate's agent on another tool didn't know the repo's conventions or which sdlc files it must leave alone. [Issue #1](https://github.com/tammai/sdlc/issues/1) proposed generating an adapter per tool for rules, commands, skills and role prompts.

The proposal was written from memory. Checking it against the current docs (2026-10-24) changed four things:
- Codex custom prompts are deprecated in favour of skills.
- Codex caps the combined `AGENTS.md` text at 32 KiB. The orchestrator skill alone is 23 KB, so it can't be inlined there.
- Both tools now have plugin formats. Skill text that names `${CLAUDE_PLUGIN_ROOT}`, though, only resolves in Claude Code, and 26 of this plugin's skills, commands and agents do that.
- The area globs in `config.defaults.json` are file types (`**/*.{ts,tsx}`), not folders, so a nested `AGENTS.md` per folder can't carry them.

## Decision

- **Phase 1 writes one managed block in the root `AGENTS.md`**, between `<!-- sdlc:begin -->` and `<!-- sdlc:end -->`, only when `tools.targets` names `cursor` or `codex`. Both tools read that file, so each instruction is written once and loads once. No `.cursor/rules/*.mdc` files are written.
- **Content is copied in, not pointed to.** The block carries a workflow section for non-Claude teammates (`templates/project/agents/workflow.md`), `CLAUDE.md`, and each area rule with its globs stated in a line. Every copied line passes through one mapping table:
  - an `@path` import becomes "Also read `path`";
  - `/sdlc:<cmd>` is marked "(Claude Code)";
  - a construct with no equivalent (`${CLAUDE_PLUGIN_ROOT}`, `scaffold.py`) stops the build and names the file and line.
  A pointer ("read `.claude/rules/x.md`") would hand those constructs to the other tool unchecked.
- **The generator lives in `scaffold.py` (`agents`, `agents --check`)**, not in a separate `agents_adapter.py` as the issue proposed. It is one more keyed merge: it shares the lock, `merged` and the eject and upgrade-plan logic, so a second script would have duplicated them.
- **Packaging the plugin for Cursor and Codex is deferred.** It needs a way to resolve `${CLAUDE_PLUGIN_ROOT}` in skill text, and testing in the real tools.

### Alternatives considered

| Option | Why not |
|---|---|
| A generated file per tool (`.cursor/rules/*.mdc` plus `AGENTS.md`) | Cursor reads both, so a team on both tools gets every instruction twice. Cursor also splits `globs:` on commas, which breaks `{ts,tsx}`. |
| A nested `AGENTS.md` per area | the areas are file types, not folders |
| The stage flow inlined in `AGENTS.md` | over Codex's 32 KiB cap; and Cursor and Codex can't run the stages anyway, because they need the plugin's scripts and subagents |
| Ship `.cursor-plugin/` and `.codex-plugin/` manifests now | skills would tell those agents to run paths that don't resolve |

## Consequences

- **Good:**
  - a Cursor or Codex teammate gets the repo's conventions, document locations and the protected-file rules, with no copying by hand;
  - `/sdlc:doctor` reports a stale block, and `/sdlc:upgrade` rebuilds it on each plugin release;
  - the user's own `AGENTS.md` text is never touched.
- **Costs:**
  - in Cursor, area rules load for every file, not only matching ones;
  - every `CLAUDE.md` or rule change must be followed by `scaffold.py agents`. `sdlc:managing-knowledge` does this, and doctor catches the rest;
  - a Claude-only line in `CLAUDE.md` blocks the build until someone rewords it.
- **Guards:** none in phase 1. On Cursor and Codex, the protected files (state, `test-report.md`, the baseline) are protected by instruction only. The CI checks that enforce them for every tool come in phase 2.
