# Command contract for the sdlc plugin. Required recipes: install test lint typecheck build verify.
# Use as a repo-root justfile, or as one package of a polyglot monorepo (see polyglot-root.just).
# Recipes wrap the project's own tools; edit them freely, but keep the names.
# Package manager: swap pnpm for npm / yarn / bun to match the lockfile.
# Single-language pnpm/npm/yarn workspace: run each recipe with -r (pnpm) or --workspaces (npm) instead of using modules.

default:
    @just --list

install:
    pnpm install --frozen-lockfile

# Full test suite. Extra args filter it (`just test src/a.test.ts`), which doesn't count as a full run.
test *args:
    pnpm test {{args}}

lint:
    pnpm lint

typecheck:
    pnpm exec tsc --noEmit

build:
    pnpm build

verify: lint typecheck build test
