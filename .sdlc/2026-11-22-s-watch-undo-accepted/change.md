# The read-only watch takes a return to the first look silently after an accept

## Why

From `.sdlc/todo.md`: "Undoing a read-only change the user already accepted counts as a new change (the accepted baseline holds the change); consider accepting a return to the first look silently — 3.8.0 smoke test K".

Proof: in a workbench, sdlc first sees `specs/` clean, a change to `specs/b.md` is reported, the user sends `accept read-only`, then `specs/b.md` is removed: the watch reports `undone or committed: b.md` and blocks Stop (the AC test fails).

## Decisions

- The baseline keeps each repo's **first look** (`first`) beside the accepted one; an accept never replaces it, and a repo cloned later gets its own.
- When a repo differs from the accepted baseline but not from its first look, the watch takes the repo as the baseline again, silently. Any other difference is reported as before.
- A baseline written before this change has no `first`: nothing is taken silently there (the old behaviour).

## Acceptance criteria

- **AC-001** After an accept, undoing the accepted change back to the first look gives no report and no Stop block; a new change after that is still reported.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_workbench.py › ReadOnlyBackstop.test_undoing_an_accepted_change_back_to_the_first_look_is_silent | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_undoing_an_accepted_change_back_to_the_first_look_is_silent` |

## Must never break

- The rest of ReadOnlyBackstop: a change is said once and blocks Stop, an accept clears it, a missing marker or baseline is a standing difference.

## Out of scope

- The watch's own protections (the text check on its files): a separate todo.

## Review

No review ran: no trigger fired (risk low); everything goes into the end-of-push review.

- **End-of-push review (one pass over all of the 2026-11-22 todo fixes, by area):** scripts and hooks security reviews r1 FAIL, fixed in ddd2c43 and a1552fc; r2 FAIL past the cap, and the user chose to fix the rest (4a0e8f8) and park the read-only guard's lexer as a documented limitation (docs/wiki/Limitations.md). UI review r1 FAIL, fixed in b43026e. What is left is in `.sdlc/todo.md`.
