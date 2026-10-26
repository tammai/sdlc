# Build (Stage 4)

- Isolation: `sdlc:using-git-worktrees` (L, or whenever the working tree is dirty).
- Always on: `sdlc:test-driven-development` (one failing test per behaviour, the code that passes it, then the full suite); `sdlc:systematic-debugging` the moment something fails unexpectedly.
- **By `Build:`:**
  - `native`: work through the spec's tasks (or the slice plan) in this session (`Flow: full`: with `sdlc:executing-plans`, told "Prove reviews the branch" so it skips its own final review, and its `Ruling:` lines logged with `state.py log`; Lite and slices load no execution skill). Make no state updates between tasks. Lite and slices make no commits here; the full flow may commit per task, never staging `.sdlc/`.
  - `subagent`: you keep the spec, state and gates. One fresh implementer (standard tier; S: cheap) gets the tasks, the slice plan or S's `intent.md`, using `sdlc:subagent-driven-development`'s `implementer-prompt.md`. It builds test first, runs the full suite and returns a short summary: files, tests, suite result, open issues. Tell it not to commit. Don't read the implementation. Prove's findings go back to that implementer (message it); only run the suite yourself.
  - `tasks`: `sdlc:subagent-driven-development`, with one implementer and one review per task. Tell it to skip its final whole-branch review ("Prove reviews the branch"), and record the `Ruling:` lines it reports with `state.py log`, so Prove sees them.
  - `sdlc:dispatching-parallel-agents` for truly independent tasks.
- **S:** the implementer's brief is `<intents>/intent.md` (a feature started earlier: `brief.md`). A failing test reproducing the bug comes first (a new test file is allowed), then the fix, then the full suite. Tell it: "stop with BLOCKED if the fix needs more than 3 files, touches auth, payments, secrets, PII or migrations, or the cause stays unclear". Don't write the fix in this session; with no subagent tool, do it here and say so. A BLOCKED for one of those reasons moves the feature to M: back to Define for a spec.
- Optional loop for a single well-specified task with a machine-checkable finish: `/sdlc:ralph-loop "<task>" --completion-promise "DONE" --max-iterations 15`.
- Background: the security-guidance hooks warn on risky edits; hookify rules (if any) enforce team rules.
- **Gate:** every task done; build and full test suite pass; no TODO without a ticket. Then `state.py advance <f> 5 --gate pass`.
