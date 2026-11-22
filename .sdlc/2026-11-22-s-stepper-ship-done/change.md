# The stepper finishes Ship when CI passes and keeps only the ship this session ran

## Why

Two sdlc-stepper items from `.sdlc/todo.md`:

- "in a workbench with parallel sessions, a feature another session ships stays on this bar at Ship while it is the shown one, and it hides older active features until the next start; mark a feature shipped only when this session ran `ship.py` — UI review UI-M3 of 2026-11-20-s-stepper-ship-stage".
- "after CI passes, the Ship band keeps its last words (`Ship · CI`) and the desktop ring keeps pulsing until the next start or session end; consider showing Ship as done once `gh pr checks` passes — UI review UI-L1".

Proof: with feature a shown at Review and b active in Build, a turns done on disk (another session shipped it) and the bar keeps a at Ship; after `gh pr checks` exits 0, the bar still reads `Ship · CI` with Ship current (the AC tests fail on the old `register.tsx`).

## Decisions

- **`shippedHere`:** the features this session ran `ship.py` for (`shipTarget` reads the name from the command). A shipped feature stays on the bar only if it is the one shown and in that set; otherwise the bar reads the disk without it.
- **CI passed:** at Ship, a `gh pr checks` run on its own (not piped or chained: `| tail` or `|| true` exit 0 on red checks) that succeeds sets the step `CI passed`. Ship stays current, without the pulse on the desktop, and its alt text says `waiting for merge`; only a merge draws every stage done (UI review r1 H1 and M1: four ✓ before the merge read as merged).
- **A failed merge** now reads `Ship · merge failed` at Ship (before, it kept the earlier step's words).
- Existing tests that flip a feature to shipped now make the `ship.py` call the session would have made.

## Acceptance criteria

- **AC-001** At Ship, red checks, and checks piped or chained, leave `Ship · CI` with Ship current and pulsing; green checks run alone read `Ship · CI passed` with Ship current, and the desktop drawing has no animation and the alt `Ship: waiting for merge`. `ship.py <f> --status` marks nothing shipped.
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

### End-of-push review (2026-11-22)

- **UI review r1, FAIL:**
  - **H1:** a piped or chained `gh pr checks` read as CI passed.
  - **M1:** four ✓ before the merge read as merged.
  - **Ms:** a declined merge kept the finished band; a reload drops which feature this session shipped (not in the README).
  - **Ls:** `--status` counted as a ship; the design system was missing the new states.
  
  Fixed test first (AC-001 widened): the bare-command check, Ship current with no pulse while waiting for the merge, `--status` ignored, the reload in the README, the design system updated.
- **Left as noted:** in a workbench, one repo's passing checks set `CI passed` while other PRs may still be pending. `shippedHere` is keyed by the feature name only.
