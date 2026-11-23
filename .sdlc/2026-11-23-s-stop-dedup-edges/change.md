# Stop review dedup: a repeated snippet and an interrupted turn

## Why

**Request (verbatim):** two open tickets from `.sdlc/todo.md`:
- "Stop review dedup: a finding has no location, so the same snippet at a second place in one file is dropped on a rewake when the model reports the other occurrence later (or the cap cut the file on the first fire); consider a line number in the key or no drop for a truncated file"
- "Stop review dedup: after an interrupted turn the next prompt keeps the old `prompt_at` (UserPromptSubmit returns before setting it when the baseline is kept), so code reverted and re-added across the interrupt can be dropped; use a marker written on every prompt"

**Proof:** both new tests in `tests/test_workbench.py` fail before the fix: the second Stop exits 0 with `skip_reason` 36 (dropped as already reported).

**Root cause:**
- The drop's key, (file, category, vulnerable code, file diff, turn), can't tell two places with the same snippet apart.
- The turn is `prompt_at`, which UserPromptSubmit doesn't set when it keeps an interrupted turn's baseline.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| No drop when the finding's snippet appears more than once in that file's diff, or when the review's diff was truncated | a line number in the key | the model's finding carries no reliable line; ambiguity re-raises, which only costs a rewake |
| A `turn_at` marker set on every prompt, the drop keyed on it | changing `prompt_at` | `prompt_at` also dates the other repos' diffs, which must reach back to the kept baseline |

## Acceptance criteria

- **AC-001** A finding whose snippet appears twice in the file's diff is raised again on a rewake.
- **AC-002** After an interrupted turn, a finding on code reverted and re-added is raised again in the next turn.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_workbench.py › StopReviewEveryRepo.test_the_same_snippet_at_another_place_in_the_file_is_raised | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_the_same_snippet_at_another_place_in_the_file_is_raised` |
| AC-002 | tests/test_workbench.py › StopReviewEveryRepo.test_a_finding_after_an_interrupted_turn_is_raised_again | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_a_finding_after_an_interrupted_turn_is_raised_again` |

## Must never break

- A declined finding on unchanged code (one occurrence) is still dropped on a rewake in the same turn.
- The other repos' diffs still reach back to the kept baseline after an interrupt.

## Out of scope

- A location in the review's finding format.

## Review

No review ran: no trigger fired.
