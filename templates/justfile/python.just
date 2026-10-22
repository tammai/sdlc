# Command contract for the sdlc plugin. Required recipes: install test lint typecheck build verify.
# Use as a repo-root justfile, or as one package of a polyglot monorepo (see polyglot-root.just).
# Recipes wrap the project's own tools; edit them freely, but keep the names.

default:
    @just --list

install:
    uv sync --frozen

# Full test suite. Extra args filter it (`just test tests/test_a.py`), which doesn't count as a full run.
test *args:
    uv run pytest {{args}}

lint:
    uv run ruff check .
    uv run ruff format --check .

typecheck:
    uv run mypy .

# No artifact for an application; use `uv build` for a library
build:
    @echo "no build step"

verify: lint typecheck build test
