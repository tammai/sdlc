# A generated lock entry never overwrites or deletes an untracked local file

## Why

From `.sdlc/todo.md`: "A committed lock entry of class `generated` can make an upgrade overwrite, or eject delete, a local file git doesn't track (`.env`, `.claude/settings.local.json`, a key): regenerate and eject act whatever the file's state; render over or delete an untracked existing file only when its hash matches the lock, else review or ask — security review S-2 of 2026-11-22-s-lock-template-trusted, predates it; `scripts/scaffold.py` `cmd_upgrade_plan`, `eject_plan`".

Proof: with a lock entry naming `.env` as generated and a local `.env` git doesn't track, `upgrade-plan` lists it under `regenerate` and `eject` under `delete` (the AC test fails). Root cause: both plans act on `generated` whatever the file's state, and the lock is committed, so anyone can name a local file there.

## Decisions

- **`Project.untracked(path)`** asks git (`ls-files --error-unmatch`); outside a git repo it's False (nothing to tell apart, and no committed lock to distrust).
- A generated entry whose file differs from the lock and isn't tracked goes to `review` in the upgrade and `ask` in eject; tracked, unchanged or missing generated files are handled as before.

## Acceptance criteria

- **AC-001** A generated entry for an untracked, edited `.env` is under `review` (not `regenerate`) in `upgrade-plan` and under `ask` (not `delete`) in `eject`, and `eject --apply` leaves it; a tracked, edited generated file is still regenerated and deleted.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_scaffold.py › ScaffoldTest.test_a_generated_entry_never_overwrites_or_deletes_an_untracked_local_file | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_a_generated_entry_never_overwrites_or_deletes_an_untracked_local_file` |

## Must never break

- Generated files in repos that aren't git repos, and tracked ones: the scaffold and upgrade tests pass.

## Out of scope

- A missing generated file named by the lock is still created on upgrade (no local data at risk).

## Review

Security review fires (Risk: high); deferred by the user to one review over all of the 2026-11-22 todo fixes at the end of the push.

- **End-of-push review (one pass over all of the 2026-11-22 todo fixes, by area):** scripts and hooks security reviews r1 FAIL, fixed in ddd2c43 and a1552fc; r2 FAIL past the cap, and the user chose to fix the rest (4a0e8f8) and park the read-only guard's lexer as a documented limitation (docs/wiki/Limitations.md). UI review r1 FAIL, fixed in b43026e. What is left is in `.sdlc/todo.md`.
