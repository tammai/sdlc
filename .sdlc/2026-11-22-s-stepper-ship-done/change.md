# The stepper finishes Ship when CI passes and keeps only the ship this session ran

## Why

Two sdlc-stepper items from `.sdlc/todo.md`:

- "in a workbench with parallel sessions, a feature another session ships stays on this bar at Ship while it is the shown one, and it hides older active features until the next start; mark a feature shipped only when this session ran `ship.py` — UI review UI-M3 of 2026-11-20-s-stepper-ship-stage".
- "after CI passes, the Ship band keeps its last words (`Ship · CI`) and the desktop ring keeps pulsing until the next start or session end; consider showing Ship as done once `gh pr checks` passes — UI review UI-L1".

Proof: with feature a shown at Review and b active in Build, a turns done on disk (another session shipped it) and the bar keeps a at Ship; after `gh pr checks` exits 0, the bar still reads `Ship · CI` with Ship current (the AC tests fail on the old `register.tsx`).

## Decisions

- **`shippedHere`:** the features this session ran `ship.py` for (`shipTarget` reads the name from the command). A shipped feature stays on the bar only if it is the one shown and in that set; otherwise the bar reads the disk without it.
- **CI passed:** at Ship, `gh pr checks` that succeeds sets the step `CI passed`, and the band draws every stage done (on the desktop nothing pulses). It still clears only after a merge (`done`), not on the next prompt: the merge is the user's call.
- **A failed merge** now reads `Ship · merge failed` at Ship (before, it kept the earlier step's words).
- Existing tests that flip a feature to shipped now make the `ship.py` call the session would have made.

## Acceptance criteria

- **AC-001** At Ship, red checks leave `Ship · CI` with Ship current; green checks show four ✓ and `Ship · CI passed`, and the desktop drawing has every stage done and no animation.
- **AC-002** A feature that turns done without this session running `ship.py` gives way to the older active feature.
- **AC-003** A merge that fails reads `Ship · merge failed` with Ship current.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | plugins/sdlc-stepper/tests/stepper.test.tsx › checks that pass at Ship finish it on the bar; checks that fail leave Ship current | `cd plugins/sdlc-stepper && claude plugin test .` |
| AC-002 | plugins/sdlc-stepper/tests/stepper.test.tsx › a feature another session ships gives way to the older active one here | `cd plugins/sdlc-stepper && claude plugin test .` |
| AC-003 | plugins/sdlc-stepper/tests/stepper.test.tsx › a merge that failed leaves the feature at Ship | `cd plugins/sdlc-stepper && claude plugin test .` |

## Must never break

- The rest of the stepper suite; `.sdlc/design-system.md` (marks, the one pulse, theme keys).

## Out of scope

- A PR merged outside the session is still not seen.

## Review

UI review applies (the stepper band); deferred by the user to one review over all of the 2026-11-22 todo fixes at the end of the push.
