# `.claude` and `.sdlc` are barred in every spelling `.git` is

## Why

From `.sdlc/todo.md`: "`runbook_path` and `objects` bar `.claude` / `.sdlc` with a narrower spelling rule than `.git`'s (8.3 names, NTFS stream suffix, HFS+ code points); generalise `sdlc_scopes.git_segment` — end review SP-L1, unconfirmed".

Proof: `scaffold.runbook_path` and `objects.target` accept `CLAUDE~1/x.md`, `SDLC~1/x.md` and `.claude::$DATA/x.md`, which open `.claude` or `.sdlc` on Windows; `runbook_path` also accepts `.c‌laude/x.md`, which opens `.claude` on HFS+ (the tests fail). Root cause: `git_segment` holds the one spelling rule but names only `.git`; the two checks compare `.claude` and `.sdlc` by case and trailing dots alone.

## Decisions

- `sdlc_scopes.dot_segment(seg, name)` is the rule, with the 8.3 short name taken as Windows does (dot dropped, first six characters, `~1`); `git_segment(seg)` is `dot_segment(seg, ".git")`, so `.git` keeps exactly its meaning.
- Short names `~1`-`~4` are barred for `.claude` and `.sdlc` (a folder sorting first, `.claude-a`, gives `.claude` `~2`), `~1` alone for `.git`, as git does (security-r1 S-3).
- Case is compared with `casefold()`, as APFS folds it: `.ſdlc` opens `.sdlc` there (security-r1 S-2, reproduced). `.git` gains this too. Also upper-cased first, as NTFS compares: `.gıt` may open `.git` there (security-r2 R2-1, unconfirmed, predates it).
- The hashed short name Windows gives past `~4` isn't barred by the rule; where the folder exists, the checks on the resolved path catch it (security-r2 R2-3).
- `runbook_path` still bars `.claude` and `.sdlc` only at the top (as before); `objects` at any depth (as before).

## Acceptance criteria

- **AC-001** `dot_segment` names every spelling of `.git`, `.claude` and `.sdlc` (`.ſdlc`, `.gıt` and `CLAUDE~2` included; numbered short names only), and not names that only start like them.
- **AC-002** `runbook_path` refuses every spelling of `.claude` and `.sdlc`.
- **AC-003** `objects.target` refuses every spelling of `.claude` and `.sdlc`, at the top or deeper.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_sdlc_layout.py › SdlcFolderSpellingTest.test_the_shared_helper_names_every_spelling | `python3.10 -m unittest discover -s tests -t tests -p test_sdlc_layout.py -k test_the_shared_helper_names_every_spelling` |
| AC-002 | tests/test_sdlc_layout.py › SdlcFolderSpellingTest.test_runbook_path_refuses_every_spelling | `python3.10 -m unittest discover -s tests -t tests -p test_sdlc_layout.py -k test_runbook_path_refuses_every_spelling` |
| AC-003 | tests/test_sdlc_layout.py › SdlcFolderSpellingTest.test_objects_path_refuses_every_spelling | `python3.10 -m unittest discover -s tests -t tests -p test_sdlc_layout.py -k test_objects_path_refuses_every_spelling` |

## Must never break

- Every `.git` check keeps its meaning (`GitSegmentTest`, `GitPrefixedNamesPassTest`).
- The old layout's own `.sdlc/objects.md` (objects set to true) is still allowed.

## Out of scope

- The read-only guard's own path checks (`hooks/role_guard.py`): the lexer todo.

## Review

Security review fired (Risk: high), run once over both changes of branch `2026-11-23-todo-fixes` (`2026-11-23-s-impeccable-local-link`, `2026-11-23-s-sdlc-folder-spellings`), on opus.

- Round 1 PASS (no high): S-1 a refused or unreadable impeccable config counted as hook running, so sdlc dropped its UI guardrail — fixed (counts as off); S-2 `.ſdlc` opens `.sdlc` on APFS — reproduced, fixed (`casefold`); S-3 short names `~2`-`~4` — fixed; S-5 test cases — added; S-4 (runbook bars `.claude`/`.sdlc` only at the top, predates it) — ticket in `.sdlc/todo.md`.
- Round 2 PASS (closing check: each round-1 finding gone): R2-2 a test case that couldn't fail — fixed; R2-1 `.gıt` on NTFS (unconfirmed, predates it) — fixed; R2-3 hashed short names — wording softened, the resolved-path checks cover it; R2-4 (a dotfiles-linked local config gets advice that doesn't name the link) — ticket.
- Reports: `.sdlc/.work/findings/2026-11-23-todo-fixes/security-r1.md`, `security-r2.md`. No lesson filed.
