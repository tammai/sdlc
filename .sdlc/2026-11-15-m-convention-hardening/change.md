# Fix the tickets the stack-blueprints review left

## Why

**Request (verbatim):** "can you do the review?", answered "Fix the review tickets": the tickets listed in
`.sdlc/2026-11-14-l-stack-blueprints/change.md` ## Review (PR #53, merged 2026-11-15).

Those tickets are gaps in `scaffold.py conventions`, the lock it reads, and the docs around it:
- a write that can leave the repo or overwrite a file;
- an untracked file left after a crash;
- lock data that still crashes a script;
- a rule whose globs cover the wrong app;
- docs that point at things that don't exist.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| The lock's shape (a JSON object, `files` an object, `declined` a list) is checked once, in `require_lock`, so every command that reads it gets the error JSON | a check per command | recurring defect "malformed state or config crashes a script": one check on every path. `conventions` keeps its per-item report in upgrade-plan (Review r1: the rest of the plan still stands) |
| A render records the lock entry first, then publishes the file through a hard link from a temp file, which fails if a file appeared in the meantime; a filesystem without hard links falls back to an exclusive create | write then save (today); `os.replace` after an exists check | a crash after the save leaves an entry without a file, which a rerun renders (r1's M1 fix); the link never overwrites |
| A `.claude/rules` folder (or `.claude`) that resolves outside the repo is refused | following it like the other scaffold writers | recurring defect: paths kept inside the repo after symlinks. The other writers are out of scope (below) |
| `--one-deployable` keeps only a node template's `backend/` globs; Define passes it for the one-deployable shape | a new config field; leaving `src/**` | stacks.md puts the one-deployable API in `backend/`; in a Next.js app with `src/`, `src/**` covers the web app |
| A lock entry's `root` goes through the same check as `--package`'s path when read back | trusting the lock | repo data is read like input (recurring defect) |
| The "Every stack" principle bans an SSR layer, BFF, queue, distributed cache or new service until a measured need, or the scaling roadmap's trigger when the project has one | adding roadmap rows for each | brownfield has no roadmap page (B5 decision); the rule must stand without one |

## Acceptance criteria

- **AC-001** Given a `.claude/rules` folder that is a link to a folder outside the repo, when `scaffold.py
  conventions` renders, then it is refused and nothing is written outside the repo.
- **AC-002** Given a file that appears at the destination after the exists check, when the render publishes, then the
  file is not overwritten, the command is refused, and the lock holds no entry for it.
- **AC-003** Given a render killed after the lock is saved and before the file is written, when it runs again, then
  the convention is rendered.
- **AC-004** Given a lock that isn't a JSON object, or whose `files` isn't an object or `declined` isn't a list, when
  `conventions` or `upgrade-plan` runs, then it exits with error JSON naming the lock, not a traceback.
- **AC-005** Given a lock entry whose `root` is not a relative path inside the project (a list, `..`, absolute),
  then upgrade-plan skips it and `--seen` refuses it.
- **AC-006** Given `conventions node <area> --one-deployable`, then the rule's `paths:` keep only the template's
  `backend/` globs; for a stack whose template has none, it is refused with nothing written.
- **AC-007** (manual) The docs agree with the above:
  - the constitution's "Every stack" principle stands without a roadmap page;
  - upgrade.md's steps are numbered 1–11, with no "5a";
  - flow.md says when to pass `--one-deployable`;
  - the `libs.versions.toml` claim has a source (below).

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_stack_blueprints.py › Hardening.test_rules_folder_linked_outside_is_refused | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_rules_folder_linked_outside_is_refused` |
| AC-002 | tests/test_stack_blueprints.py › Hardening.test_file_appearing_mid_render_is_kept | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_file_appearing_mid_render_is_kept` |
| AC-003 | tests/test_stack_blueprints.py › Hardening.test_render_killed_before_the_write_reruns | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_render_killed_before_the_write_reruns` |
| AC-004 | tests/test_stack_blueprints.py › Hardening.test_lock_of_the_wrong_shape_is_an_error | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_lock_of_the_wrong_shape_is_an_error` |
| AC-005 | tests/test_stack_blueprints.py › Hardening.test_lock_root_is_checked_on_read | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_lock_root_is_checked_on_read` |
| AC-006 | tests/test_stack_blueprints.py › Hardening.test_one_deployable_keeps_backend_globs | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_one_deployable_keeps_backend_globs` |
| AC-007 | manual | wording in docs; read against the criteria in Review |

**Source for AC-007:** Gradle version catalogs live in `gradle/libs.versions.toml` (docs.gradle.org/current/userguide/version_catalogs.html; developer.android.com/build/migrate-to-catalogs).

## Must never break

- An existing rule file is never overwritten, and no convention takes an `sdlc-` name.
- A render that succeeds leaves the file in `declined` and its entry in `conventions`, exactly as before.
- Every other command that reads a well-formed lock behaves as before.
- The plugin stays Python stdlib only.

## Out of scope

- Following links in the other scaffold writers (`render`, `agents`): same class, not touched by the stack-blueprints change; a ticket.
- New scaling-roadmap rows.

## Review

- **Recommended and chosen:** code. It fired because the Public Surface isn't `- none` (`--one-deployable`). Not asked: low risk.
- **Verdicts:** built-in `code-review high --max-findings all`, rated here.
  - Round 1: `.sdlc/.work/findings/2026-11-15-m-convention-hardening/code-reviewer-r1.md` → FAIL — CR-02, CR-07 (high), plus CR-01, 03, 04, 06, 09 (bugs).
  - Round 2: `code-reviewer-r2.md` → PASS.
- **Fixed:**
  - CR-02 (high): a lock entry with `root: null` was accepted. Test: `test_lock_root_is_checked_on_read`.
  - CR-07 (high): a link to another drive gave exit 1 instead of the refusal. Test: `test_rules_folder_on_another_drive_is_refused`.
  - CR-01: the race rollback dropped the earlier lock entry. It now restores it (`test_file_appearing_mid_render_is_kept`).
  - CR-03: a lock entry marked `one_deployable` on a template with no `backend/` paths refused the whole upgrade plan. It is now that item's error.
  - CR-04: `--one-deployable` now drops `src/` globs instead of keeping only `backend/` ones, so node schema keeps `drizzle/**` and `drizzle.config.ts`. This departs from AC-006's wording, recorded as a deviation.
  - CR-06 and R2-04: any failure after the lock save rolls the lock back, and the no-hard-link fallback removes a partial file. Test: `test_failed_write_without_hard_links_leaves_no_file`.
  - CR-09: flow.md and s-track.md say a one-deployable app is two stacks, so `node` is named for its API.
  - In passing:
    - CR-08: `require_lock` sets the empty value;
    - CR-10, CR-11: dead code removed;
    - CR-05, R2-02, CR-12, R2-08: the changelog scope, the spec trace and upgrade.md's error sources are corrected;
    - R2-07: both write paths give the rule file 0644;
    - R2-12: a long test line is rewrapped;
    - R2-14: `--one-deployable` is refused with `--seen`;
    - CR-13: the root matrix is cut to `..` plus null.
  - Full suite: 594 tests OK on Python 3.10, run from Git Bash.
- **Correction to the round-2 report:** it lists R2-01 as "fixed now". On a closer look it is a ticket, below: in the reported scenario the other writer's entry is already lost at the second run's first save, so no rollback can restore it.
- **Tickets:**
  - R2-01: concurrent scaffold commands overwrite each other's lock (every command does an unlocked read-modify-write). Needs a lock file across scaffold.py.
  - R2-03: a kill in the middle of the no-hard-link fallback leaves a partial file that a rerun refuses. Telling it apart from a user's edit is a design choice.
  - R2-05: an entry that fails `convention_entry` is skipped silently in the upgrade plan.
  - R2-06: `require_lock` checks the container types, not their items (upgrade-plan's `set(declined)` with dict items predates this change).
  - R2-09: lock checks sit in several helpers; one loader would close the class, including `status` and `design`, which still read the lock unchecked.
  - R2-10: `_publish_new` repeats `_write_atomic`'s temp-file sequence.
  - R2-13: `.claude/rules` can be swapped for a link between the check and the write.
  - From the change's own out of scope: following links in `render` and `agents`.
  - R2-11 kept as it is: AC-004 names the three lock shapes its test loops over.
- **Drift and manual checks:**
  - Deviations: test-change (`declined` now gets require_lock's error JSON, exit 1); the helpers `convention_text`, `relative_root` and `_publish_new`; AC-006's `src/` behaviour; the r1 and r2 fix lines.
  - AC-007 (manual), each checked by reading the diff:
    - the "Every stack" principle names "a measured need" first and the roadmap only when one exists;
    - upgrade.md's steps run 0–11, with no 5a;
    - flow.md and s-track.md name `--one-deployable`;
    - the `libs.versions.toml` source is in this file.
- **Lessons filed:** None.
