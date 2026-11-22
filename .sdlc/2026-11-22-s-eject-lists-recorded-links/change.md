# Eject names a linked fixed file only when it has something to unmerge

## Why

From `.sdlc/todo.md`: "Eject lists every linked fixed file (AGENTS.md, .gitignore, the settings files) under `outside`, even one sdlc never merged into, and eject.md tells the user to unmerge by hand; list only files with something recorded, or reword — security review R2-L2 of 2026-11-22-s-fixed-writers-refuse-links".

Proof: in a Claude-Code-only repo (no AGENTS.md block recorded), an AGENTS.md linked outside the repo is listed under `outside` by `eject` and `eject --apply` (the AC test fails), so the user is told to unmerge a file sdlc never wrote. Root cause: `eject_plan` lists every linked name in `FIXED_FILES` without looking at the lock's `merged`.

## Decisions

- **`UNMERGE_KEYS`** maps each fixed file to its lock `merged` keys (AGENTS.md → its block, `.gitignore`, settings.json → allow list and team plugin keys, settings.local.json → plugin keys); a linked file is listed only when one of them holds something.
- eject.md's wording stays: what's listed now always has something to unmerge.

## Acceptance criteria

- **AC-001** A linked AGENTS.md with no block recorded isn't listed under `outside` by `eject` or `eject --apply`, and stays unchanged; a linked `.gitignore` with recorded lines still is (existing test).

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_scaffold.py › ScaffoldTest.test_eject_lists_only_linked_files_with_something_recorded | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_eject_lists_only_linked_files_with_something_recorded` |

## Must never break

- The other eject tests, the linked `.gitignore` and `.claude` ones included.

## Out of scope

- None.

## Review

No review ran: no trigger fired (risk low, no public surface); everything goes into the end-of-push review.

- **End-of-push review (one pass over all of the 2026-11-22 todo fixes, by area):** scripts and hooks security reviews r1 FAIL, fixed in ddd2c43 and a1552fc; r2 FAIL past the cap, and the user chose to fix the rest (4a0e8f8) and park the read-only guard's lexer as a documented limitation (docs/wiki/Limitations.md). UI review r1 FAIL, fixed in b43026e. What is left is in `.sdlc/todo.md`.
