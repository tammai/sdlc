# diff_stats and verify_freshness keep file names with spaces and non-ASCII whole

## Why

`verify.drift()` and the reviewers read `diff_stats.collect()`'s file lists; `verify.py` and the trust anchor read `verify_freshness.changed_code_files()`. Both mangled real file names, so drift was reported for files that don't exist and missed for the task that names the real file.

Request (verbatim): "diff_stats splits file names with spaces and keeps git's quoting on non-ASCII names. `diff_stats.collect()` splits file names that contain a space, and keeps git's quoting on non-ASCII names. An untracked `src/my file.py` comes back as two files, `src/my` and `file.py`; `café.py` comes back as `"caf\303\251.py"` with the quotes. `verify.drift()` then reports drift for files that don't exist, and for the task that names the real file. Expected: `['café.py', 'my file.py']`: each path once, exactly as on disk. Root cause: `scripts/diff_stats.py` `collect()` (and `parse_diff()` for `+++ b/` lines) splits `git ls-files --others` / `git diff --name-only` output with `.split()`, which splits on spaces, and git's default `core.quotePath` quotes non-ASCII paths. Use `-z` and split on NUL (or pass `-c core.quotePath=false` where `-z` isn't available). `hooks/verify_freshness.py` `changed_code_files()` has the same quoting problem: a non-ASCII `.md` counts as code because its name ends in `.md"`."

Proof: the three tests below failed before the fix: untracked `src/my file.py` came back as `src/my`, `file.py`; `café.py` as `"caf\303\251.py"`; `changed_code_files` returned `"notes caf\303\251.md"` as code.

Root cause: name lists were read from git's default output, split on whitespace, and kept git's C-style quoting (`core.quotePath`); `+++ ` diff headers are quoted the same way, and git appends a tab to a header name that contains a space.

## Decisions

- Name lists (`git diff --name-only`, `git ls-files --others`) use `-z` and split on NUL: no quoting, no whitespace splitting, and it covers every odd character (tabs, quotes, newlines), unlike `core.quotePath=false`, which still quotes those.
- The `+++ ` header in `parse_diff()` has no `-z` form: it is unquoted with a small C-unquote (octal bytes decoded as UTF-8, `\t`, `\n`, `\"`, `\\`) and its trailing tab is dropped. Ruled out: `core.quotePath=false` alone, which leaves names with `"` or `\` quoted.

## Acceptance criteria

- AC-001: untracked files named `src/my file.py` and `café.py` are each listed once, as on disk, in `changed_files`, `new_files` and `files`.
- AC-002: the same names committed since the base (and a modified file beside them) are listed once, as on disk, and their added lines are counted from the diff.
- AC-003: `verify_freshness.changed_code_files()` returns `dé.py` and `src/my file.py` whole, and doesn't count `notes café.md` as code.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_diff_stats.py › test_untracked_names_with_spaces_and_non_ascii_stay_whole | `python3 -m unittest discover -s tests -t tests -p test_diff_stats.py -k test_untracked_names_with_spaces_and_non_ascii_stay_whole` |
| AC-002 | tests/test_diff_stats.py › test_committed_names_with_spaces_and_non_ascii_stay_whole | `python3 -m unittest discover -s tests -t tests -p test_diff_stats.py -k test_committed_names_with_spaces_and_non_ascii_stay_whole` |
| AC-003 | tests/test_verify_freshness.py › test_changed_code_files_keeps_names_with_spaces_and_non_ascii_whole | `python3 -m unittest discover -s tests -t tests -p test_verify_freshness.py -k test_changed_code_files_keeps_names_with_spaces_and_non_ascii_whole` |

## Must never break

- Every existing `test_diff_stats.py` and `test_verify_freshness.py` test; ASCII names come back unchanged.
- Git output is still read with `encoding="utf-8", errors="replace"`.

## Out of scope

- Other scripts that read git name lists; only the two named in the request change.

## Review

No review ran: no trigger fired.
