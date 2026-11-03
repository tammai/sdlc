# Backlog: <feature>

Record: the feature's change file (`scaffold.py paths <feature>` → `change`) · Branch: `<branch>` · Each slice gets a short `plan-B<n>.md` when it starts and ends as one commit on the branch.

| ID | Slice | FRs | ACs | Deps | Size | Status |
|---|---|---|---|---|---|---|
| B1 | <a vertical slice: something a user or test can see working end to end> | FR-001–002 | 1, 2 | — | S | todo |
| B2 | <next slice> | FR-003 | 3 | B1 | M | todo |

<!--
  Status: todo | in progress | done | blocked: <reason> (state.py writes it; `done` goes into the part's own commit). Deps: slice IDs, or —.
  ACs: the AC numbers the part proves (`1, 2`, `AC-003–005`): verify.py skips those of parts not started yet.
  Every spec FR appears in some row. Size: S (a few tasks) or M (up to ~6); bigger means split it.
  scripts/backlog.py reads this table: keep the ID, Deps and Status columns.
-->
