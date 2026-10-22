# Greenfield setup

The repo has no source code yet. Goal: a minimal skeleton whose `just verify` passes on day one, so Stage 5 and CI have real commands from the first feature.

## `stack` – interview, then propose (hard stop)

Ask only what you can't infer, a few questions at a time, with a suggested answer each:

- What is being built: library, CLI, API service, web app, mobile app, several of these (→ monorepo)?
- Runtime and language per part; package manager; test runner. Default to the ecosystem's current mainstream choice and say why in one line.
- Where it deploys (only if it changes the skeleton, e.g. a Dockerfile).

Propose: the stack per package, the directory layout, the generator command for each package, and the justfile layout (single, or polyglot root + per-package). Keep it to what the first feature needs; no auth, DB, Docker, or infra "for later" unless the user named it. **The user approves before anything is generated.**

## `skeleton` – generate with the official tools

Use the ecosystem's own generator (`pnpm create vite`, `npx create-next-app`, `uv init`, `cargo new`, `go mod init`, `dart create`, `flutter create`, `dotnet new`, `gradle init`, …) rather than hand-writing project files. Then apply only: strict type checking, the test runner, a lint/format tool, and one passing smoke test per package. Pin the package manager (`packageManager` field for corepack, `.python-version`, `rust-toolchain.toml`, …) so CI matches local.

## `justfile`

Start from `${CLAUDE_PLUGIN_ROOT}/templates/justfile/<stack>.just` (stacks: node, python, go, rust, dart, flutter, shell, gradle, dotnet). Several stacks or packages → copy `polyglot-root.just` to the root, one stack justfile per package, and keep its `mod` lines and `packages` variable in step. Adapt the recipe bodies to the generated scripts; keep the recipe names.

Check: `$S contract` → `ok: true` (every module too), `just.ok: true`. Run `just install` and `just verify`; both must pass. Fix the skeleton, not the recipe, if they don't.

## `ci`

Render the workflow for the stack: `$S render templates/project/ci/sdlc-verify-<node|python|go>.yml .github/workflows/sdlc-verify.yml --class seeded`. Windows contributors → set `"ci": {"os": ["ubuntu-latest", "windows-latest"]}` in `.sdlc/config.json` first.

No template for the stack, or several stacks: write the workflow yourself from the same shape (checkout → `extractions/setup-just@v2` → each toolchain's setup action → `just install` → `just verify`, `defaults.run.shell: bash`, OS matrix from config), then `$S record seeded .github/workflows/sdlc-verify.yml` (no `--template`: upgrades leave it alone).

Then continue with the common steps in `SKILL.md`. Greenfield has no baseline: `just verify` passes, so there are no known failures.
