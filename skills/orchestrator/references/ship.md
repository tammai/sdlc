# Ship (Stage 8), with Learn

1. **Verified tree.** Review's gate just checked it; if code changed since, run the core's check against `Verified:`. Anything left is unverified code: back to Build, then Review.
2. **Learn, before the final commit**, so the knowledge lands in the change and the PR reviewer sees it (docs only, so the verified-tree check ignores it):
   - **Lessons.** Only when the change taught something not obvious from the code or the commit (a platform gotcha, a trap that cost time): `sdlc:managing-knowledge` files it in the right tier (CLAUDE.md, a path-scoped rule, or `knowledge/`), linked from `review.md`'s `## Lessons filed`. A feature summary or a restated decision is not a lesson. Corrected twice and mechanically checkable → `/sdlc:hookify`. Nothing to learn → say so in one line and write nothing.
   - **Defects.** Each high finding fixed in Review that a reviewer could check next time, and not already listed, gets one line in `<docs>/recurring-defects.md` (shape in `recurring-defects.md`).
3. **Green locally:** the last `verify.py` run must be on this exact code, after Learn's edits (`verify.py status` → `reuse: true`; Learn writes only docs, so Review's check usually still stands); otherwise run it, and anything red goes back to Build.
4. **Commit, push and open the PR in one shell call**, with git and `gh` directly (no `/sdlc:commit` or `/sdlc:commit-push-pr`): a branch named after the feature if you're on the default branch, then add code, tests, the record (`intent.md`, `spec.md`, `plan.md`, `review.md`), knowledge and state, commit, push, and `gh pr create`. The commit message names the record's path (`docs/sdlc/intents/<f>/`), so `git blame` leads from a line to its why; the PR description links `intent.md`, `spec.md` and `review.md`. No remote: commit only and stop with the branch ready.
5. **Watch CI** for the pushed commit (`gh pr checks --watch`, or the provider's equivalent).
   - Red because of the code: fix it once, with a failing test first, rerun `verify.py`, commit and push again.
   - Still red after that fix, or red for a reason in CI itself (a missing secret, a runner problem, a flaky test): stop and tell the user what failed. Never change code to work around a CI problem.
6. **Stop at the PR.** The final message is a few lines: what changed, the test result, the branch and commit, then `PR <url> open, local and CI green; say "merge" to merge.` (without a remote: the branch is ready). Merge only when the user says so; then `finishing-a-development-branch.md` (worktree clean-up too), and `/sdlc:clean_gone` prunes merged branches when asked.
7. Once reported: `state.py set <f> Status done`. The state file then differs from the commit; that's expected and rides with the next commit. Deploying is a separate request: `/sdlc:deploy`.

**Gate:** verified-tree check clean; Learn done; local and CI green, or the user told what's red; PR open, or the branch ready without a remote.
