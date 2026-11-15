# Scaffold lock: merge concurrent saves, keep eject inside the repo, and the smaller lock tickets

## Why

**Request (verbatim):** "fix them": the tickets still open after PR #58, from
`.sdlc/2026-11-15-m-scaffold-lock-safety/change.md` ## Review. For concurrency the user chose "Detect, don't
prevent": at save, re-read the lock and merge only what this command changed, with no lock file and no OS locks.

The tickets:
- concurrent scaffold commands lose each other's lock changes;
- a committed lock naming `../` or absolute paths makes `eject --apply` delete outside the repo (LS3-05);
- a kill between the fallback's placeholder and its replace leaves an empty rule file that a rerun refuses (LS3-02);
- a `config.json` that isn't an object crashes `status` (LS3-04);
- a lock file containing `null` reads as absent (LS3-06);
- `run-commands` loses its results when the lock is gone at save (LS3-07);
- a kill leaves a stray `.tmp-` file, and the temp file's handle leaks if `fdopen` fails (LS3-08).

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| `Project` keeps a copy of the lock as it read it. At save it re-reads the file; if another command changed it since, it applies only this command's own changes (keys and entries added, changed or removed against that copy) onto the file as it is now: objects key by key, lists by item. Where both changed the same value, this command's wins, as every save does today | a mutex (two designs failed review); refusing on conflict (a command that already wrote files would leave them untracked) | the user's choice; lost updates narrow to two commands changing the same entry |
| A lock removed since this command read it (eject ran meanwhile) is not recreated: the save fails with error JSON. `run-commands` then still prints its results, with the save error beside them | writing it back | recreating it would undo the eject |
| `check_lock` refuses a `files` key or `declined` item that isn't a relative path inside the repo (absolute, a drive, `..`). `eject` also skips any file whose real path, after links, is outside the repo, listing it under `outside`; it never deletes it, and `--also` can't take it | trusting the lock's paths | repo data is read like input (recurring defect); links are the other route out |
| An empty file at a convention's path with that convention's lock entry is this command's interrupted placeholder, and a rerun renders over it | asking the user | an empty file holds nothing to lose, and the lock says the plugin made it |
| `config.json` is checked on first read like the lock: it must be a JSON object | a check per reader | `status`, the session hook and doctor read it unguarded |
| A lock file containing JSON `null` is refused like any other non-object, and plain `init` refuses it as existing | reading it as absent | it exists; reading it as absent silently restarts setup |
| `_temp_copy` closes the handle if `fdopen` fails and, before writing, removes `.tmp-` files in the same folder that are over an hour old | leaving them | a kill can't clean up after itself; the next write can |

## Acceptance criteria

- **AC-001** Given two scaffold commands that read the lock and then save different changes, then the lock holds both.
- **AC-002** Given a lock removed after a command read it, when the command saves, then the lock isn't recreated; and when that command is `run-commands`, its results are still printed.
- **AC-003** Given a lock whose `files` names a path outside the repo, or a file reached through a link out of the repo, when `eject --apply` runs, then nothing outside the repo is deleted.
- **AC-004** Given an empty rule file left by an interrupted render, with its lock entry, when `conventions` runs again, then the rule is rendered.
- **AC-005** Given a `config.json` that isn't an object, or a lock that is JSON `null`, then `status` exits with error JSON naming the file, and the session hook says it's unreadable.
- **AC-006** Given a `.tmp-` file over an hour old beside a file scaffold writes, then the next write removes it.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_stack_blueprints.py › LockMerge.test_concurrent_saves_merge | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_concurrent_saves_merge` |
| AC-002 | tests/test_stack_blueprints.py › LockMerge.test_removed_lock_is_not_recreated | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_removed_lock_is_not_recreated` |
| AC-003 | tests/test_stack_blueprints.py › LockMerge.test_eject_stays_inside_the_repo | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_eject_stays_inside_the_repo` |
| AC-004 | tests/test_stack_blueprints.py › LockMerge.test_empty_placeholder_renders_again | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_empty_placeholder_renders_again` |
| AC-005 | tests/test_stack_blueprints.py › LockMerge.test_config_and_null_lock_are_errors | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_config_and_null_lock_are_errors` |
| AC-006 | tests/test_stack_blueprints.py › LockMerge.test_stale_temp_files_are_swept | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_stale_temp_files_are_swept` |

## Must never break

- A save with no concurrent change writes exactly what it wrote before, and the lock file's format is unchanged.
- `init` and `init --force` still write a new lock; `eject` still deletes every plugin file inside the repo.
- An existing rule file with content is never overwritten.
- The plugin stays Python stdlib only.

## Failure modes

- Concurrent use: AC-001, AC-002.
- Untrusted repo data naming a path: AC-003.
- A crash mid-write: AC-004, AC-006.
- Persisted data read back: AC-005.

## Out of scope

- Mutual exclusion: two commands changing the same entry still end with the last writer's value (the user's choice).
- The gap between the save's re-read and its write: it is short, but it isn't closed.
- Dead `setdefault`s for `files`/`declined` (LS3-10): cosmetic.

## Review

- **Recommended and chosen:** code. It fired because the change file names concurrent use, untrusted repo paths and a crash mid-write as failure modes. Not asked: low risk. Round 3 was the user's choice at the review cap ("One more targeted round").
- **Verdicts:** built-in `code-review high --max-findings all`, rated here; reports in `.sdlc/.work/findings/2026-11-15-m-lock-merge-and-tickets/`.
  - `code-reviewer-r1.md` → FAIL — LM-01, 02, 05 high, plus bugs.
  - `code-reviewer-r2.md` → FAIL — LM2-03, 04 high.
  - `code-reviewer-r3.md` → PASS.
- **Fixed (tested):**
  - **AC-001, the merge:**
    - this command's own objects stay the ones it saves, so a rollback through a held reference lands (LM-01);
    - a key both commands added starts from empty (LM-02);
    - a record in `files`, `conventions` or `command_runs` is kept whole (LM2-10);
    - every other section merges key by key (LM3-02);
    - the lock is written only when this command set it, or read it and changed it (LM2-03).
  - **AC-002:**
    - a lock removed or broken meanwhile is not overwritten (LM-07);
    - the merge base moves only after a successful write (LM2-07);
    - `run-commands` keeps its results on any save error (LM2-05).
  - **AC-003:** `check_lock` refuses paths outside the repo; eject lists a file reached through a link out under `outside` and never reads or deletes it (LM-09).
  - **AC-004:** the empty placeholder is rendered over.
  - **AC-005:**
    - `config.json` must be an object;
    - plain `init` refuses a malformed config and `--force` replaces it (LM-11, LM2-04);
    - a lock holding `null` is refused.
  - **AC-006:** only scaffold's own `.sdlc-tmp-*` files are swept (LM-05).
  - **Saves:**
    - lock and config are written atomically, keeping each file's mode and writing through links (LM-04);
    - `config.json` is written only when the command changed it (LM-03, LM2-08);
    - a read-only file is refused (LM2-02).
  - Full suite: 604 tests OK on Python 3.10, run from Git Bash.
- **Tickets:**
  - LM3-03: two concurrent renders of one convention without hard links can delete each other's placeholder.
  - LM3-05: a kill mid-save leaves `.sdlc/.sdlc-tmp-*` until the hourly sweep, and it could be committed.
  - LM3-10: `config.json` is written whole, not merged.
  - LM3-04: after a failed write, merged changes stay in memory (latent).
  - LM3-07: the Windows retry also retries permanent permission errors.
  - LM3-08: `os.access` misses ACL-only protection on Windows.
  - LM3-09: eject's unmerged report is empty (pre-existing).
  - LM2-01: `file_state` and `render` still follow links out (pre-existing); needs one shared containment helper.
  - LM2-08: the workbench writes keep 0600 (pre-existing).
  - LM2-09: lists of objects merge by equality (latent).
  - LM2-12: the atomic replace resets owner, ACLs and hard links.
  - LM-12 to 15, LM3-11: altitude and cleanup.
- **Drift and manual checks:**
  - Deviations: the helpers, the test change for the `run-commands` script, the docs, the r1, r2 and r3 fix lines.
  - AC-006's wording says `.tmp-`; the sweep now takes `.sdlc-tmp-` (recorded as a deviation).
- **Lessons filed:** None new.

