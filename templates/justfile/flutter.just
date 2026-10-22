# Command contract for the sdlc plugin. Required recipes: install test lint typecheck build verify.
# Use as a repo-root justfile, or as one package of a polyglot monorepo (see polyglot-root.just).
# Recipes wrap the project's own tools; edit them freely, but keep the names.

default:
    @just --list

install:
    flutter pub get --enforce-lockfile

# Full test suite. Extra args filter it (`just test test/widget_test.dart`), which doesn't count as a full run.
test *args:
    flutter test {{args}}

lint:
    dart format --output=none --set-exit-if-changed lib test
    flutter analyze

# flutter analyze (in lint) is the type checker
typecheck:
    flutter analyze --no-fatal-infos

# Pick the target CI should prove builds: apk, appbundle, ios --no-codesign, web, ...
build target="web":
    flutter build {{target}}

verify: lint typecheck build test
