# Command contract for the sdlc plugin. Required recipes: install test lint typecheck build verify.
# Use as a repo-root justfile, or as one package of a polyglot monorepo (see polyglot-root.just).
# Recipes wrap the project's own tools; edit them freely, but keep the names.

default:
    @just --list

install:
    dart pub get --enforce-lockfile

# Full test suite. Extra args filter it (`just test test/a_test.dart`), which doesn't count as a full run.
test *args:
    dart test {{args}}

lint:
    dart format --output=none --set-exit-if-changed .
    dart analyze --fatal-infos

# dart analyze (in lint) is the type checker
typecheck:
    dart analyze --fatal-warnings

# For a CLI: dart compile exe bin/main.dart -o build/main. A library has no build step.
build:
    @echo "no build step"

verify: lint typecheck build test
