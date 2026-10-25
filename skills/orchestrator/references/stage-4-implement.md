# Stage 4 · Implement

- Isolation: `sdlc:using-git-worktrees` (L track, or whenever the working tree is dirty)
- Execution, as picked at Stage 3: `sdlc:subagent-driven-development` (default for L), `sdlc:executing-plans` (native), or `Build: subagent` (the core's rule); `sdlc:dispatching-parallel-agents` for truly independent tasks.
- One whole-branch review per feature, in Stage 6: tell the execution skill to skip its own final whole-branch review ("Stage 6 reviews the branch"). Per-task reviews still run. Record the `Ruling:` lines it reports with `state.py log`, so Stage 6 sees them.
- Always on: `sdlc:test-driven-development`; `sdlc:systematic-debugging` the moment something fails unexpectedly
- Optional loop for a single well-specified task with a machine-checkable finish: `/sdlc:ralph-loop "<task>" --completion-promise "DONE" --max-iterations 15`
- Background: the security-guidance hooks warn on risky edits; hookify rules (if any) enforce team rules
- **S track:** no plan file. If the expected behaviour isn't clear from the request, ticket or a repro, ask the core's blocking questions once first; write the answers and your assumptions into the brief. Dispatch one implementer on the implementer tier (`sdlc:subagent-driven-development`'s `implementer-prompt.md`, with a brief file you write in place of a plan task): the bug and the expected behaviour; a failing test reproducing the bug first (a new test file is allowed), then the fix, then the full suite; on UI work, the UI mapping line from the Gate log; and "stop with BLOCKED if the fix needs more than 3 files, touches auth, payments, secrets, PII or migrations, or the cause stays unclear". Don't write the fix in this session; with no subagent tool, do it here and say so. A BLOCKED for one of those reasons moves the feature to M.
- **Gate:** every plan task checked; build + full test suite pass; no TODO without a ticket. Then `state.py advance <f> 5 --gate pass`.
