# A repo made writable in workbench.json stays guarded until the user accepts

## Why

**Request (verbatim):** "working on the open items in todo". The item: "Workbench: a repo the watch recorded as read-only stays guarded per call until the user accepts its flip; today `role_guard` reads the live `workbench.json`, so `"write": true` lets writes through until it's reverted (the watch reports and blocks Stop) — 3.15.0 smoke test K5".

**Proof:** `tests/test_workbench.py` › `test_a_repo_made_writable_stays_guarded_until_the_user_accepts` fails: after the agent sets `"write": true` for `specs`, a Write into `specs/` isn't denied. Seen live in the 3.15.0 smoke test (K5): `echo x >> specs/README.md` ran and changed the repo.

**Root cause:** `role_guard.read_only_problem` takes its list from `sdlc_scopes.read_only_names`, which reads the live `workbench.json`. The read-only watch keeps its own record of the read-only repos (`read_only` in its baseline, outside the repo) and reports a flip until the user accepts it, but the per-call guard never read that record.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| The guard also denies writes into every repo the watch's baselines list as `read_only`, until an accept rewrites that list | trusting `workbench.json` alone; denying the edit to `workbench.json` | the record lives outside the repo, and an accept is the user's own message; `workbench.json` is the team's file and must stay editable (`scaffold.py workbench add`) |
| Read the baseline the marker names, and this host's own only when that one can't be read; any read error adds nothing and leaves the manifest's guard standing | reading both (round 1) | every host's accept rewrites the marker's baseline, so a stale own file denied a repo accepted elsewhere with no way out (SR1-M2); a marker pointed at a decoy baseline is the documented text-check limitation on the watch's own files |
| A flipped repo's deny says how to lift it: the user's `accept read-only <name>` | the owner message | the user decides a flip, not the owner |

## Acceptance criteria

- **AC-001** After the watch's first look, a repo made writable in `workbench.json` is still denied per call (naming `accept read-only <name>`) until the user accepts, and writable after.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_workbench.py › ReadOnlyBackstop.test_a_repo_made_writable_stays_guarded_until_the_user_accepts | `python3 -m unittest discover -s tests -t tests -p test_workbench.py -k test_a_repo_made_writable_stays_guarded_until_the_user_accepts` |

## Must never break

- The rest of `test_workbench` and the role guard tests: an unseeded workbench, or one with no flip, guards exactly as before.
- `scaffold.py workbench add` and `remove` still work; a removed repo asks for one accept, as before.

## Out of scope

- The watch's own files' protection (a documented limitation, docs/wiki/Limitations.md).

## Review

- Fired: security (`Risk: high`). Code and UI: no trigger.
- Security r1 (opus): FAIL. SR1-M1 (a baseline read error lifted the whole per-call guard) and SR1-M2 (a stale host baseline denied a repo accepted elsewhere) fixed test first; SR1-L1 (tests used the runner's data folder) fixed; docstrings, spec 06 GRD-FR-033 and the changelog updated.
- Security r2 (opus): PASS, no new findings.
- Lessons: none filed; the trade-off on a forged marker is in Decisions.
