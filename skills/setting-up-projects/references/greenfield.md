# Greenfield setup

The repo has no source code yet. Goal: a minimal skeleton whose commands all pass on day one, so Stage 5 and CI have real commands from the first feature.

## `stack` – interview, then propose (hard stop)

Ask only what you can't infer, a few questions at a time, with a suggested answer each:

- What is being built: library, CLI, API service, web app, mobile app, several of these (→ monorepo)?
- Runtime and language per part; package manager; test runner. Default to the ecosystem's current mainstream choice and say why in one line.
- Where it deploys (only if it changes the skeleton, e.g. a Dockerfile).

Propose: the stack per package, the directory layout, the generator command for each package, and the five commands per package (below). Keep it to what the first feature needs; no auth, DB, Docker, or infra "for later" unless the user named it. **The user approves before anything is generated.**

## `skeleton` – generate with the official tools

Use the ecosystem's own generator (`pnpm create vite`, `npx create-next-app`, `uv init`, `cargo new`, `go mod init`, `dart create`, `flutter create`, `dotnet new`, `gradle init`, …) rather than hand-writing project files. Then apply only: strict type checking, the test runner, a lint/format tool, and one passing smoke test per package. Pin the package manager and toolchain (`packageManager` field for corepack, `.python-version`, `rust-toolchain.toml`, …) so CI matches local.

## `commands`

Write the project's own commands into `.sdlc/config.json` (only what differs from the defaults goes there):

```json
"project": {"kind": "greenfield", "stack": ["typescript"]},
"commands": {"install": "pnpm install --frozen-lockfile", "test": "pnpm test", "lint": "pnpm lint",
             "typecheck": "pnpm exec tsc --noEmit", "build": "pnpm build"}
```

Use the commands the generated project already defines (`package.json` scripts, `pyproject` tool config, `cargo`, `go`, …); add a script to the project rather than a long inline command. A step that doesn't exist for the stack is `null` (e.g. `"build": null` for a Python app, `"typecheck": null` for shell scripts).

Monorepo or several stacks: `packages` instead of `commands`, one entry per package with `name`, `path`, `stack` and its own five commands, each run from its `path`. A workspace tool's root-level test command (`pnpm -r test`, `turbo run test`) can go in root `commands.test`; it then counts as a full run for every package.

Check: `$S contract` → `ok: true` and `tools_ok: true`. Then `$S run-commands` (install first, then the verify plan, each in its `cwd`, every exit recorded in the lock); every command must have run and exited 0. Fix the skeleton, not the command, if they don't.

## `ci`

`$S render builtin:ci .github/workflows/sdlc-verify.yml --class seeded` generates the workflow from the commands: one toolchain setup per stack, then install and the verify steps per package (with `working-directory`), on an OS matrix from `ci.os`. Windows contributors → set `"ci": {"os": ["ubuntu-latest", "windows-latest"]}` in `.sdlc/config.json` first. A stack without a known setup action gets a `# TODO` line in the workflow: fill it in and tell the user.

Then continue with the common steps in `SKILL.md`. Greenfield has no baseline: every command passes, so there are no known failures.
