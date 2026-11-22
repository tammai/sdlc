# Editing the workbench's control files no longer turns its guards off

## Why

From `.sdlc/todo.md`: "Workbench control files the agent can edit: setting `"write": true` or removing an entry in `workbench.json`, or `"workbench": false` in the workbench config, turns the read-only guard, the watch and the app commit review off; guard or watch those files (security-r7 SR7-M3)".

Proof: after the watch's first look, making `specs` writable in `workbench.json` (or dropping it) gives no report, and with `"workbench": false` a change in `specs/` isn't reported either (the AC test fails). Root cause: the guards, the watch and the review gate read both files fresh on every call, and nothing notices a change that unguards a repo.

## Decisions

- **The watch records which repos are read-only** (`read_only` in its baseline, outside the repo). A repo that stops being read-only (`write: true`, or removed from the manifest) is reported, and blocks Stop, until the user sends `accept read-only`; an accept naming other repos keeps it reported. `scaffold.py workbench remove` of a read-only repo therefore asks for one accept.
- **`guarded_workbench` also holds once the watch has seeded the workbench** (`.sdlc/.work/read-only-seeded`, now `sdlc_scopes.SEEDED_MARKER`), so `"workbench": false` doesn't turn off the write guard, the watch (its root lookup uses it now) or the app commit review.
- The marker and baseline themselves are still protected by a text check only: the separate SR7-M1/M2 todo.

## Acceptance criteria

- **AC-001** After the first look, `specs` made writable or removed in `workbench.json` is reported (`no longer read-only`) and blocks Stop; an accept clears it.
- **AC-002** With `"workbench": false` after seeding, `guarded_workbench` is still true and a change in `specs/` is still reported.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_workbench.py › ReadOnlyBackstop.test_the_control_files_cannot_turn_the_watch_off | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_the_control_files_cannot_turn_the_watch_off` |
| AC-002 | tests/test_workbench.py › ReadOnlyBackstop.test_the_control_files_cannot_turn_the_watch_off | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_the_control_files_cannot_turn_the_watch_off` |

## Must never break

- The rest of test_workbench, role_guard and the review gate; outside a seeded workbench nothing changes.

## Out of scope

- The watch's own files' protection (SR7-M1/M2).

## Review

Security review fires (Risk: high); deferred by the user to one review over all of the 2026-11-22 todo fixes at the end of the push.

- **End-of-push review (one pass over all of the 2026-11-22 todo fixes, by area):** scripts and hooks security reviews r1 FAIL, fixed in ddd2c43 and a1552fc; r2 FAIL past the cap, and the user chose to fix the rest (4a0e8f8) and park the read-only guard's lexer as a documented limitation (docs/wiki/Limitations.md). UI review r1 FAIL, fixed in b43026e. What is left is in `.sdlc/todo.md`.
