# The .git checks drop the code points HFS+ ignores, and the hooks' check ignores case

## Why

From `.sdlc/todo.md`: "`git_internal` doesn't drop the code points HFS+ ignores (U+200C and the rest of git's `is_hfs_dotgit` set), so `.g‌it/` passes on an HFS+ volume (APFS doesn't ignore them); unconfirmed — security review R2-5 of 2026-11-22-s-lock-template-trusted; `scripts/scaffold.py` `_git_segment`".

Proof: `scaffold.py render … .g‌it/hooks/x` is accepted (AC-001's test fails). The same class in the hooks' reader added today (`sdlc_scopes._inside`, 1a4dfc0): a config linked to `../.GIT/config.json` passed on macOS, where `normcase` doesn't lower case (AC-002's test fails).

## Decisions

- `_git_segment` and `sdlc_scopes._inside` drop git's `is_hfs_dotgit` code points (U+200C–U+200F, U+202A–U+202E, U+206A–U+206F, U+FEFF) and compare lower-cased, with the trailing dots/spaces, the NTFS stream suffix and `git~1` as before.
- Refused on every volume, as git does, not only on HFS+.

## Acceptance criteria

- **AC-001** `render` and `record` refuse `.g‌it/…`, `﻿.git/…` and `.gi⁪t/…`.
- **AC-002** The hooks' config reader reads a config linked to `../.GIT/config.json` or `../.g‌it/config.json` as absent.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_scaffold.py › ScaffoldTest.test_nothing_is_recorded_or_rendered_under_git | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_nothing_is_recorded_or_rendered_under_git` |
| AC-002 | tests/test_sdlc_layout.py › LinkedConfigTest.test_config_and_manifest_linked_out_of_the_repo_read_as_absent | `python3.10 -m unittest discover -s tests -t tests -p test_sdlc_layout.py -k test_config_and_manifest_linked_out_of_the_repo_read_as_absent` |

## Must never break

- Names that only start with `.git` (`.gitignore`, `.github/`, `.gitattributes`) still render.

## Out of scope

- `hooks/role_guard.py`'s own path checks: the lexer todo.

## Review

Security review fires (Risk: high); deferred by the user to one review over all of the 2026-11-22 todo fixes at the end of the push.
