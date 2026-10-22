# Command contract for the sdlc plugin. Required recipes: install test lint typecheck build verify.
# Use as a repo-root justfile, or as one package of a polyglot monorepo (see polyglot-root.just).
# Recipes wrap the project's own tools; edit them freely, but keep the names.
# Java / Kotlin with the Gradle wrapper.

default:
    @just --list

install:
    ./gradlew dependencies --quiet > /dev/null

# Full test suite. Extra args filter it (`just test --tests '*LoginTest'`), which doesn't count as a full run.
test *args:
    ./gradlew test {{args}}

# check without tests: ktlint/detekt/spotless/checkstyle, whatever the build applies
lint:
    ./gradlew check -x test

typecheck:
    ./gradlew classes testClasses

build:
    ./gradlew assemble

verify: lint typecheck build test
