# Brownfield setup

The repo has code, history and habits. Goal: adopt sdlc without breaking anything, record what's already failing so features aren't blamed for it, and turn what the codebase already knows into knowledge the agent can load. **Nothing the audit drafts is written without the user's approval.**

## `stack` – detect (no questions unless ambiguous)

Read, don't guess: lockfiles and manifests (`package.json`, `pnpm-workspace.yaml`, `pyproject.toml`, `go.mod`/`go.work`, `Cargo.toml`, `pubspec.yaml`, `*.csproj`, `build.gradle*`), existing task runners (`Makefile`, `justfile`, `package.json` scripts, `Taskfile.yml`), CI (`.github/workflows`, `.gitlab-ci.yml`, …), and workspace layout. A repo with an existing `.sdlc/` from before setup: keep its features as they are; setup only adds config and lock.

Record stack and packages in `.sdlc/config.json` → `project` (`stack`, and `packages` as `[{name, path, stack}]` for monorepos).

## `justfile` – wrap, don't replace (hard stop)

Write recipes that **call what already exists** (`just test` → `pnpm test`, `make test`, `./gradlew test`, …). Start from the stack templates in `${CLAUDE_PLUGIN_ROOT}/templates/justfile/`; polyglot → `polyglot-root.just` plus a justfile per package. An existing justfile: add only the missing contract recipes. Show the diff; the user approves.

Check: `$S contract` → `ok: true` (every module too), `just.ok: true` (offer `just.install` if not, as a hard stop).

## `baseline` – what fails today

Run `just install`, then each of `lint`, `typecheck`, `build`, `test` separately (so one failure doesn't hide the others). Render `$S render templates/project/baseline.md .sdlc/baseline.md` then `$S forget .sdlc/baseline.md` (user-owned from now on) and fill it in:

- failing tests by file › name with a one-line failure
- lint/type errors as counts per rule and file (not every line)
- the commit and date

Show it to the user. A failing `install` or `build` is a blocker, not a baseline item: stop and report.

## `audit` – seed the knowledge (parallel, then batched approval)

Dispatch `sdlc:code-explorer` agents in parallel, one per angle; each returns drafts, not files:

1. **Conventions:** naming, layering, error handling, logging, test style, with file:line examples → `knowledge/conventions/*.md` drafts.
2. **History:** `git log` hot files (most changed), reverts, recurring fix areas (`fix` commits clustered by path), large deletions → `knowledge/gotchas/*.md` drafts.
3. **Decisions:** existing ADRs, design docs, READMEs with rationale → `knowledge/decisions/*.md` (migrate) or links from `knowledge/index.md` (leave in place).
4. **Areas:** the real areas of the codebase and their paths → tier-2 rule drafts `.claude/rules/<area>.md` (user-owned; `paths:` with real globs, ≤ 30 lines, each line linking to the tier-3 doc behind it). Also adjust `areas.*` in `.sdlc/config.json` where the defaults miss this layout (e.g. migrations live in `db/migrate/`).

Present each batch as a list of titles with one-line summaries; the user approves, edits or drops per item. Write only what's approved (follow `sdlc:managing-knowledge` for format and linking).

## `ai-config` – migrate existing AI instructions (one diff per source)

For each of `CLAUDE.md` (over ~60 lines), `AGENTS.md`, `.cursor/rules/`, `.cursorrules`, `.github/copilot-instructions.md`, `.specify/`, `docs/adr/`: propose where each part goes in the tiers (always-true and short → CLAUDE.md; path-specific → `.claude/rules/<area>.md`; detail → `knowledge/`). Show one diff per source. Originals stay unless the user approves deleting them. Never `@import` the knowledge folder into CLAUDE.md.

## `ci`

Existing CI already runs build/lint/test → leave it; suggest (don't apply) switching its commands to `just` recipes so local and CI can't drift. No CI, or CI that doesn't verify → offer the workflow as in `greenfield.md` → `ci` (hard stop: it's a new required check for everyone).

Then continue with the common steps in `SKILL.md`. In `lint`, new warnings from the sdlc lint snippet go into the baseline counts rather than being fixed during setup.
