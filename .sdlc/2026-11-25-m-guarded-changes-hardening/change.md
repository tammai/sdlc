# Guarded changes catch dependency sources, more suppressions and more manifests

## Why

**Request:** "work on open issues", the guarded-changes todos in `.sdlc/todo.md`. They came from the push security review of PR #139 and from code review rounds 2 and 3 of `2026-11-24-m-gh-92-guarded-changes`. With `guards.dependencies` or `guards.lint_config` on (ADR 0032), the following changes go by unflagged today:

- a change to where dependencies come from: an index URL, an override, a `replace`, a registry config;
- several common suppression comments;
- dependencies in `dev-requirements.txt`, `requirements.in` and an inline `optional-dependencies` table.

Some of the guard's own handling is also wrong:

- an uncommitted plain move re-flags a file's suppressions;
- an unreadable Base manifest gets a misleading label;
- an Allow can cover a label the question excludes, or another feature's item;
- a few calls in `verify.guarded_failures` can raise instead of reporting `guarded_not_checked`.

## Decisions

| Decision | Chosen | Ruled out | Why |
|---|---|---|---|
| How a dependency source shows | One item per changed file, `dependency source <file> (<hash>)`. It hashes the source-relevant part: the option lines of a requirements file, package.json's `overrides`, `resolutions` and `pnpm.overrides`, go.mod's `replace` lines, Cargo's `[patch.*]` and `[replace]` tables, and the whole of `.npmrc`, `.yarnrc`, `.yarnrc.yml`, `pip.conf` and `pip.ini`. | An item per option or URL | Sources are few and rarely change. One item per file keeps the Allow question short, and the hash asks again after any later change. |
| An Allow that excludes | A question with an exclusion word (`except`, `excluding`, `but not`, `other than`, `apart from`, `without`) allows nothing; the agent asks again naming only what to allow | Parsing the sentence | Fails closed. The orchestrator already says to name each label to allow. |
| Which feature an Allow covers | The feature the question names, when it names a waiting one. Otherwise every feature only when a single feature has the named label pending. | Every feature with the label (today) | An answer for one feature must not allow another feature's change. |
| An unreadable Base manifest | Its dependencies count as none, so each dependency in the new manifest is its own item | One `unreadable` item hashing the new text | Fails closed, with labels the user can read. A new manifest that can't be read keeps today's `unreadable` item. |
| A plain move | An untracked source whose deleted tracked file has the same name (a unique match) is compared with that file's Base | Counting it as all new | A move by `mv` before `git add` is the same file. |

## Acceptance criteria

- **AC-001** A changed dependency source fails verify until allowed: a requirements option line (`--index-url`, `-e`), package.json `overrides`, go.mod `replace`, Cargo `[patch.crates-io]`, and a new or changed `.npmrc`.
- **AC-002** Each of these added comments is a suppression: `# ruff: noqa`, `# flake8: noqa`, `# mypy: ignore-errors`, `# pyright: basic`, `/* eslint no-console: "off" */`, `// oxlint-disable`, `// deno-lint-ignore`.
- **AC-003** A new dependency in `dev-requirements.txt`, in `requirements.in`, or in an inline `optional-dependencies = { dev = [...] }` table is flagged.
- **AC-004** A source file moved with `mv` and not yet staged is compared with its old self, so its existing suppressions aren't flagged again.
- **AC-005** When the Base manifest can't be parsed, each dependency the new manifest names is flagged by name.
- **AC-006** The `Allow` answer allows nothing when its question excludes something, and allows only the named feature's items when the question names one.
- **AC-007** An error anywhere in the guarded check reports `guarded_not_checked`, never a traceback.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_guarded_hardening.py › GuardedHardeningTest.test_a_changed_dependency_source_is_an_item | `py -3.10 -m unittest discover -s tests -t tests -p test_guarded_hardening.py -k test_a_changed_dependency_source_is_an_item` |
| AC-002 | tests/test_guarded_hardening.py › GuardedHardeningTest.test_more_suppressions_are_counted | `py -3.10 -m unittest discover -s tests -t tests -p test_guarded_hardening.py -k test_more_suppressions_are_counted` |
| AC-003 | tests/test_guarded_hardening.py › GuardedHardeningTest.test_more_manifests_are_read | `py -3.10 -m unittest discover -s tests -t tests -p test_guarded_hardening.py -k test_more_manifests_are_read` |
| AC-004 | tests/test_guarded_hardening.py › GuardedHardeningTest.test_a_plain_move_keeps_its_suppressions | `py -3.10 -m unittest discover -s tests -t tests -p test_guarded_hardening.py -k test_a_plain_move_keeps_its_suppressions` |
| AC-005 | tests/test_guarded_hardening.py › GuardedHardeningTest.test_an_unreadable_base_manifest_flags_each_dependency | `py -3.10 -m unittest discover -s tests -t tests -p test_guarded_hardening.py -k test_an_unreadable_base_manifest_flags_each_dependency` |
| AC-006 | tests/test_guarded_hardening.py › GuardedAllowTest.test_an_allow_covers_only_what_its_question_allows | `py -3.10 -m unittest discover -s tests -t tests -p test_guarded_hardening.py -k test_an_allow_covers_only_what_its_question_allows` |
| AC-007 | tests/test_guarded_hardening.py › GuardedAllowTest.test_an_error_in_the_check_is_not_checked | `py -3.10 -m unittest discover -s tests -t tests -p test_guarded_hardening.py -k test_an_error_in_the_check_is_not_checked` |

## Must never break

- Every existing guarded-changes test passes untouched: a version bump isn't an item; an Allow naming the item, or a typed `allow`, lets verify pass.
- Without the guards on, nothing is read.
- An existing allow keeps covering its item: the ids of today's items don't change.

## Out of scope

- A git-ignored lint config or manifest, or a `.gitignore` change that hides one (todo item 3). Seeing it means listing ignored files, an open set (`node_modules`, a developer's own `.npmrc`). That is the kind of guard that didn't converge in `2026-11-25-m-approval-hardening`; it stays a todo.

## Review

No review ran: low risk, no trigger fired (2 source files, no public surface); every AC red then green (verify.py); full suite 940 OK on Python 3.10.
