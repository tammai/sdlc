# Skills and agents

## Skills (`sdlc:` namespace)

| Group | Skills |
|---|---|
| Conductor | `orchestrator` |
| Set up | `setting-up-projects` (setup, upgrade, eject; its `references/trimming-context.md` backs `/sdlc:context-diet`) |
| Define | `brainstorming` (the interview on L, unless a written spec settles the design), `project-constitution` |
| Build | `test-driven-development`, `systematic-debugging` |
| Check | `verification-before-completion` (the review entry points are Review, `/sdlc:review-pr` and `/sdlc:code-review`) |
| Ship and learn | `managing-knowledge` (with the CLAUDE.md quality check that was `claude-md-improver`), `hookify` (with the rule syntax that was `writing-hook-rules`), `todo` |
| Orchestrator references (read when the flow needs them, not skills) | `using-git-worktrees.md`, `dispatching-parallel-agents.md`, `receiving-code-review.md`, `finishing-a-development-branch.md` |

## Subagents

| Agent | Used for |
|---|---|
| `code-explorer` | Brownfield setup's audit: trace existing code |
| `code-reviewer` | Review: the code review (one full depth) with the shared reviewer brief; the security review with the security-only brief |
| `ui-reviewer` | Review, when the diff touches UI files: design-system conformance, AI-slop styling, states, accessibility; screenshots on request |
| `qa-tester` | On request: runs the feature as a user would, without reading the code |
| `pr-test-analyzer`, `silent-failure-hunter` | `/sdlc:review-pr`, chosen by the diff |
| `sdlc-extras:comment-analyzer`, `sdlc-extras:type-design-analyzer`, `sdlc-extras:code-simplifier` | `/sdlc:review-pr`, chosen by the diff, when the `sdlc-extras` plugin is installed (skipped, and said so, otherwise) |
| `sdlc-extras:conversation-analyzer` | `/sdlc:hookify`: find behaviors worth preventing with hooks, when `sdlc-extras` is installed (otherwise the session does the analysis) |
