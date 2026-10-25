# Backlog: a cheaper, faster pipeline

Spec: [spec.md](spec.md) · Branch: `tammai/lite-and-slices` · Each slice gets a short `plan-B<n>.md` when it starts and ends as one commit on the branch.

| ID | Slice | FRs | ACs | Deps | Size | Status |
|---|---|---|---|---|---|---|
| B1 | `scripts/state.py` and the control contract (`state.json`, `events.jsonl`, `commands/` format), `docs/specs/12-control-contract.md` | FR-03 | 1, 2 | — | M | done 1aae424 |
| B2 | Orchestrator split into a core plus per-stage references, using `state.py` throughout; `Build: native \| subagent` | FR-02, FR-01, FR-10 | 3, 4, 9 | B1 | M | done (this commit) |
| B3 | Review loop: parallel verify + review, no simplifier, qa-tester on M and single-session Lite, failure modes in specs, recurring-defects list in reviewer briefs | FR-04, FR-07, FR-08, FR-09 | 5, 8 | B2 | M | todo |
| B4 | Commit security review once per review-ready diff while a feature is active (Claude Code) | FR-05 | 6 | — | S | todo |
| B5 | Setup leaves the product's manifest, dependencies and tooling alone unless the user agrees | FR-06 | 7 | — | S | todo |

Each slice updates the docs for its own requirements and runs the `CONTRIBUTING.md` stale-docs audit on the names it adds; `hosts.py check`, `scaffold.py agents --check` and the suite pass at every commit (FR-10). Tests: one per user-visible behaviour plus the failure that matters most; skill and command text is instructed only. Release notes under Unreleased in `CHANGELOG.md`.
