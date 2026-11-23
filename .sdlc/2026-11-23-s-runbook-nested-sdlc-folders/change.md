# The deploy runbook path is barred from `.claude` and `.sdlc` at any depth

## Why

From `.sdlc/todo.md`: "`scaffold.runbook_path` bars `.claude` and `.sdlc` only at the top, so a nested `pkg/.claude/…` or an app repo's `.sdlc` in a workbench passes as a deploy runbook — security review S-4 of 2026-11-23-todo-fixes, unconfirmed, predates it".

Proof: `runbook_path(root, "pkg/.claude/skills/x/SKILL.md")` and `"api/.sdlc/todo.md"` are accepted (AC-001's test fails), so a committed `deploy.runbook` could have `/sdlc:deploy` append to a nested package's Claude Code skill or an app repo's sdlc state. Root cause: the check tests `parts[0]` only for `.claude` and `.sdlc`, while `.git` is tested at every depth.

## Decisions

- Also refused (security review L-2, L-3, found here, predating the change): an agent instruction file as the runbook, since `/sdlc:deploy` appends to it, and a name with a control or format character, with the objects path's own check, now shared (`sdlc_scopes.odd_name`).
- Every segment is checked for all three folders, in every spelling (`sdlc_scopes.dot_segment`), as `objects._refused` already does. Ruled out: listing nested exceptions; no runbook belongs in either folder.

## Acceptance criteria

- **AC-001** `runbook_path` refuses a path with `.claude` or `.sdlc` (any spelling) at any depth, and still accepts `knowledge/runbooks/deploy.md`, `docs/claude/…` and `.claudex/…`.

- **AC-002** `runbook_path` refuses an agent instruction file (`CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, any case, any depth) and a name with a control or format character.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_sdlc_layout.py › SdlcFolderSpellingTest.test_runbook_path_refuses_them_at_any_depth | `python3.10 -m unittest discover -s tests -t tests -p test_sdlc_layout.py -k test_runbook_path_refuses_them_at_any_depth` |
| AC-002 | tests/test_sdlc_layout.py › SdlcFolderSpellingTest.test_runbook_path_refuses_instruction_files_and_odd_names | `python3.10 -m unittest discover -s tests -t tests -p test_sdlc_layout.py -k test_runbook_path_refuses_instruction_files_and_odd_names` |

## Must never break

- The default runbook `knowledge/runbooks/deploy.md` and any path outside those folders still pass.

## Review

- **What fired:** a security review, because the risk is high: an untrusted config path reaches a file sdlc writes. It ran on opus.
- **Round 1, PASS.** L-1 (a test gap) was filled. L-2 (instruction files accepted as the runbook) and L-3 (control and format characters) predate this change; I confirmed both and fixed them here as AC-002, with the objects path's check now shared.
- **Round 2, PASS** (closing check): every round-1 finding is gone, and the fixes added no bug. L-4 (no test of a link to an instruction file) is added.
- **Reports:** `.sdlc/.work/findings/2026-11-23-s-runbook-nested-sdlc-folders/security-r1.md` and `security-r2.md`.
- **Tests:** full suite 788 OK on Python 3.10. No lesson filed.
