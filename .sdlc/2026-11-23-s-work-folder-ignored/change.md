# sdlc's working folder is ignored from setup's first step

## Why

**Request (verbatim):** "Fix all 6, then release", applied to what the 3.15.0 smoke test (part G) then found: "The first setup commit (e8ba52b, "detect, stack, commands") adds `.sdlc/.work/trust-anchor.json`. The later gitignore step deletes it from git, so it stays in history."

**Proof:** `tests/test_trust_anchor.py` › `test_the_first_record_in_a_new_work_folder_is_never_committed` fails: the trust anchor's first record (`sdlc_scopes.write_record`) creates `.sdlc/.work/` and shows in `git status`.

**Root cause:** setup adds `.sdlc/.work/` to the repo's `.gitignore` in its `gitignore` step, after the steps that commit; hooks write their records there from the first tool call after `init`.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| `sdlc_scopes.write_record`, when it creates `.sdlc/.work/` itself, writes a `.gitignore` of `*` inside | `init` writing it (first try: it broke the rule that init creates no scratch, `test_init_creates_no_scratch`, and masked doctor's .gitignore check); moving the gitignore step first | the hooks' records are what land before the gitignore step; a folder that already exists is left alone |

## Acceptance criteria

- **AC-001** The first record written into a new `.sdlc/.work/` doesn't show in `git status`, while `.sdlc/config.json` does; an existing folder gets no `.gitignore`.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_trust_anchor.py › WorkFolderTest.test_the_first_record_in_a_new_work_folder_is_never_committed | `python3 -m unittest discover -s tests -t tests -p test_trust_anchor.py -k test_the_first_record_in_a_new_work_folder_is_never_committed` |

## Must never break

- `init` creates no scratch (`test_init_creates_no_scratch`); doctor's .gitignore check; the trust anchor's tests.

## Out of scope

- The generated CI failing on a brownfield repo's baselined tests (a known limitation in the 3.15.0 notes).

## Review

No review ran: no trigger fired.
