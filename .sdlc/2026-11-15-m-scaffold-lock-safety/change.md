# Scaffold lock safety: one writer at a time, no partial rule files, every reader checked

## Why

**Request (verbatim):** "fix them too": the tickets still open after PR #57, from
`.sdlc/2026-11-15-m-convention-hardening/change.md` ## Review:
- R2-01: concurrent scaffold commands overwrite each other's lock;
- R2-03: a kill during the no-hard-link fallback leaves a partial rule file;
- R2-06 and R2-09: lock checks cover only container types, and `status` and `design` read the lock unchecked.

`.sdlc/scaffold.lock.json` records every file the plugin placed, so upgrade and eject depend on it. Today:
- two commands at once (parallel build parts, a hook and a command) each read the lock, change it and write it back, and the last write wins;
- a lock that is the wrong shape inside still crashes some commands with a traceback.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| `run-commands` re-reads the scaffold lock when its commands finish and saves only `command_runs` into it | saving the copy read at the start | the run can take minutes; a change saved meanwhile (another command, the user) would be lost |
| The lock's shape is checked once, when `Project.lock` is first read: every key a command reads (`LOCK_SHAPE`, `LOCK_NESTED`: files objects with a string `class` and string-or-null `sha256`/`template`, string items in `declined`, `hosts`, `setup.completed_steps`, `migrations.applied`, list values in `merged`, run objects in `command_runs`). Null reads as absent | one check per command (today); checking in `__init__` | every reader gets the check, including `status`, `design`, `contract` and `agents`; `init --force` reads the raw lock, so it can still repair a broken one |
| The fallback for filesystems without hard links claims the name with an exclusive create of an empty placeholder, then replaces the placeholder with the complete temp file | an exclusive create, then write (today); a check, then rename (on POSIX it overwrote a file that appeared in between, Review r1 LS-05) | never over anyone else's file on any OS; a kill leaves the file absent, complete, or empty (in the instant between the two steps), never partial |
| `_write_atomic` and `_publish_new` share one temp-file helper | two copies (R2-10) | the review flagged the drift between them |

## Acceptance criteria

- **AC-001** (dropped at the review cap, out of scope below) Given another scaffold command holding the lock, when `scaffold.py conventions` runs, then it waits and both changes are kept.
- **AC-002** (dropped at the review cap, out of scope below) Given a lock holder killed mid-command, then the next command runs without waiting.
- **AC-003** Given a change to the scaffold lock saved while `run-commands` is running the project's commands, then after `run-commands` both that change and its `command_runs` are in the lock.
- **AC-004** Given a filesystem without hard links and a render killed while it writes, then `.claude/rules/<stack>-<area>.md` is either absent or complete, never partial.
- **AC-005** Given a scaffold lock that is the wrong shape at the top or inside (a `files` entry that isn't an object or has no `class`, a `declined` item that isn't a string), when `status`, `design` or `upgrade-plan` runs, then it exits with error JSON naming the lock, not a traceback; and `init --force` still rewrites it.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | manual | dropped at the review cap (user's choice, 2026-11-15): no mutex ships; see Out of scope |
| AC-002 | manual | dropped at the review cap (user's choice, 2026-11-15): no mutex ships; see Out of scope |
| AC-003 | tests/test_stack_blueprints.py › LockSafety.test_run_commands_keeps_a_concurrent_change | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_run_commands_keeps_a_concurrent_change` |
| AC-004 | tests/test_stack_blueprints.py › LockSafety.test_killed_fallback_write_leaves_no_partial_file | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_killed_fallback_write_leaves_no_partial_file` |
| AC-005 | tests/test_stack_blueprints.py › LockSafety.test_every_reader_checks_the_lock | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_every_reader_checks_the_lock` |

## Must never break

- A well-formed lock reads and saves exactly as before; every existing command keeps its output.
- `init --force` restarts setup over a broken lock.
- The session-start hook and `doctor` keep reporting, not crashing: they already catch a `ValueError` from the lock.
- The plugin stays Python stdlib only.

## Failure modes

- A change saved while `run-commands` runs: AC-003.
- A crash mid-write: AC-004.
- Persisted data read back: AC-005.

## Out of scope

- One scaffold writer at a time (the first draft's AC-001 and AC-002). Dropped at the review cap by the user's choice (2026-11-15): two designs, a lock file created and deleted and then an OS lock (`flock`/`msvcrt`), each brought new high findings (two holders through takeover or eject, a 60 s hang on filesystems without locks, Windows and WSL not excluding each other). Concurrent scaffold commands can still lose one's lock change: a ticket. The atomic lock save went with it (it made saved files 0600 and replaced symlinked settings).
- A lock file that isn't valid JSON already fails `Project()` with error JSON (`read_json`), including for `init --force`. Unchanged.
- R2-05 (an entry failing `convention_entry` skipped silently), R2-13 (`.claude/rules` swapped for a link mid-render) and following links in `render`/`agents`: not in the request.

## Review

- **Recommended and chosen:** code. It fired because the change file names concurrent use and a crash mid-write as failure modes. Not asked: low risk. Rounds past 2 were the user's choice at the review cap.
- **Verdicts:** built-in `code-review high --max-findings all`, rated here; reports in `.sdlc/.work/findings/2026-11-15-m-scaffold-lock-safety/`.
  - `code-reviewer-r1.md` → FAIL — LS-01, 02, 03, 05 high, plus bugs.
  - `code-reviewer-r2.md` → FAIL — LS2-01, 02, 03 high.
  - `code-reviewer-r3.md` → PASS.
- **What happened:**
  - **Round 1:** the first mutex design (a lock file created exclusively, taken over when stale, deleted on release) could let two writers run at once, spin forever, and be wedged by antivirus or clock skew. Its fallback rename also overwrote a file another program created.
  - **Fixes after round 1:**
    - an OS lock (`flock`/`msvcrt`) replaced the mutex;
    - the fallback became an empty placeholder, then a replace;
    - the lock's shape check grew to every key a command reads;
    - the lock save became atomic.
  - **Round 2:** three highs came from those fixes.
    - The atomic save made config, lock and settings files 0600 and replaced symlinked settings with plain files.
    - Eject's cleanup deleted a held lock file.
    - A filesystem without locks hung every command for 60 s.
  - **Review cap:** you chose "Drop mutex, ship the rest". The OS lock and the atomic save were removed, which closed those three highs by removal. AC-001 and AC-002 moved to Out of scope.
  - **Round 3:** confirmed nothing the removal left behind is broken.
- **Fixed (tested):**
  - AC-003: `run-commands` saves into the lock as it is on disk (`test_run_commands_keeps_a_concurrent_change`).
  - AC-004: the no-hard-link fallback never overwrites and never leaves part of a file. The kill test cuts the second rule-text write in str or bytes, so it fails against the old fallback, and it asserts exactly one rule-text write.
  - AC-005: `check_lock` runs on the first read of `Project.lock`: every key read, `command_runs` runs included. `status`, `design` and `upgrade-plan` give error JSON, the session hook says the lock is unreadable, and `init --force` still restarts over a malformed lock.
  - Shared `_temp_copy`.
  - Full suite: 597 tests OK on Python 3.10, from Git Bash.
- **Tickets:**
  - Concurrent scaffold commands can still lose one's lock change. Windows and WSL on one checkout make OS locks a poor fit; a different design is needed.
  - LS3-05: a committed lock whose `files` keys name `../` or absolute paths makes `eject --apply` delete outside the repo. This predates the change; worth doing next.
  - LS3-02: a kill between the fallback's placeholder and the replace leaves an empty rule file that a rerun refuses.
  - LS3-04: a `config.json` that isn't an object crashes `status`.
  - LS3-06: a lock containing `null` reads as absent.
  - LS3-07: `run-commands` loses its results when the lock is gone at save.
  - LS3-08: the temp file's handle leaks if `fdopen` fails, and a kill leaves a `.tmp-` file.
  - LS3-10: dead `setdefault`s for `files`/`declined`.
  - LS2-06, 08, 09, 11, 12, 13 went with the mutex.
- **Drift and manual checks:**
  - Deviations: the test changes, the helpers, the r1 and r2 fix lines, the review-cap removal, and the AC-002/AC-004 wording.
  - AC-001 and AC-002 are `manual` because they were dropped at the review cap.
  - The rewritten AC-002 test was never recorded failing before it was dropped.
- **Lessons filed:** None. The lesson "rounds past 2 are fix-added bugs" is already in the maintainer's notes.

