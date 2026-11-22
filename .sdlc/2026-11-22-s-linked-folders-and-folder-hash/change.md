# Doctor names a linked rules or hookify folder; a folder at a recorded path counts as edited

## Why

From `.sdlc/todo.md`: "When `.claude/rules`, `.claude/hookify` or `.sdlc` is itself a link out of the repo, doctor's globs list the outside folder's file names in its report (not their contents); check the folder with `link_problem` before globbing (`scaffold.team_rules` also reads up to 8 KiB of each outside `.md`, not printed) — security review L1 and r2 L1 of 2026-11-22-s-doctor-reads-no-links; also `scaffold.sha256` crashes on a folder at a lock-recorded path (r2, medium, predates it)".

Proof: with `.claude/rules` and `.claude/hookify` linked to an outside folder, doctor's rows name `secretname.md` and `secrethook.md`; with a folder at a lock-recorded file's path, `scaffold.py status` exits 1 with IsADirectoryError (the AC tests fail). `team_rules` no longer reads outside files since `scaffold.repo_text` (eaf6ad1), and a linked `.sdlc` is refused by `Project` since 1a4dfc0.

## Decisions

- **`repo_glob(root, folder, pattern)` in doctor:** a folder that `link_problem` refuses is named once (`.claude/rules/ (linked out of the repo or into .git)`), never listed.
- **`sha256` returns `""` for a path it can't open other than a missing one** (a folder, a looping link): no hash matches it, so it counts as edited and is never overwritten or deleted.

## Acceptance criteria

- **AC-001** With `.claude/rules` and `.claude/hookify` linked to an outside folder, doctor's rules and hookify rows warn and name the folder, and no outside file name reaches them.
- **AC-002** A folder at a lock-recorded file's path doesn't crash `status` or `upgrade-plan`, and the plan doesn't regenerate it.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_doctor.py › DoctorTest.test_folders_linked_out_of_the_repo_are_named_not_listed | `python3.10 -m unittest discover -s tests -t tests -p test_doctor.py -k test_folders_linked_out_of_the_repo_are_named_not_listed` |
| AC-002 | tests/test_scaffold.py › ScaffoldTest.test_a_folder_at_a_recorded_path_counts_as_edited | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_a_folder_at_a_recorded_path_counts_as_edited` |

## Must never break

- Plain rules and hookify folders, and plain recorded files: the doctor and scaffold tests pass.

## Out of scope

- None.

## Review

Security review fires (Risk: high); deferred by the user to one review over all of the 2026-11-22 todo fixes at the end of the push.
