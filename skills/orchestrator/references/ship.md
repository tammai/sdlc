# Ship (Stage 8), with Learn

1. **Verified tree.** Run the core's check against `Verified:`. Anything left is unverified code: back to Prove (`state.py advance <f> 5`) before committing.
2. **Learn**, small, on every feature (S: only a lesson, when there is one; it has no `review.md`), before the commit so it lands in it (docs only, so the verified-tree check ignores it):
   - **Defects.** Read `## Fixed` in `<intents>/review.md`, which covers every slice. Each defect a reviewer could check next time, and not already listed, gets one line in `<docs>/recurring-defects.md`. Create the file from the shape in `recurring-defects.md` if needed. Define and every later reviewer read it.
   - **Lessons.** Only when the session found a durable one (a gotcha, a decision, a convention): `sdlc:managing-knowledge` files it in the right tier, and `/sdlc:revise-claude-md` gathers candidates. Corrected twice and mechanically checkable → `/sdlc:hookify` (`sdlc:writing-hook-rules`). A constitution that changed in practice → `sdlc:project-constitution`. CLAUDE.md over 60 lines → the audit in `sdlc:managing-knowledge`. Nothing durable → nothing.
   - **L also:** `<intents>/retro.md` (3–5 bullets on what worked and what to change; history, not loaded later), and `knowledge/features/<feature>.md` linking spec, design and retro. Every promoted lesson is linked from `knowledge/index.md` or a tier-2 rule.
3. **Commit.** One commit for the feature on its branch (code, tests, docs, state), with `/sdlc:commit`; on the full flow with per-task commits, the rest. The commit-time security review runs on it. A finding that needs a code change goes back to Prove.
4. **S, and M on `Flow: lite`: don't ask.** The commit is on a feature branch (step 3; create one named after the feature first if you're on the default branch), nothing is pushed or merged. Report it in one line: branch, commit, and that push, PR and merge are the user's to ask for. Ask only when the user wants a push, a PR, a merge or a deploy.
   **M on `Flow: full`, and L (a backlog too, whatever its flow): ask** about merge, PR or keep. This is a hard stop.
   - `sdlc:finishing-a-development-branch` handles the choice and worktree clean-up.
   - `/sdlc:commit-push-pr` opens a PR. Its description links `spec.md`, `test-report.md` and, if a QA round ran, `qa-report.md`.
   - CI must be green before a merge. **Never merge without the user saying so.**
   - `/sdlc:clean_gone` prunes merged branches.
5. Once committed and reported (S, M lite), or once the user has answered (M full, L): `state.py set <f> Status done`. Deploying is a separate request: `/sdlc:deploy`.

**Gate:** verified-tree check clean; Learn done; CI green before any merge.
