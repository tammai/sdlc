# Backlog: backlog slices and batched intent questions

Spec: [spec.md](spec.md) · Branch: `tammai/lite-and-slices` · Each slice is planned (`plan-B<n>.md`, short) when it starts and ends as one commit on the branch.

| ID | Slice | FRs | ACs | Deps | Size | Status |
|---|---|---|---|---|---|---|
| B1 | Batched intent questions: orchestrator Stage 1, Lite step 1 and the S brief; `writing-specs` without clarification markers; `brainstorming` builds on the answers | FR-01–02 | 1 | — | S | done f29701b |
| B2 | Backlog and the slice loop: `backlog.py` (`next`, `check`), backlog template, `writing-plans` backlog mode, orchestrator slice loop and gates, state lines, `/sdlc:start B<n>`, backlog proposals, trust-anchor test for 6 → 3 | FR-03–08, FR-11 | 2–5, 8, 9 | — | M | done (this commit) |
| B3 | Feature close: repeatable `diff_stats.py --plan`, `▶ Feature close` in the orchestrator | FR-09 | 6 | B2 | S | todo |
| B4 | Yolo: `scripts/yolo.py`, `--yolo` in `/sdlc:start` | FR-10 | 7 | B2 | M | todo |

Every slice updates `docs/specs/02-orchestration.md` for its own requirements and runs the `CONTRIBUTING.md` stale-docs audit on the names it adds. Tests stay minimal: one per user-visible behaviour plus the failure that matters most; skill and command text is instructed only. Release notes go under Unreleased in `CHANGELOG.md`.
