# A file protected only by a Windows ACL is refused too; the lock and config merges share one helper

## Why

**Request:** the user's goal, "get job done unattend": the items PR #61 left open.
- LM3-08: the read-only check uses `os.access`, which on Windows sees only the read-only attribute. A file whose ACL denies writing passes the check, and the atomic replace then swaps it out.
- CC2-12: the config merge in `save` repeats `merged_lock` almost line for line.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| The check opens the file for writing without truncating it (`r+b`) and closes it again. Whatever the OS refuses, the read-only attribute or an ACL, is refused before any write | `os.access` (blind to ACLs on Windows); calling the Windows security API | the standard library only; the open asks the OS itself |
| One `Project` helper re-reads a file at save, refuses one that was removed or broken meanwhile, and merges this command's changes onto it; the lock and config both use it | two copies | review finding CC2-12 |
| The config re-read stays before either file is written | moving it next to the config's write (CC2-06) | a refusal must leave both files as they were (CC-04/05); this is a trade-off, recorded here |

## Acceptance criteria

- **AC-001** Given a `config.json` whose Windows ACL denies writing (no read-only attribute), when a command that changed the lock and the config saves, then it is refused and neither file changes.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_stack_blueprints.py › ConfigAndContainment.test_acl_protected_config_is_refused | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_acl_protected_config_is_refused` |

## Must never break

- Every existing save, merge and refusal behaves as before (the full suite).
- The plugin stays Python stdlib only.

## Out of scope

- Moving the config re-read later in `save` (Decisions).

## Review

No review ran: no trigger fired (S, low risk, no public surface).
