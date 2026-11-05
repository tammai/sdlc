# hosts.py ignores stray entries in hosts/skills/ and hosts/cursor/agents/

## Why

**Request (verbatim):** hosts.py build crashes, and check reports stale, on a stray file in hosts/skills/ — `scripts/hosts.py` treats every entry in `hosts/skills/` as a skill folder. A stray file there, such as the `.DS_Store` macOS writes, makes `check` report `hosts/skills/.DS_Store/SKILL.md` as stale on every run, and `build` crash with a traceback before writing anything. A folder in `hosts/skills/` without a `SKILL.md` does the same. Expected: entries that aren't a folder holding a `SKILL.md` are ignored by `check` and `build`; `check` stays `{ "stale": [] }` and `build` succeeds. Root cause: `stale()` builds `hosts/skills/<name>/SKILL.md` for every `os.listdir` entry without checking it's a directory with that file, and `main()` then calls `os.remove` on the path without handling one that isn't there. The listing of `hosts/cursor/agents/` is unfiltered in the same way.

A maintainer on macOS gets a failing `check` (and CI-style drift) and a crashing `build` from a file Finder writes on its own.

**Bug:** `tests/test_hosts.py › test_stray_file_in_hosts_skills_is_ignored` fails today with `{'stale': ['hosts/skills/.DS_Store/SKILL.md']}`; the folder and cursor-agents variants fail the same way. Root cause: `stale()` lists `hosts/skills/` and `hosts/cursor/agents/` with no filter, so every entry not in the fresh build is reported as a file to delete, and `build` then removes a path that doesn't exist.

**The user's words:** None asked.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| Filter in `stale()`: a skill is a folder holding a `SKILL.md` file; a Cursor agent is a `.md` file | Catching the error around `os.remove` in `main()` | `check` would still report the stray entry as stale; the listing is the root cause |
| Leave stray entries on disk | Deleting them | They aren't ours; the request says ignore |

**Proposals not asked for:** None

## Acceptance criteria

- **AC-001** Given a stray file `hosts/skills/.DS_Store`, when `check` then `build` run, then check is `{"stale": []}` exit 0, build writes nothing and exits 0, and the file is left alone.
- **AC-002** Given a folder in `hosts/skills/` with no `SKILL.md`, when `check` then `build` run, then both report nothing and exit 0, and the folder is left alone.
- **AC-003** Given a stray non-`.md` file or a folder in `hosts/cursor/agents/`, when `check` then `build` run, then both report nothing and exit 0.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_hosts.py › test_stray_file_in_hosts_skills_is_ignored | `python3 -m unittest discover -s tests -t tests -k test_stray_file_in_hosts_skills_is_ignored` |
| AC-002 | tests/test_hosts.py › test_folder_without_skill_md_in_hosts_skills_is_ignored | `python3 -m unittest discover -s tests -t tests -k test_folder_without_skill_md_in_hosts_skills_is_ignored` |
| AC-003 | tests/test_hosts.py › test_stray_entries_in_cursor_agents_are_ignored | `python3 -m unittest discover -s tests -t tests -k test_stray_entries_in_cursor_agents_are_ignored` |

## Must never break

- A generated file whose source was removed is still reported by `check` and deleted by `build` (guarded by `tests/test_hosts.py › test_removed_command_and_agent_are_still_deleted`, which passed before the fix too).
- `check` on the real repo stays `{"stale": []}`.

## Out of scope

- `dist`'s copy of the repo (it already skips nothing but `.git`, `tests`, `__pycache__`; a stray file is copied harmlessly).

## Review

No review ran: no trigger fired.
