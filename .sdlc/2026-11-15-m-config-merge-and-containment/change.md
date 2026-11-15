# Config merges like the lock, scaffold's temp files stay in scratch, and one inside-the-repo check

## Why

**Request:** the user's goal, "get job done unattend", after "fix them": the tickets PR #59 left open in
`.sdlc/2026-11-15-m-lock-merge-and-tickets/change.md` ## Review.

- LM3-10: `config.json` is written whole when a command changed it, so two commands editing different config keys at once lose one edit.
- LM3-05: a kill mid-save leaves `.sdlc/.sdlc-tmp-*`, a copy of the lock or config, beside them, where it can be committed.
- LM2-01 and LM2-13: `status` and `upgrade-plan` still read a lock path through a link out of the repo (a link to `/dev/zero` hangs the session-start hook), and `render` writes through one. The inside-the-repo check exists in three copies.
- LM2-09: lists of objects merge by equality, which would duplicate an item both commands edited (config's `packages` is one).

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| `config.json` merges the way the lock does: re-read at save, this command's changes applied onto the file as it is now, key by key | a mutex; leaving it whole | the user chose detect-and-merge for the lock; config gets the same mechanism |
| A list holding objects merges whole: this command's version wins if it changed it | merging by item | an edited object isn't equal to its old self, so a by-item merge keeps both copies |
| The temp file for a save of `.sdlc/scaffold.lock.json` or `.sdlc/config.json` is created in `.sdlc/.work/`, the gitignored scratch folder, then renamed into place | beside the file (today) | a kill leaves it where it is never committed; same filesystem, so the rename is still atomic |
| One helper, `inside_repo(root, path)`, decides whether a path resolves inside the repo after links. `file_state` reports `outside` without reading the file; `upgrade-plan` lists such files under `outside`; `render` refuses to write one; eject and conventions use the same helper | a fourth copy | the class keeps coming back while every reader has its own copy |

## Acceptance criteria

- **AC-001** Given two commands that read `config.json` and then save different keys, then the file holds both; and given both changed `packages`, then it holds one command's whole list, with no duplicate entry.
- **AC-002** Given a lock or config save killed before its rename, then no temp copy is left in `.sdlc/` itself, only in `.sdlc/.work/`.
- **AC-003** Given a lock path whose folder links out of the repo, then `status` reports it `outside` without reading it, `upgrade-plan` lists it under `outside`, and `render` to it is refused with nothing written.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_stack_blueprints.py › ConfigAndContainment.test_config_saves_merge | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_config_saves_merge` |
| AC-002 | tests/test_stack_blueprints.py › ConfigAndContainment.test_save_temp_stays_in_scratch | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_save_temp_stays_in_scratch` |
| AC-003 | tests/test_stack_blueprints.py › ConfigAndContainment.test_links_out_are_not_followed | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_links_out_are_not_followed` |

## Must never break

- A save with no concurrent change writes what it wrote before, and both files keep their format.
- `render`, `status` and `upgrade-plan` behave as before for every path inside the repo.
- The plugin stays Python stdlib only.

## Failure modes

- Concurrent use: AC-001.
- A crash mid-write: AC-002.
- Untrusted repo data naming a path: AC-003.

## Out of scope

- Windows ACL-only protection that `os.access` can't see (LM3-08), and retrying a permanent permission error (LM3-07): platform limits, left as tickets.
- Two concurrent renders of one convention without hard links (LM3-03), and a merge left in memory after a failed write (LM3-04): rare and latent.

## Review

- **Recommended and chosen:** code. It fired because the change file names concurrent use, a crash mid-write and untrusted repo paths as failure modes. Not asked: low risk.
- **Verdicts:** built-in `code-review high --max-findings all`, rated here; reports in `.sdlc/.work/findings/2026-11-15-m-config-merge-and-containment/`.
  - `code-reviewer-r1.md` → FAIL — CC-01 high, plus bugs.
  - `code-reviewer-r2.md` → PASS. Its mediums were fixed with tests and closed by `verify.py`, without another round.
- **Fixed (tested):**
  - **AC-001:**
    - `config.json` merges onto the file as it is now;
    - a list of objects merges whole, and lands in the object this command holds (CC2-11);
    - a config removed, broken or read-only meanwhile stops the save before either file is written (CC-04, CC-05, CC2-04).
  - **AC-002:**
    - the lock's and config's temp copies go in `.sdlc/.work/`;
    - an earlier version's leftovers beside them are swept (CC-06);
    - a scratch folder on another device, unwritable, or with a file in its place falls back to a temp beside the file (CC-08, CC2-05).
  - **AC-003:** `inside_repo` is the one check, so a file reached through a link out is never read, written or deleted.
    - `file_state` reports `outside`, and `status`, `upgrade-plan` and eject list it.
    - `render` and `record` refuse it (CC-02).
    - A design swap keeps an outside guardrail (CC-01).
    - `agents_state` never reads an outside mirror (CC2-02), and a removed host keeps the outside mirror's lock entry (CC2-09).
    - `upgrade-plan` checks for outside paths before `template_gone` and for new files in `add` (CC2-01, CC2-03).
  - Full suite: 607 tests OK on Python 3.10, run from Git Bash. One earlier run hung once after `test_autopilot`; it didn't happen again on a rerun.
- **Tickets:**
  - CC-07: `init`'s first save creates `.sdlc/.work/` before setup's gitignore step adds its line.
  - CC-10, CC2-08: doctor doesn't report the `outside` state.
  - CC-13, CC2-14: `inside_repo` resolves the root on every call, and each save globs twice.
  - CC2-06: the config re-read sits earlier in `save`, which widens the gap for a lost update.
  - CC2-12: the config merge repeats `merged_lock`.
  - Also carried over: Windows ACL-only protection (LM3-08) and retrying a permanent permission error (LM3-07).
- **By design:**
  - a list of objects both commands changed keeps the last writer's list (CC-03);
  - a deliberate link from a plugin file to a shared folder outside the repo is now skipped by upgrade and refused by `render` (CC-11);
  - a new lock is written in the checked shape, with `declined: []` (CC2-07).
- **Drift and manual checks:**
  - Deviations: the helpers, the docs, the r1 and r2 fix lines.
  - `upgrade.md`'s new Outside step renumbered the steps after it; nothing refers to them by number.
- **Lessons filed:** None.

