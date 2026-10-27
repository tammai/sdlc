# Ship (Stage 8), with Learn

1. **Verified tree.** Run the core's check against `Verified:`. Anything left is unverified code: back to Build: rerun `verify.py` there (S, M lite and `Prove: skip` then go on to Ship), and on a feature with Prove, through Prove again (`state.py advance <f> 4`), before committing.
2. **Learn**, small, on every feature (S: only a lesson, when there is one; it has no `review.md`), before the commit so it lands in it (docs only, so the verified-tree check ignores it):
   - **Defects.** Read `## Fixed` in `<intents>/review.md`, which covers every slice. Each defect a reviewer could check next time, and not already listed, gets one line in `<docs>/recurring-defects.md`. Create the file from the shape in `recurring-defects.md` if needed. Define and every later reviewer read it.
   - **Lessons.** Only when the session found one that isn't obvious from the code, the commit or the design (a platform gotcha, say), never a feature summary or a restated decision: `sdlc:managing-knowledge` files it in the right tier, and `/sdlc:revise-claude-md` gathers candidates. Corrected twice and mechanically checkable → `/sdlc:hookify` (`sdlc:writing-hook-rules`). A constitution that changed in practice → `sdlc:project-constitution`. CLAUDE.md over 60 lines → the audit in `sdlc:managing-knowledge`. Nothing durable → nothing.
   - **L also:** `<intents>/retro.md` (3–5 bullets on what worked and what to change; history, not loaded later). Every promoted lesson is linked from `knowledge/index.md` or a tier-2 rule.
3. **Commit.** One commit for the feature on its branch (code, tests, docs, state), with `/sdlc:commit`; on the full flow with per-task commits, the rest. The commit-time security review runs on it. A finding that needs a code change goes back to Build: rerun `verify.py` there (S, M lite and `Prove: skip` then go on to Ship), and on a feature with Prove, through Prove again.
4. **Don't ask, on every track** (a backlog too): keeping the branch is the safe default. The commit is on a feature branch (step 3; create one named after the feature first if you're on the default branch), nothing is pushed or merged. End with one line: `Branch <name> kept (<commit>); say "merge" or "PR" to go further.` Merging, pushing, a PR and a deploy each wait for the user's word:
   - `sdlc:finishing-a-development-branch` handles them, and worktree clean-up, when asked.
   - `/sdlc:commit-push-pr` opens a PR. Its description links `spec.md`, `review.md` and, if a QA round ran, `qa-report.md`.
   - CI must be green before a merge. **Never merge without the user saying so.**
   - `/sdlc:clean_gone` prunes merged branches.
5. Once committed and reported: `state.py set <f> Status done`. Deploying is a separate request: `/sdlc:deploy`.

**Gate:** verified-tree check clean; Learn done; CI green before any merge the user asks for.
