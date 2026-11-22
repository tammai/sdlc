# The guard denies shell syntax its lexer reads differently from the shell

## Why

From `.sdlc/todo.md`: "`role_guard.lex` reads some shell syntax differently from the shell, so a write hides in a line the read-only-repo guard (GRD-FR-033) and the watch guard pass: a substitution inside `$(( ))`, a `#` after an escaped space read as a comment, ANSI-C `$'…'` quoting, zsh's `>!` redirect — security review SR1-H1 of 2026-11-22-m-watch-guard-reads, predates it; `hooks/role_guard.py` `_lex`".

Proof: in a workbench, each of these passes the guard though the shell removes or writes `specs/a.md` (AC-001's test fails):
- `echo $(( $(rm specs/a.md) + 1 ))` and the backtick form;
- `echo a\ #; rm specs/a.md`;
- `echo $'\''; rm specs/a.md`;
- `echo x >! specs/a.md` and `>| specs/a.md`.

## Decisions

- **Deny, don't parse.** `.claude/rules/hooks.md` says not to widen a parser. `_lex` (sh) raises `Unreadable`, a kind of `TooDeep`, on each construct:
  - ANSI-C `$'`;
  - `>!` and `>|`;
  - a `#` after an escaped blank;
  - `$(` or a backtick inside `$(( ))` / `(( ))`.
  
  Every caller already denies on `TOO_DEEP`, and the reason now names these constructs and asks for plain syntax.
- The cost: in a workbench, and in a repo with recorded acceptance tests (the other `shell_write` guard), commands using these rare constructs are denied with that reason, even harmless ones.

## Acceptance criteria

- **AC-001** Each hidden-write line above is denied; `echo $(( 1 + 2 )) > out.txt`, `echo 'a #b'`, `echo x > out.txt` and `printf '%s' x` still pass.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_workbench.py › ReviewRound4Guards.test_shell_syntax_the_lexer_cant_read_is_denied | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_shell_syntax_the_lexer_cant_read_is_denied` |

## Must never break

- The other ReviewRound4Guards tests, test_role_guard, test_recorded_tests.

## Out of scope

- PowerShell and cmd dialects.

## Review

Security review fires (Risk: high); deferred by the user to one review over all of the 2026-11-22 todo fixes at the end of the push.

- **End-of-push review (one pass over all of the 2026-11-22 todo fixes, by area):** scripts and hooks security reviews r1 FAIL, fixed in ddd2c43 and a1552fc; r2 FAIL past the cap, and the user chose to fix the rest (4a0e8f8) and park the read-only guard's lexer as a documented limitation (docs/wiki/Limitations.md). UI review r1 FAIL, fixed in b43026e. What is left is in `.sdlc/todo.md`.
