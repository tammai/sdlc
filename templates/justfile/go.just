# Command contract for the sdlc plugin. Required recipes: install test lint typecheck build verify.
# Use as a repo-root justfile, or as one package of a polyglot monorepo (see polyglot-root.just).
# Recipes wrap the project's own tools; edit them freely, but keep the names.

default:
    @just --list

install:
    go mod download

# Full test suite. A package argument (`just test ./internal/auth`) doesn't count as a full run.
test pkgs="./...":
    go test {{pkgs}}

lint:
    golangci-lint run

# The compiler is the type checker; vet adds the static checks
typecheck:
    go vet ./...

build:
    go build ./...

verify: lint typecheck build test
