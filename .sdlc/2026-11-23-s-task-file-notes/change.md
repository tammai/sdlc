# A note after a task's file stays with it

## Why

**Request (verbatim):** "Fix all 6, then release" — the todo: "`state.py new --task` splits a file note like `src/x.test.ts (test)` into a stray `(test)` file — 3.15.0 smoke test P5".

**Proof:** `tests/test_state.py` › `test_a_note_after_a_task_file_stays_with_it` fails: the Files line reads `` `src/x.test.ts`, `(test)` ``.

**Root cause:** `task_lines` splits the files part on commas and whitespace, so every word becomes a file.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| A whole token that starts with `(` opens a note, kept through the token ending with `)`, beside the file before it and outside its backticks | splitting on commas only; dropping notes | space-separated files keep working, and `app/(group)/page.tsx` stays one file |

## Acceptance criteria

- **AC-001** `--task "Fix | AC-001 | src/x.ts, src/x.test.ts (test)"` writes `` - Files: `src/x.ts`, `src/x.test.ts` (test) ``.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_state.py › StateTest.test_a_note_after_a_task_file_stays_with_it | `python3 -m unittest discover -s tests -t tests -p test_state.py -k test_a_note_after_a_task_file_stays_with_it` |

## Must never break

- Comma- and space-separated file lists, as in `test_new_writes_the_state_file_from_defines_answers`.

## Out of scope

- Paths with spaces.

## Review

No review ran: no trigger fired.
