# Guarded changes: a new dependency, a changed lint config or an added suppression waits for the user

## Why

**Request:** GitHub issue #92, part 3 of 4, gap 2: "New dependencies and loosened checks don't stop. A dependency is only recorded in `## Public Surface`, and the audit runs only when Security fires. Edits that weaken lint/type checks (`tsconfig` `strict`, eslint/ruff/mypy config, `@ts-ignore`, `eslint-disable`, `# type: ignore`) have no guard." Proposed: `guards.dependencies` and `guards.lint_config`; an approved dependency runs the stack's audit in Review. Off by default (part 2 added the `guards` key and its acceptance rule, ADR 0032).

## Decisions

| Decision | Chosen | Ruled out | Why |
|---|---|---|---|
| Where it stops | `verify.py`'s full run fails on each item the user hasn't allowed | a PreToolUse deny per edit; a Stop block | verify runs before every part's commit, Review and Ship, and sees every route (file tools, `npm install`, other hosts) with no command parser and no new hook answer; the edit itself is not prevented, only kept from being built on, reviewed or shipped |
| What is an item | a dependency name new since Base in a known manifest; any change to a known lint or type config file (or its section in `pyproject.toml`, `setup.cfg`, `tox.ini`); a suppression comment whose count in a source file grew since Base | judging whether a config change "weakens" | judging is guesswork; any change is cheap to allow; a version bump, a removed or moved suppression is free |
| Manifests and config names | a fixed list in the plugin | the repo's `commands` | repo config is agent-editable (`repo-config-is-untrusted`) |
| TOML, YAML, Gemfile, go.mod | a simple name rule that over-flags rather than misses | a parser | no `tomllib` before Python 3.11, no YAML in the stdlib |
| Allowing | the answer `Allow` (a trailing `(Recommended)` aside) to a question headed `Allow change` that names each item by its label, recorded by `hooks/guarded_changes.py` through `user_answer.py`; or a typed `allow`, which allows every item the last verify listed for the one feature waiting; an allow belongs to the feature that asked | any next prompt | as in ADR 0031; the issue's header `Guarded change` is 14 characters, past the question tool's 12 |
| An item's identity | its content: the dependency's name and file, the config file and its hash, the suppression, file and count | the file alone | a later change to the same file asks again |
| Audit trail | `ship.py` writes the allowed items into the Gate log | none | `.sdlc/.work` is gitignored; the record is the point |
| The audit | an allowed dependency makes Review run the stack's dependency audit (`dependency-audit-r<N>.md`), as an instruction | an enforced check | the audit command is per stack and needs a network |

## Acceptance criteria

- **AC-001** With `guards.dependencies` on, a dependency added to `package.json` or `pyproject.toml` since Base fails `verify.py`, naming it; a version bump doesn't. Without the guards nothing is checked.
- **AC-002** The user's `Allow` to an `Allow change` question naming the item, or a typed `allow`, lets `verify.py` pass; another answer, or a question that doesn't name the item, doesn't.
- **AC-003** With `guards.lint_config` on, a changed `tsconfig.json` fails `verify.py`, and so does an added `// @ts-ignore`; a removed suppression doesn't.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_guarded_changes.py › GuardedChangesTest.test_a_new_dependency_fails_verify_and_a_version_bump_does_not | `py -3.10 -m unittest discover -s tests -t tests -p test_guarded_changes.py -k test_a_new_dependency_fails_verify_and_a_version_bump_does_not` |
| AC-002 | tests/test_guarded_changes.py › GuardedChangesTest.test_the_users_allow_for_the_named_item_lets_verify_pass | `py -3.10 -m unittest discover -s tests -t tests -p test_guarded_changes.py -k test_the_users_allow_for_the_named_item_lets_verify_pass` |
| AC-003 | tests/test_guarded_changes.py › GuardedChangesTest.test_a_changed_lint_config_or_an_added_suppression_fails_verify | `py -3.10 -m unittest discover -s tests -t tests -p test_guarded_changes.py -k test_a_changed_lint_config_or_an_added_suppression_fails_verify` |

## Must never break

- With no guard on, verify behaves as in 3.15: nothing is checked, and the only extra read is the guards lookup itself (config, the trust anchor's record, and HEAD's config when there's no record), which the S lock already needs (`test_without_the_guards_nothing_is_checked`).
- `guards.s_tests` and the guards' trust-anchor acceptance work as before.

## Out of scope

- Preventing the edit itself (a per-call deny); asked for only if the user wants it.
- Part 4 of #92 (UI evidence and the setup profile question).

## Review

- **Fired:** code review, because `## Public Surface` lists `guards.dependencies` and `guards.lint_config`. Security and UI review didn't fire: risk low, no sensitive path.
- **Ran:** `sdlc:code-reviewer` on opus, three rounds. The user granted round 3 past the cap of 2.
- **Round 1:** FAIL, with four highs and six mediums. Fixed test first:
  - H1: each question's own answer counts.
  - H2: TOML bracket depth, dotted tables, pubspec indent, and section headers with comments.
  - H3: BOM and UTF-16 decoding, git failure and a bad Base fail closed, and unreadable manifests become items.
  - M2: `pending` is per feature.
  - M3: taking back an allowed suppression stays allowed.
  - M5: names are sanitised.
  - M6: the Gate log line has a test.

  Fixed by reading, without a test (see Deviations): H4 (the must-never-break line was restated: the guards lookup is the one read), M1, M4 (workbench repos), M7, M8, M9, and L1–L4.
- **Round 2:** FAIL, with two highs. Fixed test first:
  - R2-H1: allows are scoped per feature.
  - R2-H2: an INI section header is any column-0 bracket line.
  - R2-M1: the form-feed crash; any error is caught as `guarded_not_checked`.
  - R2-M2: the diff's prefixes and quoting are fixed, with a both-versions fallback.

  Also fixed: R2-M3 and L1, L5.
- **Round 3:** PASS. Its R3-M1 (an unchanged `git mv`) and R3-M2 (an added line starting `++ `) were fixed test first.
- **Tickets:** the remaining lows are in `.sdlc/todo.md`.
- **Note for the user:** the must-never-break line about "no extra git reads" was restated, not met as first written: with no guard on, verify still reads the guards setting (config, the trust anchor's record, and HEAD's config when there is no record).
- **Lessons filed:** None
