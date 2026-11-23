# impeccable's local config is never read through a link out of the repo

## Why

From `.sdlc/todo.md`: "`.impeccable/config.local.json` (the winning, machine-local file) is still read through a committed link (`scaffold.impeccable_hook_off`) — lane A of 2026-11-22-todo-lanes".

Proof: with `.impeccable/config.local.json` linked to a file outside the repo, or the `.impeccable` folder itself linked out, `impeccable_hook_off` reads the outside file and returns its value (AC-001's test fails). Root cause: only `config.json` goes through `sdlc_scopes.read_repo_text`; `config.local.json` is opened with `read_json`, which follows links.

## Decisions

- Both files go through `sdlc_scopes.read_repo_text`, so a link out of the repo or into `.git` reads as absent, like every other committed file sdlc reads. A machine-local file is still in the repo tree, and a committed link at its name is what the check is for.
- Ruled out: refusing only a link at the file's own name; `read_repo_text` resolves the whole path, so a linked `.impeccable` folder is caught by the same call.
- A file that is there but refused (a link out) or unreadable (not UTF-8) counts as hook off, for either file: sdlc keeps its own UI guardrail rather than drop it while impeccable, which may still read through the link, keeps its hook off (security-r1 S-1). Ruled out: reading it as absent, which deleted the guardrail.

## Acceptance criteria

- **AC-001** `impeccable_hook_off` never reads either file through a link out of the repo or into `.git`, at the file or the `.impeccable` folder, and counts such a file, or an unreadable one, as off; a plain file and a link inside the repo still read.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_scaffold.py › ScaffoldTest.test_impeccable_config_linked_out_of_the_repo_or_into_git_is_never_read | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_impeccable_config_linked_out_of_the_repo_or_into_git_is_never_read` |

## Must never break

- A plain `config.local.json` still wins over `config.json` (`test_impeccable_guardrail_follows_the_hook_switch` and its neighbours).
- Invalid JSON in either file is still a ValueError naming the file.
- No file means the hook runs.

## Out of scope

- The other end-review leftovers in `.sdlc/todo.md`; SP-L1 is its own change.

## Review

Security review fired (Risk: high), run once over both changes of branch `2026-11-23-todo-fixes` (`2026-11-23-s-impeccable-local-link`, `2026-11-23-s-sdlc-folder-spellings`), on opus.

- Round 1 PASS (no high): S-1 a refused or unreadable impeccable config counted as hook running, so sdlc dropped its UI guardrail — fixed (counts as off); S-2 `.ſdlc` opens `.sdlc` on APFS — reproduced, fixed (`casefold`); S-3 short names `~2`-`~4` — fixed; S-5 test cases — added; S-4 (runbook bars `.claude`/`.sdlc` only at the top, predates it) — ticket in `.sdlc/todo.md`.
- Round 2 PASS (closing check: each round-1 finding gone): R2-2 a test case that couldn't fail — fixed; R2-1 `.gıt` on NTFS (unconfirmed, predates it) — fixed; R2-3 hashed short names — wording softened, the resolved-path checks cover it; R2-4 (a dotfiles-linked local config gets advice that doesn't name the link) — ticket.
- Reports: `.sdlc/.work/findings/2026-11-23-todo-fixes/security-r1.md`, `security-r2.md`. No lesson filed.
