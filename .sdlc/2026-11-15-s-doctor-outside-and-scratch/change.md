# Doctor reports files outside the repo; the scratch folder is used only once it exists

## Why

**Request:** the user's goal, "get job done unattend": the fixable tickets PR #60 left open in
`.sdlc/2026-11-15-m-config-merge-and-containment/change.md` ## Review.
- CC-10/CC2-08: `doctor` counts a file in the `outside` state as tracked and ok.
- CC-07: `init`'s first lock save creates `.sdlc/.work/` before setup's gitignore step adds its line, so a kill at that moment leaves a temp copy in a folder git would commit.
- CC-13/CC2-14: every save and every `file_state` call resolves the repo root and globs folders again.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| The lock and config use `.sdlc/.work/` for temp copies only when the folder already exists; otherwise the temp goes beside the file, as before PR #60 | creating it, or writing `.sdlc/.work/.gitignore` | setup's gitignore step, or the first scratch file, creates it; no new file in the user's tree |
| `doctor` warns, listing the files that resolve outside the repo, with the fix "upgrade and eject skip them; remove the link or untrack them" | an error | they're kept safely; the user should only know |
| `inside_repo` caches the root's real path per process, and the sweep of a folder runs once per process | leaving it as it is | `status` runs at every session start, and its cost grows with the number of tracked files |

## Acceptance criteria

- **AC-001** Given a tracked file that resolves outside the repo through a link, then `doctor`'s plugin-files check warns and names it.
- **AC-002** Given a repo with no `.sdlc/.work/`, when `init` saves the lock, then `.sdlc/.work/` isn't created.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_doctor.py › DoctorTest.test_outside_files_warn | `py -3.10 -m unittest discover -s tests -t tests -p test_doctor.py -k test_outside_files_warn` |
| AC-002 | tests/test_stack_blueprints.py › ConfigAndContainment.test_init_creates_no_scratch | `py -3.10 -m unittest discover -s tests -t tests -p test_stack_blueprints.py -k test_init_creates_no_scratch` |

## Must never break

- A healthy repo's `doctor` report is unchanged.
- Saves stay atomic, and their temp copies still go in `.sdlc/.work/` once it exists.

## Out of scope

- Windows protection set only through ACLs (LM3-08): the standard library can't see it, so it stays a documented platform limit.
- The config merge sharing code with the lock merge (CC2-12), and the config re-read's place in `save` (CC2-06): cleanup, no behaviour change.

## Review

No review ran: no trigger fired (S, low risk, no public surface).
