# Backlog: 2026-11-13-l-workbench

Record: the feature's change file (`scaffold.py paths 2026-11-13-l-workbench` → `change`) · Branch: `2026-11-13-l-workbench` · Each slice gets a short `plan-B<n>.md` when it starts and ends as one commit on the branch.

| ID | Slice | FRs | ACs | Deps | Size | Status |
|---|---|---|---|---|---|---|
| B1 | One scope parser for scripts and hooks; root test beside packages runs; brownfield doc fix | — | 1, 2, 3 | — | S | done |
| B2 | Workbench manifest: detection, scopes, `workbench add/remove`, doctor checks | — | 4, 5, 6 | B1 | M | done |
| B3 | Routing into app repos, read-only guard, no features in app repos | — | 7, 8, 9 | B2 | M | done |
| B4 | One feature across repos: per-repo branch and base, verify and freshness per repo, moved read-only repos | — | 10, 11, 12 | B3 | M | done |
| B5 | Ship across repos: commits per repo, merge order, linked PRs, out-of-order warning | — | 13, 14 | B4 | M | todo |
| B6 | App CI checks out the workbench; contract check in the workbench | — | 15 | B2 | S | todo |
| B7 | Setup reference, ADR 0025, wiki, CHANGELOG, stale-docs audit | — | 16 | B5, B6 | M | todo |
| B8 | Preferred stacks reference that greenfield setup proposes from | — | 17 | B7 | S | todo |

<!--
  Status: todo | in progress | done | blocked: <reason> (state.py writes it; `done` goes into the part's own commit). Deps: slice IDs, or —.
  ACs: the AC numbers the part proves (`1, 2`, `AC-003–005`): verify.py skips those of parts not started yet.
  Every spec FR appears in some row. Size: S (a few tasks) or M (up to ~6); bigger means split it.
  scripts/backlog.py reads this table: keep the ID, Deps and Status columns.
-->
