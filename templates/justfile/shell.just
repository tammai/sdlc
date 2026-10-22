# Command contract for the sdlc plugin. Required recipes: install test lint typecheck build verify.
# Use as a repo-root justfile, or as one package of a polyglot monorepo (see polyglot-root.just).
# Recipes wrap the project's own tools; edit them freely, but keep the names.
# For a folder of shell scripts (e.g. scripts/ or tools/). Needs shellcheck, shfmt, and bats-core for tests.

default:
    @just --list

install:
    @echo "nothing to install"

# bats tests under test/. Extra args filter it (`just test test/deploy.bats`), which doesn't count as a full run.
test *args:
    bats {{ if args == "" { "test" } else { args } }}

lint:
    #!/usr/bin/env bash
    set -euo pipefail
    files="$(git ls-files '*.sh' '*.bash')"
    [ -z "$files" ] || { shellcheck $files; shfmt -d $files; }

# Shell has no type checker; shellcheck (in lint) covers what it can
typecheck:
    @echo "n/a for shell"

build:
    @echo "no build step"

verify: lint typecheck build test
