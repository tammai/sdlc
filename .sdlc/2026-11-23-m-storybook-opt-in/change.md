# Storybook as an opt-in living design system

## Why

**Request (verbatim):** from `.sdlc/todo.md`: "Adopt Storybook as a living design system, as an optional opt-in (not the default) — not built yet; today the design system is `.sdlc/design-system.md` and the ui-reviewer checks against it (2026-11-20)". The user chose it next (2026-11-23).

Today the design system is a document, `<docs>/design-system.md`. It can drift from the components, and the UI review checks code against prose. A team that already keeps its components in Storybook has a catalog that runs. With this opt-in, the stories become the system: each component a change touches has stories for the states the spec names, the UI review checks against them, and the catalog's build or test runs in verify.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| A switch inside the builtin design mode: `"storybook": true` in `.sdlc/config.json`, set by `scaffold.py storybook on\|off` (setup's design step, `/sdlc:setup design`), refused without a `.storybook/` folder and in impeccable mode | a third design mode | impeccable has its own system (`DESIGN.md`); a mode would duplicate the builtin rules, guardrail and review |
| `<docs>/design-system.md` names Storybook as the source of truth for components (tokens stay where they are) | copying the catalog into the doc | the catalog is the living part; the doc points at it |
| UI work: the `## UI mapping` names each component's story; a new or changed component gets a story for each state the spec names (loading, empty, error, success), in the same change, as a task with an AC | stories later | a story added after the screen ships is the drift this prevents |
| The UI review treats a component used without a story as off-system and checks the stories cover the named states | review the doc only | the stories are the system now |
| An optional `commands.storybook` (the team's Storybook build, e.g. `npx storybook build --test`; the test runner needs a served Storybook) runs in verify right after `build` (in a monorepo, a root one after the packages'); unset, nothing runs | always build Storybook | a build costs time; the team chooses the command, like every other |
| Doctor warns when `storybook` is on but `.storybook/` is missing | silent | a switch with nothing behind it reviews against nothing |
| Code review r1: switching to impeccable clears `storybook` (and it reads as off outside builtin); a `.storybook/` in a package counts and the root's `commands.storybook` runs in a monorepo; a custom `verify.order` without `storybook` is warned of; `storybook-static/` is build output, never drift or committed; the suggested command is the build (the test runner needs a served Storybook) | — | SB1–SB11 |

## Acceptance criteria

- **AC-001** `scaffold.py storybook on` records `"storybook": true` only when `.storybook/` exists and the design mode isn't impeccable (else exit 2); `off` removes it; any other value is refused; no argument prints it.
- **AC-002** `commands.storybook`, when set, runs in the verify plan right after `build`; unset, the plan is as before.
- **AC-003** Doctor warns when `storybook` is on and `.storybook/` is missing, and is ok when it exists.
- **AC-004** `ui-work.md`, the UI reviewer, the design-mode reference and the design-system template state the Storybook rules, and the design-mode reference gives the `storybook` command.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_storybook.py › StorybookTest.test_storybook_is_turned_on_only_where_it_exists_and_in_builtin_mode | `python3.10 -m unittest discover -s tests -t tests -p test_storybook.py -k test_storybook_is_turned_on_only_where_it_exists_and_in_builtin_mode` |
| AC-002 | tests/test_storybook.py › StorybookTest.test_the_storybook_command_runs_after_build_when_set | `python3.10 -m unittest discover -s tests -t tests -p test_storybook.py -k test_the_storybook_command_runs_after_build_when_set` |
| AC-003 | tests/test_storybook.py › StorybookTest.test_doctor_warns_when_storybook_is_on_but_missing | `python3.10 -m unittest discover -s tests -t tests -p test_storybook.py -k test_doctor_warns_when_storybook_is_on_but_missing` |
| AC-004 | tests/test_storybook.py › StorybookTest.test_the_ui_flow_and_review_name_the_storybook_rules | `python3.10 -m unittest discover -s tests -t tests -p test_storybook.py -k test_the_ui_flow_and_review_name_the_storybook_rules` |

## Must never break

- A repo without `storybook` or `commands.storybook` works exactly as before (the verify plan, the UI flow, the review).
- impeccable mode is untouched.

## Review

- **What fired:** a code review, because Public Surface isn't none (the `storybook` command and config key, `commands.storybook`). Risk is low, so it wasn't asked. It ran as the built-in `code-review high --max-findings all`, and I rated each finding.
- **Round 1, FAIL.**
  - Medium bugs, all fixed test first:
    - SB1: Storybook stayed on in impeccable mode.
    - SB2 and SB3: monorepo command and catalog.
    - SB4: a custom verify order skipped the step silently.
    - SB5: an unusable test-runner suggestion.
    - SB6: `storybook-static/` showed as drift or got committed.
  - Lows SB7 to SB11: fixed.
- **Round 2, PASS** (no high). Its bugs were fixed test first and closed by verify:
  - the duplicate spec ID;
  - `storybook-static/` in the hooks' reviews;
  - doctor's hint per problem;
  - the command map;
  - the cleared switch now said;
  - the docs.
- **Ticket:** R2-12, which predates this change: doctor never checks root-scope commands.
- **Reports:** `.sdlc/.work/findings/2026-11-23-m-storybook-opt-in/code-reviewer-r1.md` and `-r2.md`.
- **Tests:** every AC red then green, re-red at Base after each test change. Full suite 856 OK on Python 3.10.
- **Lessons filed:** none.
