# Base fixes that fit their cause

## Why

**Request (verbatim):** "continue", after I suggested the todo item: "Drift after a rebase onto, or a merge of, a newer main: the old `Base:` stays an ancestor of HEAD, so drift is diffed two-dot from it and counts every upstream change as the feature's".

**What it became:** four review rounds showed that verify can't safely find where a branch forks. Each version read a ref the agent can move (`main`, `origin/main`), and each round faked one so that drift, or the advice, would hide the feature's own commits. At the round cap the user chose to drop the detection. Kept from those rounds are the bugs they found in the base checks #152 and #153 added, and a Troubleshooting entry (R16a) on moving `Base:` by hand.

**Proof:** each criterion's test fails on #153's `scripts/verify.py` and `scripts/diff_stats.py`.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| Drift counts from `Base:`; after taking in a newer main, the user moves `Base:` (Troubleshooting R16a), which the trust anchor shows | measuring drift from the fork point (round 1); naming it (rounds 2, 3); a note without a sha (round 4) | every ref the fork point is read from is the agent's to move: `git branch -f main HEAD` hid committed files, and `main` at `HEAD~1` put the named point on the feature's own work. The user chose to drop it |
| `base_missing`'s fix fits its cause: the full sha for an ambiguous id; `--unshallow` only in a shallow clone; else a fetch from the remote that has it, or the re-record fix when none does | one fix for every cause; `git fetch origin` | `--unshallow` fails on a complete clone; a remote may not be called `origin` |
| An app repo's base is corrected only after asking the user | hand-editing `## Repos` | the trust anchor doesn't show that line |
| Only an app repo git failed to diff is `drift_unchecked` (`scan_errors`); a branch line sdlc leaves alone isn't | every `not scanned` flag | `repo_failures` already reports that line, and the root's drift should still count |
| git's checks run in the C locale | the user's locale | the error text is matched in English |
| A short id a commit and a blob share fails closed with git's own message (`drift_unchecked`) | resolving `Base:` to its full sha (round 5 found it partial; the user chose to drop it) | very rare, and a full resolution touches every diff, app repos' included |
| Stacked on #153 | branching from main | it changes the code #152 and #153 add |

## Acceptance criteria

- **AC-001** A `Base:` missing from a complete clone gets the fix to fetch it from the remote that has it, or to re-record it, not `--unshallow`.
- **AC-002** An ambiguous short `Base:` gets the full-sha fix, not a fetch.
- **AC-003** An app repo's `base_not_ancestor` fix says to ask the user before its `## Repos` base changes.
- **AC-004** Only a repo git failed to diff is `drift_unchecked`; a branch line sdlc leaves alone isn't.
- **AC-005** git's checks run with `LC_ALL=C`.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_verify.py › VerifyTest.test_a_base_commit_missing_from_the_clone_fails_with_a_message_not_a_traceback | `python3 -m unittest discover -s tests -t tests -p test_verify.py -k test_a_base_commit_missing_from_the_clone_fails_with_a_message_not_a_traceback` |
| AC-002 | tests/test_verify.py › VerifyTest.test_base_missing_gives_the_fix_that_fits_the_cause | `python3 -m unittest discover -s tests -t tests -p test_verify.py -k test_base_missing_gives_the_fix_that_fits_the_cause` |
| AC-003 | tests/test_workbench.py › PluginReviewWorkbench.test_an_app_repos_base_no_longer_behind_its_head_fails_drift | `python3 -m unittest discover -s tests -t tests -p test_workbench.py -k test_an_app_repos_base_no_longer_behind_its_head_fails_drift` |
| AC-004 | tests/test_workbench.py › PluginReviewWorkbench.test_a_branch_line_sdlc_leaves_alone_doesnt_stop_the_roots_drift | `python3 -m unittest discover -s tests -t tests -p test_workbench.py -k test_a_branch_line_sdlc_leaves_alone_doesnt_stop_the_roots_drift` |
| AC-005 | tests/test_verify.py › VerifyTest.test_gits_checks_run_in_the_c_locale | `python3 -m unittest discover -s tests -t tests -p test_verify.py -k test_gits_checks_run_in_the_c_locale` |

## Must never break

Each guard passes before and after this change:

- After a rebase onto or a merge of a newer main, the upstream file is drift, and moving `Base:` to the fork point clears it (`tests/test_verify.py` › `test_after_taking_in_a_newer_main_moving_base_clears_upstream_drift`).
- Moving `main` onto the feature, whole or in part, never hides its committed drift (`test_moving_main_onto_the_feature_never_hides_its_committed_drift`, `test_a_main_holding_some_feature_commits_never_names_one`).
- On the default branch, a file committed after `Base:` is drift (`test_on_the_default_branch_drift_still_counts_from_base`).

## Out of scope

- Finding the fork point automatically (dropped: see Why).
- Several missing bases reported one per run (todo).

## Review

- Fired: code review (the Public Surface changed). Built-in `code-review` at high, all findings.
- Round 1: FAIL. High: measuring drift from the fork point let a moved `main` hide committed files. Changed to a note that names the fork point.
- Round 2: FAIL at the cap. Highs: the note could name HEAD; an app repo's fix said to hand-edit `## Repos`. The user chose one more round. Fixed: refs holding HEAD skipped, app-repo fixes ask the user, dropped branch lines no longer stop drift, fixes fit their cause.
- Round 3: FAIL. High: a `main` holding some feature commits made the named point a feature commit. The user chose a note without a sha.
- Round 4: FAIL. High: the note's claim itself could be faked. The user chose to drop the detection. Kept: the base-check fixes, Troubleshooting R16a, the C locale, the re-record fix.
- Round 5: FAIL. High: the full-sha resolution was partial. The user chose to drop it, so the change only shrank, and no round 6 ran (`waived round 5` deviation).
- Lessons: none filed. The rounds showed that verify can't trust any ref the agent can move. The spec's Known gaps records that.
