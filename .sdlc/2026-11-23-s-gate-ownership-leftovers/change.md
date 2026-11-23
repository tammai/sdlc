# Workbench review ownership: a deleted merged branch ends it, one remote lookup, subagent Stops at the root

## Why

From `.sdlc/todo.md`: "SubagentStop at a workbench root now resolves to the app repo and skips (reason 11); `_merged` costs grow with every done feature that listed a repo; a locally deleted feature branch keeps ownership — end review SG-L1..L3 of 2026-11-22-todo-lanes".

Proof (each test fails before the fix):
- SG-L3: after `gh pr merge --delete-branch` (or `git branch -D`), `_merged` finds no `refs/heads/<branch>` and the done feature owns the app repo's commits forever (AC-001).
- SG-L2: each done feature listing the repo re-resolves `origin/HEAD`, `origin/main`, `origin/master` on every check: 9 lookups for three features (AC-002).
- SG-L1: a SubagentStop whose session is the workbench root resolves to the app repo it edited, finds the session repo (the root) different and skips (reason 11), so build subagents' app edits get no turn-end review (AC-003).

## Decisions

- A branch gone from `refs/heads/` is judged by its last tip from HEAD's reflog (the commit HEAD left at `checkout: moving from <branch> to …`), with the same rule: past its base and in the remote's default branch. No reflog entry, or a tip not merged: still owned (fail closed). While the remote still has the branch (`origin/<branch>`), it must be merged too: HEAD's reflog misses commits made in another worktree (security review S-1). The tip is read from the checkout entry's own raw reflog line, so pruned neighbours don't matter. The reflog is local and the agent's to rewrite, the same trust as the branch ref the rule already reads (now named in docs/wiki/Limitations.md, S-3).
- The remote's default branch is resolved once per `_workbench_feature` call and shared by its features (no process-wide cache: a fetch during a session must count).
- A SubagentStop counts an app repo directly below a guarded workbench that is the session's folder as the session's own repo.

## Acceptance criteria

- **AC-001** A done feature's branch deleted locally ends ownership when its last tip is in the remote's default branch, and keeps it when that tip isn't, or when the remote's copy of the branch holds unmerged work.
- **AC-002** One ownership check resolves the remote's default branch at most once (three ref lookups) whatever the number of done features.
- **AC-003** A SubagentStop with the session at the workbench root reviews the app repo the subagent edited instead of skipping (reason 11).

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_workbench.py › PluginReviewWorkbench.test_a_merged_branch_deleted_locally_ends_ownership | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_a_merged_branch_deleted_locally_ends_ownership` |
| AC-002 | tests/test_workbench.py › PluginReviewWorkbench.test_the_remote_default_branch_is_looked_up_once_per_check | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_the_remote_default_branch_is_looked_up_once_per_check` |
| AC-001 | tests/test_workbench.py › PluginReviewWorkbench.test_a_deleted_branch_with_unmerged_work_on_the_remote_stays_owned | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_a_deleted_branch_with_unmerged_work_on_the_remote_stays_owned` |
| AC-003 | tests/test_workbench.py › StopReviewEveryRepo.test_a_subagent_stop_at_the_root_reviews_the_app_repo | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_a_subagent_stop_at_the_root_reviews_the_app_repo` |

## Must never break

- A done feature whose branch exists keeps today's rule (`test_a_done_feature_owns_its_app_repo_until_its_branch_is_merged`).
- A SubagentStop in another repo than the session's still skips (reason 11).

## Review

- **What fired:** a security review, because the risk is high: ownership decides whether app-repo commits get a security review. It ran on opus.
- **Round 1, PASS.**
  - S-1 (medium, a bug in this change): the reflog tip misses commits from another worktree. Fixed test first: the remote's copy of the branch must be merged too, and the tip is read from the checkout entry's own raw reflog line.
  - S-2 (a test gap): fixed; a SubagentStop outside the workbench still skips.
  - S-3: docs/wiki/Limitations.md now names the reflog.
- **Round 2, PASS** (closing check): every round-1 finding is gone. S-4 (low, a bug): a FIFO at `.git/logs/HEAD` would block the hook. Fixed test first: only a regular file is read, and only its tail.
- **Reports:** `.sdlc/.work/findings/2026-11-23-s-gate-ownership-leftovers/security-r1.md` and `security-r2.md`. No lesson filed.
