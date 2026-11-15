# A failed lock write leaves this command's copy as it was before the merge

## Why

**Request:** the user's goal, "get job done unattend": LM3-04, the last open item from
`.sdlc/2026-11-15-m-lock-merge-and-tickets/change.md` ## Review.

`save` merges another command's changes into this command's lock, then writes it. When the write fails, those merged
changes stay in this command's copy while its merge base doesn't move, so a later save sees a difference this command
never made and writes the lock again, even after this command undid its own change.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| When the write fails, the merge is undone in place: the copy goes back to its pre-merge state, in the same objects this command holds | leaving it (latent) | a later save must see only this command's own changes |
| The `Project` lock fields (LM-14/LM3-11) stay as they are | folding them together | a cleanup with no behaviour change, in code that just went through three review rounds; ADR 0027 records the design |

## Acceptance criteria

- **AC-001** Given a lock save whose write fails after merging another command's change, when this command then undoes its own change and saves again, then nothing is written.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_stack_blueprints.py › LastTickets.test_failed_write_undoes_the_merge | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_failed_write_undoes_the_merge` |

## Must never break

- A save that succeeds merges and writes as before.
- The plugin stays Python stdlib only.

## Out of scope

- The `Project` field cleanup (Decisions).

## Review

No review ran: no trigger fired (S, low risk, no public surface).
