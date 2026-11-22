# The read-only watch finds a seeded workbench without CLAUDE_PROJECT_DIR

## Why

A gap in 2026-11-22-s-workbench-control-files (d7f4979), found while checking it before the end-of-push review. It made `guarded_workbench` hold once the watch has seeded the workbench. But the watch's own root lookup, for a host without `CLAUDE_PROJECT_DIR` (Codex), still walked up with `workbench_root(cwd)`, which asks `is_workbench`.

Proof: with `"workbench": false` after seeding and no `CLAUDE_PROJECT_DIR`, the watch called from `api/` at Stop finds no workbench and stays silent while `specs/` has a change. AC-001's test fails on d7f4979. The change file of d7f4979 also claimed the write guard and the app review survive the flag, which its test didn't check: AC-001 checks them now.

## Decisions

- The watch looks up its root with `workbench_root(cwd, guarded=True)`, as `pretooluse.py` already does.
- The workbench docs say how a user really stops using a workbench: delete `.sdlc/.work/read-only-seeded` in their own terminal.

## Acceptance criteria

- **AC-001** With `"workbench": false` after seeding: a Write into `specs/` is denied, `api` is still a member for the app review, and the watch blocks Stop when called from `api/` with no `CLAUDE_PROJECT_DIR`.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_workbench.py › ReadOnlyBackstop.test_the_control_files_cannot_turn_the_watch_off | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_the_control_files_cannot_turn_the_watch_off` |

## Must never break

- The rest of ReadOnlyBackstop.

## Out of scope

- None.

## Review

Security review fires (Risk: high); deferred by the user to one review over all of the 2026-11-22 todo fixes at the end of the push.

- **End-of-push review (one pass over all of the 2026-11-22 todo fixes, by area):** scripts and hooks security reviews r1 FAIL, fixed in ddd2c43 and a1552fc; r2 FAIL past the cap, and the user chose to fix the rest (4a0e8f8) and park the read-only guard's lexer as a documented limitation (docs/wiki/Limitations.md). UI review r1 FAIL, fixed in b43026e. What is left is in `.sdlc/todo.md`.
