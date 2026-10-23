<!-- Managed by the sdlc plugin v{{plugin_version}}. Regenerated on /sdlc:upgrade: edits here are lost. Files named sdlc-*.md belong to the plugin; put your own rules in CLAUDE.md or other .claude/rules/ files. -->
# SDLC workflow

- Start or resume work with `/sdlc:start <request>`; check progress with `/sdlc:status`. A feature's documents live in `{{layout.intents_root}}<feature>/` and its state in `{{layout.state_root}}` (both committed; `scaffold.py paths <feature>` names them); scratch goes in `.sdlc/.work/` (git-ignored).
- The project's commands are in `.sdlc/config.json`: `commands` (install, test, lint, typecheck, build), or per package under `packages` in a monorepo. Use them exactly as written, from the package's directory; don't invent other invocations.
- A full test run is that `test` command with no filters (no file, name or package arguments). In a monorepo each package has its own, run from its `path`; only that package's results go fresh.
- Known pre-existing failures are listed in `{{config.baseline}}`; only new failures block Stage 5.
- Project principles: `{{layout.constitution}}`. Team knowledge: open `knowledge/index.md` and follow links on demand; don't read the folder wholesale.
