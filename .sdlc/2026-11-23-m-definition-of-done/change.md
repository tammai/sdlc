# A project's Definition of Done, asked in setup and checked at Ship

## Why

**Request (verbatim):** from `.sdlc/todo.md`: "Add a Definition of Done to the setup step so the agent knows when a job is done — not built yet (2026-10-25)". The user chose it next (2026-11-23).

Today "done" is fixed by the plugin: tests green, reviews passed, the record complete. A team's own bar isn't recorded anywhere the agent reads at the right moment, so each change relies on the agent remembering it. Examples: a changelog line, docs updated, a migration note, screenshots for UI. After this, setup asks for the team's list, every change carries it as a checklist, and Ship won't proceed until each item is ticked with its evidence.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| `done` in `.sdlc/config.json`: 1 to 10 one-line items, each up to 200 characters, set by `scaffold.py done …` (setup's `done` step, `/sdlc:setup done`); `--clear` removes it | a constitution section | the constitution is prose; a list can be checked item by item |
| The brief prints it; Define copies it into the change file as `## Definition of Done`; before Ship each line reads `- [x] <item> — <evidence>` (or `n/a: <reason>`) | ticking without evidence | a tick with no evidence is the failure the list exists to prevent |
| `ship.py` refuses (`definition_of_done_open`, before anything moves) when an item is missing, unticked or without evidence; items match case- and whitespace-insensitively | a review-only check | Ship is the one command every change runs |
| The trust anchor treats `done` like the commands: a change from Base is a notice | no watch | removing an item relaxes the bar, and the config is the agent's to edit |
| No list: everything as today | a default list | the team's bar is theirs; the plugin's own bar already runs |
| Code review r1: an item may not hold ` — `; matching is by item prefix; items present at the feature's Base can't be dropped before Ship; an invalid list fails closed (Ship refuses, the brief says so); `n/a` needs a reason and the `<evidence>` placeholder doesn't count; any ticked line for an item counts; the check runs before `## Review` is written; the section is left out of the trust anchor's change-file digest (it is ticked at Ship) | the first build's live-config, first-split check | DOD1–DOD9 |
| Code review r2: Ship holds the live list plus the list the user last accepted (the trust anchor's `commands_ok`, else Base's), so the user's accepted edit counts and an item they added can't be dropped unseen; one heading rule (`sdlc_scopes.DONE_HEADING`); `<…>` placeholders refused; a malformed config fails closed; `[]` means none; `done` needs a set-up repo and the folder Ship reads | Base only | R2-1–R2-11 |

## Acceptance criteria

- **AC-001** `scaffold.py done <items…>` records the list; an empty item, one over 200 characters, one with a line break, or more than 10 items is refused (exit 2); `--clear` removes it; no items prints it.
- **AC-002** The brief prints the Definition of Done when config has one.
- **AC-003** `ship.py` refuses, with nothing moved, while an item is missing from `## Definition of Done`, unticked or ticked without evidence, and proceeds when each is ticked with evidence or `n/a: <reason>`.
- **AC-004** Changing `done` from its value at Base raises a trust-anchor notice.
- **AC-005** `flow.md`, `s-track.md`, the change template and the setup skill name the Definition of Done, and setup's reference gives the `done` command.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_definition_of_done.py › DefinitionOfDoneTest.test_the_list_is_set_through_scaffold_within_its_limits | `python3.10 -m unittest discover -s tests -t tests -p test_definition_of_done.py -k test_the_list_is_set_through_scaffold_within_its_limits` |
| AC-002 | tests/test_definition_of_done.py › DefinitionOfDoneTest.test_the_brief_prints_the_list | `python3.10 -m unittest discover -s tests -t tests -p test_definition_of_done.py -k test_the_brief_prints_the_list` |
| AC-003 | tests/test_definition_of_done.py › DefinitionOfDoneTest.test_ship_refuses_until_every_item_is_ticked_with_evidence | `python3.10 -m unittest discover -s tests -t tests -p test_definition_of_done.py -k test_ship_refuses_until_every_item_is_ticked_with_evidence` |
| AC-004 | tests/test_definition_of_done.py › DefinitionOfDoneTest.test_a_changed_list_is_a_trust_anchor_notice | `python3.10 -m unittest discover -s tests -t tests -p test_definition_of_done.py -k test_a_changed_list_is_a_trust_anchor_notice` |
| AC-005 | tests/test_definition_of_done.py › DefinitionOfDoneTest.test_the_flow_and_setup_text_name_it | `python3.10 -m unittest discover -s tests -t tests -p test_definition_of_done.py -k test_the_flow_and_setup_text_name_it` |

## Must never break

- A repo with no `done` ships exactly as before (`test_no_list_ships_as_before`).
- A refusal leaves the state file as it was.

## Review

- **What fired:** a code review, because Public Surface isn't none (the `done` command and config key). Risk is low, so it wasn't asked. It ran as the built-in `code-review high --max-findings all`, and I rated each finding.
- **Round 1, FAIL.**
  - Medium bugs, all fixed test first:
    - DOD1: an item with ` — ` could never be met.
    - DOD2: ticking the checklist set off a trust-anchor notice.
    - DOD3: an item could be dropped before Ship.
    - DOD4: an invalid list silently turned the check off.
    - DOD5: `/sdlc:setup done` wasn't routed.
    - DOD6: a setup guard sentence had been trimmed.
  - Lows DOD7 to DOD13: fixed, including the docs.
- **Round 2, PASS** (no high). Its bugs were fixed test first and closed by verify:
  - R2-1 and R2-2: the bar is now the live list plus the list last accepted.
  - R2-3: placeholder evidence is refused.
  - R2-4 to R2-11: one heading rule, line breaks, a malformed config, routing, the lock and folder checks, and the empty list.
- **Reports:** `.sdlc/.work/findings/2026-11-23-m-definition-of-done/code-reviewer-r1.md` and `-r2.md`.
- **Tests:** every AC red then green, re-red at Base after each test change. Full suite 842 OK on Python 3.10.
- **Lessons filed:** none.
