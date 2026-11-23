# sdlc's working folder is ignored from setup's first step

## Why

**Request (verbatim):** "Fix all 6, then release", applied to what the 3.15.0 smoke test (part G) then found: "The first setup commit (e8ba52b, "detect, stack, commands") adds `.sdlc/.work/trust-anchor.json`. The later gitignore step deletes it from git, so it stays in history."

**Proof:** `tests/test_scaffold.py` › `test_the_work_folder_is_ignored_from_setups_first_step` fails: after `scaffold.py init`, a file the trust anchor writes in `.sdlc/.work/` shows in `git status`.

**Root cause:** setup adds `.sdlc/.work/` to the repo's `.gitignore` in its `gitignore` step, after the steps that commit; hooks write their records there from the first tool call after `init`.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| `init` writes `.sdlc/.work/.gitignore` with `*`, never through a link | moving the gitignore step first; each writer of `.work` adding it | one write at the start covers every hook and script, whatever order setup runs in |

## Acceptance criteria

- **AC-001** After `scaffold.py init`, a file in `.sdlc/.work/` doesn't show in `git status`, while `.sdlc/config.json` does.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_scaffold.py › ScaffoldTest.test_the_work_folder_is_ignored_from_setups_first_step | `python3 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_the_work_folder_is_ignored_from_setups_first_step` |

## Must never break

- The rest of test_scaffold: init's config and lock, `--force`, eject.

## Out of scope

- The generated CI failing on a brownfield repo's baselined tests (a known limitation in the 3.15.0 notes).

## Review

No review ran: no trigger fired.
