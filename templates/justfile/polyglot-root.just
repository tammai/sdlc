# Root command contract for a polyglot monorepo (sdlc). Required recipes: install test lint typecheck build verify.
# Each package has its own justfile with the same recipes (start from templates/justfile/<stack>.just) and is
# loaded as a module below. Root recipes run every package, or one: `just test api`. Needs just >= 1.31.
# Keep `packages` in step with the mod lines: name:path, space-separated.

mod api 'services/api'
mod web 'apps/web'
mod scripts 'scripts'

packages := "api:services/api web:apps/web scripts:scripts"

default:
    @just --list --list-submodules

# Run one contract recipe in every package (or just `pkg`), stopping at the first failure
[private]
each recipe pkg="":
    #!/usr/bin/env bash
    set -euo pipefail
    ran=0
    for entry in {{packages}}; do
      name="${entry%%:*}"
      if [ -z "{{pkg}}" ] || [ "{{pkg}}" = "$name" ]; then
        echo "▶ $name: {{recipe}}"
        just "$name" {{recipe}}
        ran=1
      fi
    done
    [ "$ran" = 1 ] || { echo "unknown package: {{pkg}}" >&2; exit 1; }

install pkg="": (each "install" pkg)

# Full suite across all packages. `just test <pkg>` runs one package, which doesn't count as a full run.
test pkg="": (each "test" pkg)

lint pkg="": (each "lint" pkg)

typecheck pkg="": (each "typecheck" pkg)

build pkg="": (each "build" pkg)

verify pkg="": (each "verify" pkg)

# Test only packages with changes since `base` (committed, uncommitted and untracked)
test-affected base="origin/main":
    #!/usr/bin/env bash
    set -euo pipefail
    changed="$(git diff --name-only "{{base}}"...HEAD; git diff --name-only HEAD; git ls-files --others --exclude-standard)"
    for entry in {{packages}}; do
      name="${entry%%:*}"; path="${entry#*:}"
      if grep -q "^$path/" <<<"$changed"; then echo "▶ $name: test"; just "$name" test; fi
    done
