# Slice B5 plan: setup leaves the product alone

Spec FR-06, AC 7 · Backlog B5. Instructed only: the command contract already accepts `lint: null`, so no code change.

## Tasks

1. `skills/setting-up-projects/references/greenfield.md`: skeleton adds only the generator's output, test runner and smoke test (strict types where available); linter, toolchain pinning and extra manifest fields are opt-in proposal items; an existing manifest means brownfield rules. (FR-06)
2. `references/brownfield.md` and `SKILL.md` `lint` step: no new manifest fields, devDependencies or tooling unless asked; lint only for a linter the project has. (FR-06)
3. Docs: spec 01 SET-FR-044, CHANGELOG.

## Public Surface

- none (skill text only)
