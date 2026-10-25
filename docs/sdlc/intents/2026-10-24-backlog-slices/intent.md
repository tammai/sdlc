# Intent: backlog slices and the intent interview

Status: confirmed · 2026-10-24 · revised 2026-10-25 (rows 7, 11–14 and the summary's last sentence; the spec follows the revision)

## Summary (confirmed by the user)

A large feature today runs start to end in one session: it takes hours, the context grows, limits hit and tokens are wasted. Planning should break the work into a backlog of vertical slices that the user, or an agent, drives one at a time, so work can pause, stop and `/clear` between slices. Discover should ask only the questions that block the work, in one message, and list everything else as assumptions confirmed with the spec. (Revised 2026-10-25; was: one question at a time.)

## Answers

| # | Topic | Question | Answer |
|---|---|---|---|
| 1 | Scope | What is one backlog item? | A vertical slice with its own lifecycle: plan, implement, verify, review, commit. |
| 2 | Plan timing | When does a slice get its detailed task plan? | Just-in-time, when the slice starts, in a fresh session. Planning writes only `backlog.md`. |
| 3 | Trigger | When does planning make a backlog? | By size estimate: more than about one session (~8–10 tasks, or several distinct parts). S never; M sometimes; L usually. |
| 4 | Landing | How does a slice land? | As verified, reviewed commits on the one feature branch. Security and the single PR run once after the last slice. |
| 5 | Feature close | Whole-feature checks after the last slice | A final verify round over every acceptance criterion, plus one top-tier review of how the slices fit together; then Security, PR/CI, Learn. |
| 6 | Driving | What happens when a slice finishes? | It stops cleanly and the user runs `/clear`, then `/sdlc:start` (the next ready slice, or a named one). Plus an opt-in autopilot called **autopilot mode**: off by default, on only when the user asks. |
| 7 | Slice gates | With autopilot off, which slice points wait for the user? | **Revised 2026-10-25:** the user approves the spec and backlog once; slices then run back to back and stop only on a failed gate, a scope-adding backlog change or a hard stop (merge, deploy, migrations, anything irreversible). Per-slice plan, review and commit approval are opt-in. Autopilot is the fresh-session-per-slice runner for when context would overflow. |
| 8 | Autopilot runner | How does autopilot get a fresh context per slice? | An external script that starts a headless CLI session per slice (`claude -p`) and reads state between runs. |
| 9 | Backlog home | Where does the backlog live? | `backlog.md` in the feature's documents folder only. No tracker sync. |
| 10 | Backlog change | A slice is too big, or uncovered work turns up | The agent proposes the backlog change and the user approves. Work outside the spec is never added silently. In autopilot, a proposal that adds scope stops the run; a split that keeps the same FRs continues. |
| 11 | Interview on | Which tracks interview in Discover? | **Revised 2026-10-25:** every track asks only blocking questions, in one batched message, or none; the rest become assumptions listed in the spec. Usually 0–1 touches. |
| 12 | Done when (superseded 2026-10-25 by row 11) | When is the intent complete? | Every item on a coverage checklist is answered (goal and why, users, in scope, out of scope, success and acceptance, constraints, edge and error cases, priority order), skipping what the request or code already answers. The agent says how many are left, then plays back a summary that the user confirms. No hard cap. |
| 13 | Record (superseded 2026-10-25: answers and assumptions go in the spec) | Are answers saved? | Yes, to `intent.md` as they come in, so a cleared interview resumes. The spec is built from it. |
| 14 | Build order | How to build this change | Spec and plan first, the plan itself split into a backlog. **Revised 2026-10-25:** after the Lite flow lands, on this worktree's branch `tammai/lite-and-slices`. Slices run Lite's inner loop; a low-risk M feature that fits one session stays on the Lite flow. |
