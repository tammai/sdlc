# Stage 8 · Commit, PR, CI

- First the core's verified-tree check against `Verified:`; anything left is unverified code: back to Stage 5 for a round before committing or opening the PR.
- `sdlc:finishing-a-development-branch` to decide merge/PR/keep and clean up worktrees
- `/sdlc:commit` or `/sdlc:commit-push-pr`; `/sdlc:clean_gone` to prune merged branches
- PR description links spec.md, test-report.md and, if a QA round ran, qa-report.md.
- **Gate:** CI green. **Never merge without the user saying so.** Done without Stage 9–11: `state.py set <f> Status done`.
