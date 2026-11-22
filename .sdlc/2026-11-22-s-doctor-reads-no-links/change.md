# Doctor reads no committed file through a link out of the repo

## Why

From `.sdlc/todo.md`: "Doctor reads CLAUDE.md through a committed link to count its lines (`scripts/doctor.py` CLAUDE.md size check), so `CLAUDE.md -> /dev/zero` or a FIFO hangs it; check `scaffold.link_problem(root, "CLAUDE.md")` and report the link — security review R2-L1 of 2026-11-22-s-fixed-writers-refuse-links, predates it".

A link is committed like any file, and cloning a repo isn't consent (`knowledge/gotchas/repo-config-is-untrusted.md`). Proof: with CLAUDE.md linked to a 100-line file outside the repo, doctor reports `100 lines (budget 60)` (AC-001's test fails); a link to `/dev/zero` never returns. The same class covers every committed file doctor opens by name or glob: `.claude/rules/*.md`, the hookify rules, `knowledge/index.md` (whose broken link targets doctor prints, so an outside file's text reaches the report), the feature state files, and the freshness files under `.sdlc/.work/` (gitignored, but `git add -f` commits them; the `.error` file's first 200 characters are printed). Root cause: these reads have no containment check, while `.gitignore` and the settings files already go through `scaffold.link_problem`.

## Decisions

- **One reader, `scaffold.repo_text(root, rel)` (doctor's `repo_text` wraps it; `team_rules`, `area_rules` and the AGENTS block use it too, review r2 H1),** returns the file's text, or why it isn't read: `scaffold.link_problem` holds, or the file can't be opened (a broken or looping link, a folder), so doctor warns instead of crashing (review r1 M1); every read of a committed repo file in doctor goes through it (hookify rules are filtered by the same check before the hookify engine loads them).
- **A linked or unreadable file is named, not read:** its row warns with the path, why, and "not read", and a fix to make it a plain, readable file (added to the row's other fixes, not in place of them). Nothing from it decides a row (no line count, no rule paths, no active feature).
- A link that stays inside the repo, outside `.git`, is still followed, as everywhere else.
- Ruled out: a read timeout or a size cap. They'd bound a hang but still copy an outside file's text into the report.

## Acceptance criteria

- **AC-001** With CLAUDE.md, `knowledge/index.md`, a `.claude/rules/*.md`, a hookify rule and a feature's `state.md` each linked to a file outside the repo, doctor's rows (CLAUDE.md size, knowledge index, rules paths, hookify rules, features) warn, name the linked file and say it's not read; none of the outside text reaches the report, CLAUDE.md's lines aren't counted and the linked feature isn't counted as active. The same holds for `.sdlc/.work/verify-freshness.json` and `.error` (review r1 H1).
- **AC-002** A broken or looping link, or a folder, at one of those names gives a warn row that names it and says it's not read, not a traceback; a link that stays inside the repo, outside `.git`, is still followed, and one into `.git` is not read (review r1 M1). A folder at a hookify rule's name, read by `scaffold.team_rules` through `cmd_status`, warns too (review r2 H1), and so does a committed `verify-freshness.json` of the wrong shape (review r2 M1).
- **AC-003** The AGENTS.md block leaves out a CLAUDE.md or `.claude/rules/*.md` that can't be opened (a folder) and keeps the readable rules (review r2 H1).

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_doctor.py › DoctorTest.test_repo_files_linked_out_of_the_repo_are_named_not_read | `python3.10 -m unittest discover -s tests -t tests -p test_doctor.py -k test_repo_files_linked_out_of_the_repo_are_named_not_read` |
| AC-002 | tests/test_doctor.py › DoctorTest.test_unreadable_repo_files_warn_instead_of_crashing | `python3.10 -m unittest discover -s tests -t tests -p test_doctor.py -k test_unreadable_repo_files_warn_instead_of_crashing` |
| AC-002 | tests/test_doctor.py › DoctorTest.test_freshness_state | `python3.10 -m unittest discover -s tests -t tests -p test_doctor.py -k test_freshness_state` |
| AC-003 | tests/test_scaffold.py › ScaffoldTest.test_agents_block_skips_unreadable_sources | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_agents_block_skips_unreadable_sources` |

## Must never break

- Plain files are read and reported as before: the rest of `test_doctor` passes.

## Failure modes

- Untrusted input reaching a file path: a committed link; checked on the resolved path, every segment, as `link_problem` does.

## Out of scope

- The hooks' own reads of state files (`hooks/sdlc_layout.py`): a separate path; doctor is what the todo names.
- The shared JSON loaders (`.sdlc/config.json`, the lock, `workbench.json` through `scaffold.Project`, `sdlc_layout`, `objects`, `sdlc_scopes`): review r1 M2, a todo.

## Review

- **Fired:** security, because `Risk: high` (a committed link reaching a file path). `sdlc:code-reviewer` on opus.
- **Round 1, FAIL:** H1 the `.sdlc/.work` freshness files were read through a link; M1 a broken or looping link, or a folder, crashed doctor; L2 the link fix replaced a row's other fix. All fixed test first (AC-001 widened, AC-002).
- **Round 2, FAIL (cap):** H1 a folder at a hookify rule's name crashed doctor through `scaffold.team_rules` (and `area_rules`, the AGENTS block); M1 a wrong-shape `verify-freshness.json` crashed doctor. The user chose one more fix round: one reader, `scaffold.repo_text`, and a shape check (AC-002, AC-003).
- **Round 3: deferred by the user** to one review over all of the 2026-11-22 todo fixes at the end of the push.
- **Tickets in `.sdlc/todo.md`:** r1 M2 (shared JSON loaders through a link), r1 L1 + r2 L1 (linked folders' globs; `scaffold.sha256` on a folder), r1 L3 (rule `paths:` stall).
- **Lessons:** none new; the recurring defect "a path rule checked on one form of the path only" covers it.

- **End-of-push review (one pass over all of the 2026-11-22 todo fixes, by area):** scripts and hooks security reviews r1 FAIL, fixed in ddd2c43 and a1552fc; r2 FAIL past the cap, and the user chose to fix the rest (4a0e8f8) and park the read-only guard's lexer as a documented limitation (docs/wiki/Limitations.md). UI review r1 FAIL, fixed in b43026e. What is left is in `.sdlc/todo.md`.
