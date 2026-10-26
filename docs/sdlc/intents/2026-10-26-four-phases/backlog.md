# Backlog: four phases instead of eleven stages

Spec: [spec.md](spec.md) · Branch: `tammai/lite-and-slices` · Each slice gets a short `plan-B<n>.md` when it starts and ends as one commit on the branch.

| ID | Slice | FRs | ACs | Deps | Size | Status |
|---|---|---|---|---|---|---|
| B1 | `state.py` phase names, `phase` field and contract v2; the state template's four-line checklist; trust anchor lets stricter changes through; spec 12 | FR-01, FR-02, FR-10 | 1, 2, 3 | — | S | done 5da03c6, 6a7110c |
| B2 | Orchestrator: core rewritten with the stage → phase → file map; `define.md`, `build.md`, `prove.md`, `ship.md` (with Learn) replace `stage-*.md` and `lite-flow.md`; `backlog-slices.md` and `start.md` on the phase loop; review brief and spec skill keep to the brief and read recurring defects; Intent section | FR-03, FR-04, FR-05, FR-06, FR-07, FR-09, FR-11 | 4, 5, 6, 7 | B1 | M | done (this commit) |
| B3 | `/sdlc:deploy` command and `references/deploy.md`, `references/operate.md`; host mirrors regenerated | FR-08 | 8 | B2 | S | todo |
| B4 | Docs: README text and diagram labels, `docs/specs` (02, 04, 05, 07, README), guidebook, playbook, runbook, prd, templates that say "Stage 5", CHANGELOG; stale-docs audit over every old stage name and file | FR-12 | 9 | B2, B3 | M | todo |

Every slice runs the full suite, `hosts.py check` and `scaffold.py agents --check` before its commit (AC 10). Testing rule: one test per user-visible behaviour plus the one failure that matters most, at the lowest level that proves it. No structural or meta tests. Skill and command text is instructed only. Release notes go under Unreleased in `CHANGELOG.md`.
