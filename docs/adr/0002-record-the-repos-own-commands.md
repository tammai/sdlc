# ADR 0002: Record the repo's own commands instead of a justfile

- **Status:** Accepted, 2026-10-22. Amends [ADR 0001](0001-project-setup-upgrade-eject.md). Supersedes the justfile command contract tried earlier the same day.
- **Deciders:** Tâm Mai.

## Context

Stages, the verifier, CI, the permission allowlist and the Stage 5 freshness hook all need to run a project's install, test, lint, typecheck and build. The first design gave every set-up repo a root `justfile` with fixed recipe names that wrapped the real tools, with per-stack starter templates and a polyglot root that loaded each package's justfile as a just module (just ≥ 1.31).

Trying it showed the cost: `just` is one more tool everyone must install, and on an unsupported Homebrew setup (an Intel Mac on a new macOS, "Tier 3") `brew install just` compiles Rust and LLVM from source and runs for hours. Distro packages are often older than 1.31. For a team rollout that's a real barrier, for little gain: every project already has commands that work.

## Decision

Setup records the commands the repo already uses in `.sdlc/config.json`. No wrapper tool.

- `commands` holds `install`, `test`, `lint`, `typecheck`, `build` exactly as the team runs them (`pnpm test`, `go test ./...`, `make lint`, `./gradlew build`). A step that doesn't apply to a stack is `null`. `verify.order` (default lint, typecheck, build, test) is the sequence Stage 5 and CI run.
- A monorepo lists `packages: [{name, path, stack, commands}]`, each run from its path. A polyglot repo is packages with different stacks. A workspace-wide test command (`turbo run test`, `pnpm -r test`) may sit in root `commands.test` and counts for every package.
- **Freshness is per package.** An edit marks the owning package stale (a file outside every package: all of them); that package's test command run in its directory makes it fresh. The Stop block names each stale package and the exact command.
- **CI is generated** from the commands (`scaffold.py render builtin:ci`): one toolchain setup per stack, then install and the verify steps per package with `working-directory`, every step under `shell: bash` (Git Bash on Windows runners), over an OS matrix from config. Recorded as seeded, so upgrades regenerate it and ask first if it was edited.
- The allowlist is derived from the commands (`Bash(<command>:*)`); `scaffold.py contract` and `/sdlc:doctor` check that each command's tool is installed.

### Alternatives considered

| Option | Why not |
|---|---|
| justfile contract (first design) | install cost above; a second place to keep in sync with the real scripts |
| Makefile | not installed on Windows, needs the same `sh` as just, awkward argument passing, macOS ships GNU Make 3.81 |
| Taskfile (go-task) | runs on plain Windows, but still an extra tool to install; kept in mind only if Windows without Git Bash becomes a requirement |
| One root command per action for monorepos | simpler hook, but forces polyglot repos to add an aggregator script, and any edit makes every package stale |

## Consequences

- **Good:** nothing to install; commands are the ones developers already know; per-package freshness means an edit in one package only reruns that package's tests.
- **Costs:** the plugin reads commands from config rather than one fixed interface, so CI has to be generated rather than templated; filters inside custom commands are detected heuristically.
- **Platforms:** commands run in the shell Claude Code uses (Git Bash on Windows), so they must work there.
