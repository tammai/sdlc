# Backlog: 2026-11-14-l-stack-blueprints

Record: the feature's change file (`.sdlc/2026-11-14-l-stack-blueprints/change.md`) · Branch: `2026-11-14-l-stack-blueprints` · Each slice gets a short `plan-B<n>.md` when it starts and ends as one commit on the branch.

| ID | Slice | FRs | ACs | Deps | Size | Status |
|---|---|---|---|---|---|---|
| B1 | Selection table, warnings and the extra `stack` interview questions; ADR 0026 | — | 1, 2, 3 | — | S | done |
| B2 | Stack sections: Vue, Next.js, Flutter, iOS, Android, FastAPI; reconcile Nuxt, React, Node, Go; CI toolchains | — | 4, 5, 6, 9 | B1 | M | done |
| B3 | Per-stack convention templates and `scaffold.py conventions`, rendered on first touch | — | 7, 8, 9 | B2 | M | todo |
| B4 | Platform references: cloudflare, vercel, docker-compose with Define checks | — | 10 | B1 | M | todo |
| B5 | Constitution proposals per stack; scaling roadmap knowledge template | — | 11 | B2 | S | todo |

<!--
  Status: todo | in progress | done | blocked: <reason> (state.py writes it; `done` goes into the part's own commit). Deps: slice IDs, or —.
  ACs: the AC numbers the part proves (`1, 2`, `AC-003–005`): verify.py skips those of parts not started yet.
  Every spec FR appears in some row. Size: S (a few tasks) or M (up to ~6); bigger means split it.
  scripts/backlog.py reads this table: keep the ID, Deps and Status columns.
-->
