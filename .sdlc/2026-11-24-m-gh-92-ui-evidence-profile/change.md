# UI evidence at Ship, and solo or shared checks for setup

## Why

**Request:** GitHub issue #92, part 4 of 4, gap 4: "UI changes ship without visual evidence. Screenshots are taken only when the user asks." Proposed: `ui.screenshots: always`, "when a changed path matches `areas.ui`, Build captures before/after screenshots for each item in `## UI mapping` (Playwright when available, else a `manual` line with the reason) … `ship.py` puts them in the PR body", and "`/sdlc:setup` asks solo or team repo? and writes the matching defaults".

## Decisions

| Decision | Chosen | Ruled out | Why |
|---|---|---|---|
| The switch | `guards.ui_evidence` (`/sdlc:setup guard ui-evidence on`) | `ui.screenshots: always` | it joins the opt-in guards: off by default, turning it off is a trust-anchor notice (ADR 0032) |
| Where it's checked | `ship.py` refuses a change touching `areas.ui` with no image in `<work>/ui/` and no `- manual: <reason>` line under `## UI evidence` in `<change>` | verify | screenshots come once the UI is built; Ship is where the PR gets them |
| The PR body | `ship.py` lists the evidence (each image's path, or the manual reason) in the commit message, which `gh pr create --fill` uses | uploading images | `gh` can't attach images to a PR body; the images are committed in the work folder |
| The setting | `scaffold.py checks solo|shared`, asked in setup with the mode: shared turns on `approval: ml` and every guard, solo takes them out | the key `team`; the word `profile` | `team` already means role agents, and `profile` is the monorepo's lean/large question (code review r1 M5) |

## Acceptance criteria

- **AC-001** With `guards.ui_evidence` on, `ship.py` refuses a change touching `areas.ui` that has no image in `<work>/ui/` and no manual reason, naming the UI evidence; a change outside `areas.ui` ships.
- **AC-002** With an image in `<work>/ui/`, `ship.py` ships and the commit message lists it under `UI evidence`.
- **AC-003** `scaffold.py checks shared` writes `approval: ml` (never lowering a stricter one) and every guard on, `checks solo` takes them out, and an unknown value is refused.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_ui_evidence.py › UiEvidenceTest.test_a_ui_change_without_evidence_is_refused | `py -3.10 -m unittest discover -s tests -t tests -p test_ui_evidence.py -k test_a_ui_change_without_evidence_is_refused` |
| AC-002 | tests/test_ui_evidence.py › UiEvidenceTest.test_screenshots_ship_and_are_listed | `py -3.10 -m unittest discover -s tests -t tests -p test_ui_evidence.py -k test_screenshots_ship_and_are_listed` |
| AC-003 | tests/test_ui_evidence.py › ChecksTest.test_checks_writes_the_solo_or_shared_defaults | `py -3.10 -m unittest discover -s tests -t tests -p test_ui_evidence.py -k test_checks_writes_the_solo_or_shared_defaults` |

## Must never break

- Without `guards.ui_evidence`, Ship behaves as in 3.15 (the existing ship tests).
- A profile change toward fewer stops is a trust-anchor notice like any other relaxation.

## Out of scope

- Taking the screenshots in a script: Build takes them with the browser tool the agent has (Playwright MCP), as an instruction.

## Review

- **Fired:** code review, because `## Public Surface` lists `guards.ui_evidence` and `scaffold.py checks`. Security didn't fire. UI review didn't fire: no path in `areas.ui` changed (the tests write `.tsx` files only in temporary repos).
- **Ran:** `sdlc:code-reviewer` on opus, two rounds.
- **Round 1:** FAIL, with one high and four mediums. Fixed test first:
  - H1: the UI globs are the plugin's plus config's, so config can't remove one.
  - M1: any error, or git failing, refuses Ship.
  - M3: `checks shared` never lowers a stricter `approval`.
  - M4: the manual-reason path has a test.

  Also fixed:
  - M2: a workbench's app repos are checked.
  - M5: `profile` was renamed `checks`, since the monorepo already asks a "profile" question.
  - M6: `flow.md`'s screenshot line.
  - L1, L3, L4 and L5.

  L2 was moot.
- **Round 2:** PASS. Its N1 (a workbench test) was added, and F1, F3 and F4 were fixed.
- **Tickets:** N2–N5 are in `.sdlc/todo.md`.
- **Lessons filed:** None
