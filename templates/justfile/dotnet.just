# Command contract for the sdlc plugin. Required recipes: install test lint typecheck build verify.
# Use as a repo-root justfile, or as one package of a polyglot monorepo (see polyglot-root.just).
# Recipes wrap the project's own tools; edit them freely, but keep the names.

default:
    @just --list

install:
    dotnet restore --locked-mode

# Full test suite. Extra args filter it (`just test --filter Login`), which doesn't count as a full run.
test *args:
    dotnet test --no-restore {{args}}

lint:
    dotnet format --verify-no-changes --no-restore

typecheck:
    dotnet build --no-restore -warnaserror

build:
    dotnet build --no-restore -c Release

verify: lint typecheck build test
