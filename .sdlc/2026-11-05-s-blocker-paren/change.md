# state.py blocker raise silently drops an open question that starts with (

## Why

`state.py blocker <feature> raise "<text>"` loses an open question whose text starts with `(`: the next append to `## Open questions` deletes it without a word, and `section_items()` never lists it (so the snapshot's `open_questions` misses it). Both commands report `"ok": true`.

Request (verbatim summary): "Both open questions stay in the section, in order, and `state.py blocker … resolve "(owner) needs the API key"` removes exactly that one."

Proof: `raise "(owner) needs the API key"` then `raise "second blocker"` leaves only `- second blocker` under `## Open questions` (AC-001 fails the same way).

Root cause: `append_to_section()` strips the template's placeholder by dropping every body line starting with `- (`, and `section_items()` skips every item starting with `(`. Real items starting with `(` match too; blockers carry no date prefix, so they hit it.

## Decisions

- Match only the template's own placeholder, `- (oldest first …)` (the only `- (` line `state.py new` and `flow.md` write), in both functions, via one shared check.
- Ruled out: date-prefixing blockers (changes the stored format and what `resolve` matches).

## Acceptance criteria

- AC-001: a blocker starting with `(` stays in `## Open questions` after another is raised, in order, appears in `open_questions`, and `resolve` with its text removes exactly it; the `- (oldest first …)` placeholder is still dropped on the first append.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_state.py › test_a_blocker_starting_with_a_parenthesis_is_kept_listed_and_resolvable | `python3 -m unittest discover -s tests -t tests -p test_state.py -k test_a_blocker_starting_with_a_parenthesis_is_kept_listed_and_resolvable` |

## Must never break

- The template placeholders (`- (oldest first …)`, `-`, `- <date> Stage n: …`, `- Round 1 — <commit> …`) are still removed on the first append and never listed as items.

## Out of scope

- Other sections' formats; date-prefixing blockers.

## Review

No review ran: no trigger fired.
