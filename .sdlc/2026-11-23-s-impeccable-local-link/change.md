# impeccable's local config is never read through a link out of the repo

## Why

From `.sdlc/todo.md`: "`.impeccable/config.local.json` (the winning, machine-local file) is still read through a committed link (`scaffold.impeccable_hook_off`) — lane A of 2026-11-22-todo-lanes".

Proof: with `.impeccable/config.local.json` linked to a file outside the repo, or the `.impeccable` folder itself linked out, `impeccable_hook_off` reads the outside file and returns its value (AC-001's test fails). Root cause: only `config.json` goes through `sdlc_scopes.read_repo_text`; `config.local.json` is opened with `read_json`, which follows links.

## Decisions

- Both files go through `sdlc_scopes.read_repo_text`, so a link out of the repo or into `.git` reads as absent, like every other committed file sdlc reads. A machine-local file is still in the repo tree, and a committed link at its name is what the check is for.
- Ruled out: refusing only a link at the file's own name; `read_repo_text` resolves the whole path, so a linked `.impeccable` folder is caught by the same call.

## Acceptance criteria

- **AC-001** `impeccable_hook_off` reads `.impeccable/config.local.json` as absent when it, or the `.impeccable` folder, links out of the repo; a plain file still reads.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_scaffold.py › ScaffoldTest.test_impeccable_local_config_linked_out_of_the_repo_reads_as_absent | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_impeccable_local_config_linked_out_of_the_repo_reads_as_absent` |

## Must never break

- A plain `config.local.json` still wins over `config.json` (`test_impeccable_guardrail_follows_the_hook_switch` and its neighbours).
- Invalid JSON in either file is still a ValueError naming the file.

## Out of scope

- The other end-review leftovers in `.sdlc/todo.md`; SP-L1 is its own change.
