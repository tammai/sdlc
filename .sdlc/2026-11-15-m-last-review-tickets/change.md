# Eject reports what it unmerged; a malformed convention entry is reported; workbench writes keep mode and links

## Why

**Request:** the user's goal, "get job done unattend": the tickets still open in earlier changes' ## Review sections.
- LM3-09: `eject --apply` reports an empty `unmerged` list for `.claude/settings.json` allow entries and `.gitignore` lines. The lists it reports are the lock's own lists, which the unmerge empties as it goes.
- R2-05: upgrade-plan skips a lock `conventions` entry that fails its check without saying so, which hides why a template change isn't offered.
- LM2-08: `_write_atomic`, used for the workbench's `.gitignore` and workbench file, leaves a file 0600 and replaces a symlinked file.
- LM3-07: on Windows the save retries every permission error 50 times, including one that will never clear (a folder that refuses new files).

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| Eject reports copies of the lists, taken before it unmerges | reading them back after | the unmerge empties the lock's lists |
| A `conventions` entry under `.claude/rules/` that fails the check is an error item in upgrade-plan, not read | skipping it silently (today) | the user sees why its template change isn't offered; an entry outside `.claude/rules/` is still never read |
| `_write_atomic` keeps the target's mode (an ordinary new file's mode when it's new) and writes through links, for every caller | an opt-in per caller | one rule for every write; matches `write_json` |
| Only a permission error from the final rename is retried on Windows (another process has the file open); one from creating the temp file fails at once | retrying all of them | that one never clears |

## Acceptance criteria

- **AC-001** Given allow entries and `.gitignore` lines that setup added, when `eject --apply` runs, then its `unmerged` report lists them.
- **AC-002** Given a `conventions` lock entry for a `.claude/rules/` file whose recorded root fails the check, then upgrade-plan's conventions list has an error item for it and the file is not read.
- **AC-003** Given an existing file with mode 0644, or a symlink to a file, when `_write_atomic` writes it, then the mode stays 0644 and the link stays a link, with the target updated.
- **AC-004** Given a folder where the temp file can't be created, when a lock or config save runs, then it fails at once, without retrying.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_stack_blueprints.py › LastTickets.test_eject_reports_what_it_unmerged | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_eject_reports_what_it_unmerged` |
| AC-002 | tests/test_stack_blueprints.py › Hardening.test_lock_root_is_checked_on_read | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_lock_root_is_checked_on_read` |
| AC-003 | tests/test_stack_blueprints.py › LastTickets.test_atomic_write_keeps_mode_and_links | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_atomic_write_keeps_mode_and_links` |
| AC-004 | tests/test_stack_blueprints.py › LastTickets.test_temp_creation_refusal_is_not_retried | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_temp_creation_refusal_is_not_retried` |

## Must never break

- Eject still unmerges and deletes exactly what it did before; only its report changes.
- A save that another process briefly holds open still retries.
- The plugin stays Python stdlib only.

## Out of scope

- Two narrow races, left by decision because closing them needs the locking the user declined: `.claude/rules` swapped for a link mid-render (R2-13), and two renders of one convention at once without hard links (LM3-03).

## Review

No review ran: low risk, no trigger fired; every AC red then green (verify.py).
