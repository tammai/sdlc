# The stepper shows Ship while the session ships

## Why

The request, verbatim: "stepper dont show ship stage".

The sdlc-stepper bar never shows the Ship stage. When Ship starts, `scripts/ship.py` advances the state file to Stage 4 and sets `Status: done` in the same run (`ship.py:270-272`), so the commit carries the finished record. The stepper reads only features with `Status: active` (`plugins/sdlc-stepper/hooks/sdlc.ts`, `parseState`). So a feature is never active at Ship, and the bar disappears just as the session commits, pushes, opens the PR and watches CI.

Proof: the test `the feature this session ships stays on the bar at Ship, though Ship marks it done` gets no marks at all (`[]`) after `ship.py` marks the feature done.

## Decisions

- The stepper keeps a done feature at Ship on the bar while it is the feature the bar was already showing (the persisted view atom), so the session that ships it sees Ship through the PR and CI. A feature shipped before the session started is still not shown, since the bar never showed it.
- A shipped view gives way only to `/sdlc:start` or a `Define · …` line (`dropShipped`). The bar then reads the disk again without the shipped feature: it shows an older active feature if there is one, else the Define draft. A `Build · …` line while fixing CI is still part of Ship and keeps the band.
- `session.end` clears a shipped view, because `/clear` keeps the process going and fires no `session.start`.
- Ruled out: leaving `Status: active` until after the PR in `ship.py`. The commit has to carry the finished record (S track step 6), and the change would move state for every host.
- Ruled out: a clock window (show a done feature for N minutes). It's flaky, and a pure function can't test it.

## Acceptance criteria

- AC-001: in a session where the bar shows a feature, after `ship.py` sets it to Stage 4 with `Status: done`, the bar shows it at Ship (Define, Build and Review done; Ship current) along with its name and the Ship step (`Ship · PR` after `gh pr create`).

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | plugins/sdlc-stepper/tests/stepper.test.tsx › the feature this session ships stays on the bar at Ship, though Ship marks it done | `claude plugin test plugins/sdlc-stepper` |

## Must never break

- A feature shipped before this session isn't shown (`a feature shipped before this session is not shown`).
- After a ship, `/sdlc:start` shows Define for the next feature, not the shipped one (`starting the next feature after a ship shows Define, not the shipped one`).
- The agent's `Ship · …` lines, and a `Build · …` line for a CI fix, keep the shipped feature on the bar (`the agent's update lines during Ship keep the shipped feature on the bar, a Build line for a CI fix too`).
- The next feature's Define line replaces the shipped one (`the next feature's first Define line replaces the shipped one`), and resuming an older active feature shows that feature (`resuming an older active feature after a ship shows that feature, not a Define band`).
- After `/clear` the shipped feature isn't carried over (`after /clear the shipped feature is not carried into the new conversation`).
- A feature marked done before Ship (at Build) leaves no band (`a feature still being defined shows from the agent's own lines, then hands over to its state file`).
- The bar only reads files, and a failure in it never holds a prompt or a tool call.

## Review

- Fired: UI (`register.tsx` and the test file match `areas.ui`). No security trigger, and no code review (Public Surface: none).
- Round 1, ui-reviewer: FAIL.
  - Fixed test-first: UI-M1, a shipped feature hiding an older active one and leaving a wrong Define band (`dropShipped`); UI-M2, an untested Define-line hand-over; UI-M4, the Ship band surviving `/clear` (a `session.end` hook).
  - UI-M3 (parallel sessions in a workbench): the doc comment was fixed and the rest ticketed. UI-L1 ticketed; UI-L2 got a README line.
  - UI-L3–L5 (small test gaps rated 5 or below): dropped.
  - UI-H1 (the repo has no `.sdlc/design-system.md`): a repo-level gap this diff can't close. The reviewer and I agreed to waive it for this change, and it's ticketed in `.sdlc/todo.md`.
- Round 2, ui-reviewer (closing check): PASS. Every round 1 bug is gone. It found a missing test for the line that keeps the band up during `Ship · …` lines (UI-R2-M1) and a low, a `Build · …` line during a CI fix dropping the band (UI-R2-L1). Both were fixed test-first: only a Define line drops a shipped view now.
- Lessons: none worth filing.

## Out of scope

- How long the Ship band stays after CI finishes: it stays until the session ends or the next feature starts.
- Any change to `ship.py` or the state file's format.
