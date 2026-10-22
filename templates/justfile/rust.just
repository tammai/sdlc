# Command contract for the sdlc plugin. Required recipes: install test lint typecheck build verify.
# Use as a repo-root justfile, or as one package of a polyglot monorepo (see polyglot-root.just).
# Recipes wrap the project's own tools; edit them freely, but keep the names.

default:
    @just --list

install:
    cargo fetch --locked

# Full test suite. Extra args filter it (`just test auth::`), which doesn't count as a full run.
test *args:
    cargo test --locked {{args}}

lint:
    cargo fmt --check
    cargo clippy --all-targets --locked -- -D warnings

typecheck:
    cargo check --all-targets --locked

build:
    cargo build --locked

verify: lint typecheck build test
