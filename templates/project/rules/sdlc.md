<!-- Managed by the sdlc plugin v{{plugin_version}}. Regenerated on /sdlc:upgrade: edits here are lost. Files named sdlc-*.md belong to the plugin; put your own rules in CLAUDE.md or other .claude/rules/ files. -->
# SDLC workflow

- Start or resume work with `/sdlc:start <request>`; check progress with `/sdlc:status`. Feature artifacts live in `.sdlc/<feature>/` (committed); scratch goes in `.sdlc/.work/` (git-ignored).
- Commands go through the root `justfile`: `just test`, `just lint`, `just typecheck`, `just build`, `just verify` (all four). Don't call the underlying tools directly when a recipe exists.
- Full test runs (these clear Stage 5 freshness): {{config.verify.full}}.
- Known pre-existing failures are listed in `{{config.baseline}}`; only new failures block Stage 5.
- Project principles: `.sdlc/constitution.md`. Team knowledge: open `knowledge/index.md` and follow links on demand; don't read the folder wholesale.
