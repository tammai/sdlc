# The turn-end review covers every workbench repo a turn edited

## Why

From `.sdlc/todo.md`: "A turn that edits several app repos of a workbench gets the turn-end review in only the busiest one; review each (design in the lane C report of 2026-11-22-todo-lanes: a `hooks/stop_repos.py` module and one combined review call; about 130 lines of the vendored `handle_stop_hook` move into a function)".

Proof: a turn at the workbench root that writes `api/a.py` and `web/b.py` sends the reviewer only `api`'s file (AC-001's test fails); a turn from inside `api` that edits only `web` sends nothing (AC-003). Root cause: `handle_stop_hook` resolves one repo (`reporesolve.resolve_repo_root`) and diffs only it; the workbench's `.gitignore` hides the other app repos from that diff, and every "nothing to review here" exit (skip 51, 9, 8, 7, 6, 12) ends the hook.

## Decisions

- `hooks/stop_repos.py` (outside the vendored file) finds the other repos the turn's edit tools touched in the same guarded workbench (its root or an app repo one level below it), asks `sdlc_review_gate.review_wanted` for each, and diffs each wanted one from the time the turn began (the stored baseline belongs to the first repo): `_git_head_at` at the prompt time, `since_ns`, as the hook already does for a foreign baseline.
- Every file is named by its path from the session's cwd (`api/a.py` and `web/b.py` from the workbench root; `a.py` and `../web/b.py` from inside `api`), so the agent opens each name as written and no two repos' files share a name in one review; the repo the session sits at the top of keeps bare names, as its own one-repo and commit reviews give them. Findings are stored under the names shown. A later review from another cwd, or a one-repo review, may name a file differently and repeat a finding once: noise, never a hidden finding (code review r3 CR3-5, CR3-6). Ruled out: repo-relative stored names (r1; they collide across repos, r2 CR2-1) and workbench-relative names (r2; they read wrongly from inside an app repo, r3 CR3-6).
- The other repos come from every path the turn touched (`turn_touched`, kept across rewakes until the next prompt), and a rewake diffs them again from the turn's start: more tokens, and a file the cap cut is sent again on a rewake (r3 CR3-1, CR3-2); with no rewake it isn't, as for the first repo's own cut files, and the count goes to the `other_dropped` metric (r4). A rewake also re-sends another repo's code the agent left as it was after a finding, so a declined finding there may be raised again, at most up to the rewake cap (3) (r4, accepted: the price of never losing a cut file). Ruled out: remembering the last review's time (`other_reviewed_at`, r1 CR1-2's fix), which skipped files the caps had cut.
- The first repo's files come first under `MAX_DIFF_FILES`: its baseline moves past them after findings, so they must not be cut for the others (r3 CR3-3); the other repos fill the slots left, ranked by their repo-relative paths, so a folder named `api` or `auth` doesn't outrank the rest (CR3-4).
- A review of only the other repos (the first repo had nothing) never moves the first repo's baseline (r1 CR1-3). With no turn-start time a repo is skipped, and a repo past the first repo's size limits (reviewable source paths, diff files) is left out (r1 CR1-4, CR1-5; r2 CR2-10). A session in a repo's subfolder still finds the other repos (r2 CR2-4).
- Pre-turn uncommitted hunks inside a file this turn edited in another repo are sent too: those repos have no turn-start snapshot, the same rule the hook already follows for a baseline from another checkout (CR1-4, the rest). Ruled out: a stash per member at every prompt.
- Only repos the edit tools touched are found; a repo changed only through Bash isn't (CR1-6, worded so in CHANGELOG and NOTICE).
- One review call per Stop, as today (the emit and `last_review_failed` handle one review): the first repo's files and the others' together, under `MAX_DIFF_FILES` with the existing prioritising.
- In the vendored `handle_stop_hook`, the review-and-verdict tail becomes the nested `_review_and_exit(diff_files)`, unchanged but for indentation, and each "nothing to review in the first repo" exit becomes `_skip_or_other`: it skips with the same reason when no other repo has files, else reviews those. The other repos are read once, after the first repo's own diff, so its skip reasons stay its own. Ruled out: moving the first repo's part into a function (more lines moved, same effect).
- Not for SubagentStop, which keeps the single-repo path; not outside a workbench (a plain repo with a nested repo keeps one review).

## Acceptance criteria

- **AC-001** A turn at the workbench root that edits `api` and `web` sends both repos' files, each named by its path from there, in one review call.
- **AC-002** A turn from inside `api` that also edits `web` sends both.
- **AC-003** When the first repo has nothing to review, the other repos the turn edited are still reviewed.
- **AC-004** Only repos the review gate wants are added.
- **AC-005** A plain repo with a nested repo adds no other repo; a turn that edits one repo sends only that repo.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_workbench.py › StopReviewEveryRepo.test_a_turn_at_the_root_reviews_every_app_repo_it_edited | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_a_turn_at_the_root_reviews_every_app_repo_it_edited` |
| AC-002 | tests/test_workbench.py › StopReviewEveryRepo.test_a_turn_inside_one_app_repo_also_reviews_another_it_edited | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_a_turn_inside_one_app_repo_also_reviews_another_it_edited` |
| AC-003 | tests/test_workbench.py › StopReviewEveryRepo.test_a_first_repo_with_nothing_to_review_still_reviews_the_other | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_a_first_repo_with_nothing_to_review_still_reviews_the_other` |
| AC-004 | tests/test_workbench.py › StopReviewEveryRepo.test_only_repos_the_review_gate_wants_are_added | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_only_repos_the_review_gate_wants_are_added` |
| AC-005 | tests/test_workbench.py › StopReviewEveryRepo.test_a_plain_repo_with_a_nested_repo_adds_nothing | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_a_plain_repo_with_a_nested_repo_adds_nothing` |

`StopReviewEveryRepo.test_a_turn_in_one_repo_sends_only_that_repo` covers AC-005's second half; it passes before and after (no red).

## Must never break

- A turn that edits one repo goes through the same path, with the same skip reasons and the same request, as before.
- The hook never blocks on its own error: an error reading the other repos reviews the first repo alone.

## Out of scope

- Several stored baselines: after a fire with findings, the other repos are diffed again from the turn's start on the next fire (more tokens, nothing missed).
- Repos changed only through Bash: only paths the edit tools recorded find another repo.

## Review

- **What fired:** code review, because the diff is large (more than 300 added lines, mostly the vendored tail re-indented). Risk low, so it wasn't asked. It ran as the built-in `code-review high --max-findings all`, and I rated each finding.
- **Round 1, FAIL:** CR1-1 to CR1-4 were medium bugs: one file under two names, rewake re-diffs, the first repo's baseline moved by an other-repos-only review, pre-turn work. All were fixed test first. CR1-5 to CR1-8 were low and fixed.
- **Round 2, FAIL (highs):** CR2-1 (repo-relative stored names collide across repos), CR2-4 (a session in a subfolder), CR2-5 (an unguarded import), CR2-7 (capped files never sent again). These were past the cap. The user chose one more fix round, and the fixes went in test first.
- **Round 3, FAIL (highs):** CR3-1 to CR3-3 came from the rewake "skip what was reviewed" optimisation; CR3-6 was workbench-relative names read wrongly from inside an app repo. The user chose to simplify rather than patch. The optimisation is dropped, the first repo's files come first under the cap, and names are paths from the session's cwd.
- **Round 4, PASS:** no high. CR4-2 (turn_touched trimming) and the low items CR4-3 to CR4-7 are fixed. CR4-1 (a declined finding in another repo may be raised again on a rewake, up to 3) is accepted in Decisions and ticketed in `.sdlc/todo.md`.
- **Reports:** `.sdlc/.work/findings/2026-11-23-m-stop-review-every-repo/code-reviewer-r1.md` to `-r4.md`.
- **Tests:** full suite 786 OK on Python 3.10, every AC red then green (`verify.py`, re-red at Base after each test change).
- **Drift:** recorded in the state file's Deviations: the stop_repos functions as unlisted surface, diffstate, CONTRIBUTING, and the test changes.
- **Lessons filed:** [The turn-end review's session state and how to test it](../../knowledge/gotchas/stop-review-session-state.md).
