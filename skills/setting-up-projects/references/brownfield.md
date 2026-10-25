# Brownfield setup

The repo has code, history and habits. Goal: adopt sdlc without breaking anything, record what's already failing so features aren't blamed for it, and turn what the codebase already knows into knowledge the agent can load. **Nothing the audit drafts is written without the user's approval.**

## `stack` – detect (no questions unless ambiguous)

Read, don't guess: lockfiles and manifests (`package.json`, `pnpm-workspace.yaml`, `pyproject.toml`, `go.mod`/`go.work`, `Cargo.toml`, `pubspec.yaml`, `*.csproj`, `build.gradle*`), existing task runners (`Makefile`, `justfile`, `package.json` scripts, `Taskfile.yml`: their targets are just commands like any other), CI (`.github/workflows`, `.gitlab-ci.yml`, …), and workspace layout. A repo with an existing `.sdlc/` from before setup: keep its features as they are; setup only adds config and lock.

Record stack and packages in `.sdlc/config.json` → `project` (`stack`, and `packages` as `[{name, path, stack}]` for monorepos).

## `commands` – record what already exists (hard stop)

Find the commands the repo **already uses** for `commands` with `install`, `test`, `lint`, `typecheck`, `build` (from `package.json` scripts, `Makefile`/`justfile` targets, `pyproject` tool config, CI steps, README). Don't invent new ones; a step the repo doesn't have is `null`, and say so (it's a candidate for a later S-track fix, not something to add during setup). Setup never changes the product's manifest or dependencies: no new fields (`bin`, `engines`, `packageManager`, `scripts` entries, …) and no new devDependencies or tooling (a linter, `globals`, a formatter) unless the user asks for them at this prompt. Monorepo: `packages` with `name`, `path`, `stack` and each package's own commands, run from its `path`; a workspace-wide test command (`pnpm -r test`, `turbo run test`, `nx run-many -t test`) can go in root `commands.test`.

**Stop here:** show the proposed commands (per package, with where each came from) in one message and end your turn. Write them to `.sdlc/config.json` only after the user approves or corrects them, and don't run the baseline before that.

Check: `$S contract` → `ok: true`, and `tools_ok: true` (a tool that isn't installed: tell the user which, don't install it without asking).

## `baseline` – what fails today

Run `$S run-commands`: it runs install, then every verify command, each in its `cwd` and separately (so one failure doesn't hide the others), and records each exit in the lock. A command listed under `not_runnable` couldn't start (tool missing, timeout): fix the command with the user before going on; setup isn't complete with one. A non-zero exit is fine here; it's what the baseline records. Read each command's output from its `tail` or run it again yourself. Render `$S render templates/project/baseline.md .sdlc/baseline.md` then `$S forget .sdlc/baseline.md` (user-owned from now on) and fill it in:

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

Present each batch as a list of titles with one-line summaries and end your turn; the user approves, edits or drops per item. Write only what's approved (follow `sdlc:managing-knowledge` for format and linking). A skipped audit (too small a repo) means no drafts: no knowledge docs or area rules are written without an approved batch.

## `ai-config` – migrate existing AI instructions (one diff per source)

For each of `CLAUDE.md` (over ~60 lines), `AGENTS.md`, `.cursor/rules/`, `.cursorrules`, `.github/copilot-instructions.md`, `.specify/`, `docs/adr/`: propose where each part goes in the tiers (always-true and short → CLAUDE.md; path-specific → `.claude/rules/<area>.md`; detail → `knowledge/`). Show one diff per source. Originals stay unless the user approves deleting them. `AGENTS.md` itself always stays: Codex, Cursor and Antigravity read it, and the `agents` step adds the sdlc block there. Only offer to delete text you migrated out of it. Never `@import` the knowledge folder into CLAUDE.md.

## `ci`

Existing CI already runs build/lint/test → leave it; point out any step whose command differs from `.sdlc/config.json`, since local and CI shouldn't drift. No CI, or CI that doesn't verify → offer the generated workflow as in `greenfield.md` → `ci` (hard stop: it's a new required check for everyone). Either way, offer the invariants check from `greenfield.md` → `ci`: it checks the sdlc files themselves, which no existing CI does (same hard stop).

Then continue with the common steps in `SKILL.md`. In `lint`, new warnings from the sdlc lint snippet go into the baseline counts rather than being fixed during setup.
