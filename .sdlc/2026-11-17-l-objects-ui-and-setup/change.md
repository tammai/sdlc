# The domain model's UI layer and setup step (spec 13, parts B3 and B4)

## Why

**Request (verbatim):** "Build parts B3 and B4 of the domain model, spec 13 (docs/specs/13-domain-model.md, signed off 2026-11-17; the measurement passed and the owner chose to build them). B3, the UI layer: ui-work.md's `## UI mapping` names, for each object on a changed screen, its `Shown as` component and the actions offered; ui-reviewer reads objects.md (an object shown with a component other than its Shown as, or an action its Actions line lacks, is medium); the impeccable note (D7: when impeccable's PRODUCT.md already lists objects, objects.md links to it for the UI fields); rebuild hosts/ with scripts/hosts.py. B4: `/sdlc:setup objects`, a setup step that drafts objects.md (greenfield from the PRD, brownfield from schema, types, enums and routes), written only with per-batch approval as knowledge is, refusing in a spec-backed repo. Follow the user's testing rule: about 10 ACs or fewer, one test per user-visible behaviour."

The spec is `docs/specs/13-domain-model.md` (§Where it enters the flow, §Known gaps, D7). Its measurement (run 1, 2026-11-17) passed all four bars, and the owner chose to build B3 and B4. Until now a repo turned the model on by hand from the template; this gives it a setup step, and gives UI work and its review the object layer.

**The user's words:** "Merge PR #85, then build B3/B4" (2026-11-17), after the measurement.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| `/sdlc:setup objects` runs alone, like `/sdlc:setup deploy`, never inside a normal setup | a step every setup asks | the model is opt-in and off by default (spec 13 Constraints); a step in every setup adds a question to every repo |
| `scaffold.py objects` reports the file, the switch and what to draft from; `--enable` turns the switch on only when the file exists and `objects.py check` has no error | the agent editing `.sdlc/config.json` by hand | config goes through scaffold.py like `deploy` and `design`; switching on with a broken file would fail the next Define gate |
| Brownfield inputs are tracked files matching schema, model, type, enum and route patterns, at most 40, listed by `scaffold.py objects`; the agent reads them | parsing schemas in a script | the agent drafts the file anyway; a script that only lists candidates stays small and language-agnostic |
| D7, read against impeccable 4.9.2's `reference/init.md`: PRODUCT.md holds users, purpose and terminology, and leaves components out, so it never lists objects with their components. objects.md keeps its UI fields; the setup reads PRODUCT.md's terminology as an input, and in impeccable mode the `/impeccable shape` request names the objects and their UI names | linking objects.md to PRODUCT.md for the UI fields | the condition D7 set ("when PRODUCT.md already lists objects") doesn't hold for that version |
| Eject keeps `<docs>/objects.md` (user-owned, like the design system) | deleting it | it's the user's document; eject keeps the PRD, constitution and design system the same way |
| The setup's detail lives in a new `skills/setting-up-projects/references/objects.md`; `SKILL.md` gets one sentence | the step in `SKILL.md` | `SKILL.md` is at 19,030 of its 20,000-character limit |

**Proposals not asked for:** None.

## Acceptance criteria

- **AC-001** spec §B4: Given a set-up repo with a valid `<docs>/objects.md`, when `scaffold.py objects --enable` runs, then `.sdlc/config.json` gains `"objects": true` with its other keys kept, and `scaffold.py objects` then reports the path, `exists: true` and `on: true`.
- **AC-002** spec §B4, D5: Given a repo not set up, a spec-backed repo (a tracked `criteria.lock.json`), a missing objects file, or one `objects.py check` fails, when `scaffold.py objects --enable` runs, then it is refused with a message naming why (rspec's `domain.md` for the spec-backed repo, the check's problems for a broken file), and the config is unchanged.
- **AC-003** spec §B4: Given a repo, when `scaffold.py objects` runs, then its `inputs` name the PRD (when one exists) and the tracked files that look like schema, models, types, enums or routes (`*.prisma`, `*.sql`, `schema.*`, `models/`, `types.ts`, `*.d.ts`, `enums`, `routes/`, `api/`), at most 40, and no other files.
- **AC-004** spec §The file (project-owned): Given a set-up repo with `<docs>/objects.md`, when `scaffold.py eject` plans, then the file is under `keep`, never `delete`.
- **AC-005** spec §B4 (setup): `/sdlc:setup objects` drafts the file on branch `sdlc/objects` from the PRD (greenfield) or the inputs `scaffold.py objects` lists (brownfield) and PRODUCT.md's terminology when it exists, shows the objects in batches, writes only what the user approves, runs `objects.py check`, then `scaffold.py objects --enable`, one commit, and merges locally; it refuses in a spec-backed repo.
- **AC-006** spec §B3 (Build, UI): `ui-work.md` makes `## UI mapping` name, for each object on a changed screen, its `Shown as` component and the actions offered, when the objects file is on; in impeccable mode the `/impeccable shape` request names the objects and their UI names.
- **AC-007** spec §B3 (Review, UI): `ui-reviewer` reads the objects file when it is on; an object shown with a component other than its `Shown as`, or offering an action its `Actions` line lacks, is a Medium finding.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_objects_setup.py › ObjectsSetupTest.test_enable_turns_the_switch_on_and_keeps_the_config | `py -3.10 -m unittest discover -s tests -t tests -p test_objects_setup.py -k test_enable_turns_the_switch_on_and_keeps_the_config` |
| AC-002 | tests/test_objects_setup.py › ObjectsSetupTest.test_enable_is_refused_and_changes_nothing | `py -3.10 -m unittest discover -s tests -t tests -p test_objects_setup.py -k test_enable_is_refused_and_changes_nothing` |
| AC-003 | tests/test_objects_setup.py › ObjectsSetupTest.test_inputs_name_the_prd_and_schema_like_files_only | `py -3.10 -m unittest discover -s tests -t tests -p test_objects_setup.py -k test_inputs_name_the_prd_and_schema_like_files_only` |
| AC-004 | tests/test_objects_setup.py › ObjectsSetupTest.test_eject_keeps_the_objects_file | `py -3.10 -m unittest discover -s tests -t tests -p test_objects_setup.py -k test_eject_keeps_the_objects_file` |
| AC-005 | manual | instructions to the agent in `commands/setup.md`, `skills/setting-up-projects/SKILL.md` and the new `references/objects.md`; no document-grepping tests (user's testing rule). Checked by review, and by a headless `/sdlc:setup objects` run in a throwaway repo |
| AC-006 | manual | instructions in `skills/orchestrator/references/ui-work.md`; checked by review against spec 13 |
| AC-007 | manual | instructions in `agents/ui-reviewer.md` (and its host copies); checked by review against spec 13 |

## Must never break

- With no `objects` key, setup, upgrade, eject, Define and the UI review behave as before: no new question, no new step, no new finding.
- Setup never writes `objects.md` or turns the switch on without the user's approval, and never in a spec-backed repo.
- `scaffold.py objects` without `--enable` writes nothing.

## Failure modes

- Untrusted input: `.sdlc/config.json` is repo config; `scaffold.py objects` reads the file only through `objects.path()` (spec 13 O2a), so a bad value is reported, never followed → AC-002.
- Loaded data: a config that isn't a JSON object, or a lock that's missing, gives a refusal naming it, never a traceback → AC-002.
- Scale: a repo with many matching files lists at most 40 → AC-003.

## Out of scope

- Generating `objects.md` by script, or code from it (spec 13 §Out of scope).
- Asking about the model during a normal `/sdlc:setup` or `/sdlc:upgrade`.
- Any change to rspec's `domain.md` or impeccable's PRODUCT.md (sdlc never writes either).

## Review

- **Recommended and chosen:** code (L; Public Surface not none) and security (the repo config value `objects` reaches a file path through `scaffold.py objects`); chosen by the trigger list (L, self-chosen, `state.py log`). AC-005 also checked in a real headless `/sdlc:setup objects` session.
- **Verdicts:** code `code-reviewer-r1.md` FAIL — F1, F2, F3, F4, F6, F10 → `code-reviewer-r2.md` FAIL — R2-1, R2-2 → (user, review cap: one more fix round) `code-reviewer-r3.md` PASS; security `security-r1.md` FAIL — SEC-1, SEC-2 → `security-r2.md` PASS. All in `.sdlc/.work/findings/2026-11-17-l-objects-ui-and-setup/`.
- **Fixed:**
  - SEC-1, F1, F6, F8, F13 (one class: the objects path used without `objects.path()`'s rule while the switch is off): `objects.target()` judges any value by that rule, switch on or off; `scaffold.py objects` reports a refused value as `invalid` and never reads it, `on` only when valid; `--enable` refuses before reading. Tests: `tests/test_objects_setup_review.py` › `test_the_off_switch_path_follows_the_same_rule`, `test_an_invalid_value_is_reported_and_a_plain_run_writes_nothing`, `test_the_old_layouts_place_is_never_reached_through_a_link`.
  - R2-1 (added by the F8 fix: reviewers told to run a script their read-only rule forbids): the orchestrator names the objects file in each review prompt from the brief's section (rerunning `brief.py` when it isn't in context, R3-1), and review-brief, ui-reviewer and Learn read only that. Instructions, checked by code-review round 3.
  - R2-2: only a missing key or `false` is off; `0`, `1`, `"yes"` are reported invalid (same test).
  - SEC-2, F3, F4, F5, SEC-4, R2-3, R2-4, R3-3, R3-4 (one class: drafting inputs): listed from `git ls-files -s -z`, without links, odd names, real paths outside the repo, tests, docs, vendored or generated files, seeds or dumps; ranked schema, models, types and enums, routes, migrations; `more` counts the cut; `PRODUCT.md` and the PRD only as regular files inside the repo (`test_inputs_never_follow_a_link_or_misread_a_name`, `test_inputs_keep_the_schema_and_say_what_was_cut`).
  - F9: `--enable` refuses an unfinished setup (`test_setup_still_in_progress_is_refused`); the reference stops in a workbench app repo.
  - F2, F7, F12, F14: the setup reference starts from an existing objects file and never replaces it, shows any fix to an approved object first, removes its branch when nothing is approved, asks about a dirty tree, and comes back after Setup. Instructions, checked by review and the headless run.
- **Tickets:** SEC-3, config's `prd` is checked by spelling only, and brief.py prints it at every Define (pre-existing; `inputs.prd` here is now limited to a regular file in the repo). On M in Claude Code the built-in `code-review` skill doesn't read review-brief.md, so spec 13's DR-rule check (O9) doesn't run there (since spec 13 merged). F5's single-file names beyond the ones listed (Rails `routes.rb` is covered, `urls.py` too; more can come when a repo shows a miss). Security R2-2, the realpath of every tracked file on large repos (unconfirmed).
- **Drift and manual checks:** Deviations: the repo isn't set up for sdlc (full suite run by hand: 663 tests OK, Python 3.10); `objects.check_file()`; the scaffold helpers; `tests/test_deploy_targets.py`'s argument-hint regex; the round-1 to round-3 fixes. AC-005: a headless `/sdlc:setup objects` in a copy of the invoicing repo branched `sdlc/objects`, showed a batch and wrote nothing until it was approved, wrote an `objects.md` that passes the check, turned `"objects": true` on with the other keys kept, one commit, merged locally (before round 1's fixes; the reference's flow didn't change in substance after). AC-006, AC-007: ui-work.md and ui-reviewer read against spec 13 O15 by three code-review rounds.
- **Security:** SEC-1 and SEC-2 closed in round 2; no dependency added; the security hooks raised nothing.
- **Lessons filed:** `.sdlc/recurring-defects.md` (a reviewer told to run what its read-only rule forbids).
